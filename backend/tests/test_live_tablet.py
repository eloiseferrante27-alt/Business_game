import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setenv("GMIX_DB_PATH", str(tmp_path / "live.db"))
    import app.database as database
    import app.simulation as simulation
    import app.api_tablet as tablet
    import app.main as main
    importlib.reload(database)
    importlib.reload(simulation)
    importlib.reload(tablet)
    importlib.reload(main)
    with TestClient(main.app) as client:
        yield client, simulation.simulation, database


def start(client):
    response = client.post("/api/v2/tablet/new-game", json={"company_name": "Usine Test", "difficulty": "normal", "rules_confirmed": True})
    assert response.status_code == 200
    return response.json()


def test_live_tablet_requires_rules_and_shows_real_state(live):
    client, engine, _ = live
    initial = client.get("/api/v2/tablet").json()
    assert initial["mode"] == "live"
    assert initial["raw"] == engine.state.model_dump(mode="json")
    assert len(initial["departments"]) == 10
    assert len(initial["tools"]) == 5
    assert initial["clock"]["supportsRealtime"] is False
    assert client.post("/api/v2/tablet/next-turn").status_code == 409
    assert client.post("/api/v2/tablet/new-game", json={"company_name": "Usine Test"}).status_code == 409
    assert start(client)["started"]


def test_purchase_of_and_turn_really_change_engine_and_journal(live):
    client, engine, _ = live
    start(client)
    result = client.post("/api/v2/tablet/actions", json={"action": "purchase", "supplier_id": "SUP-01", "sku": "MAT-01", "quantity": 100}).json()
    assert result["raw"]["purchase_orders"][0]["quantity"] == 100
    assert client.post("/api/v2/tablet/actions", json={"action": "production", "sku": "SKU-01", "quantity": 300}).status_code == 200
    before = engine.stock("MAT-01").quantity
    result = client.post("/api/v2/tablet/next-turn").json()
    assert result["clock"]["period"] == 2
    assert engine.stock("MAT-01").quantity < before
    assert result["raw"] == engine.journal.state
    assert result["history"][-1]["period"] == 2
    assert result["history"][-1]["produced"] == engine.state.kpis.produced
    assert any(e["element"] == "MAT-01" and e["old_state"] != e["new_state"] for e in engine.journal.events)
    assert result["events"]


def test_locked_configuration_refused_on_server_and_persisted(live):
    client, engine, database = live
    start(client)
    original = engine.stock("MAT-01").reorder_point
    response = client.post("/api/v2/tablet/configuration", json={"department_id": "stock", "configuration_id": "MAT-01:reorder_point", "value": 1})
    assert response.status_code == 403
    assert response.json()["detail"] == "Modification interdite : le formateur a fixé ce réglage pour toute la partie."
    assert engine.stock("MAT-01").reorder_point == original
    event = engine.journal.events[-1]
    assert event["type"] == "refusal" and event["cause"] == "decision"
    assert database.load_runtime()["events"][-1] == event
    assert client.get("/api/v2/tablet").json()["events"][0]["type"] == "refusal"


def test_invalid_action_does_not_queue_orders_and_is_logged(live):
    client, engine, _ = live
    start(client)
    assert client.post("/api/v2/tablet/actions", json={"action": "purchase", "supplier_id": "SUP-05", "sku": "MAT-01", "quantity": 10}).status_code == 422
    assert not engine.state.purchase_orders
    assert engine.journal.events[-1]["type"] == "refusal"
    assert client.post("/api/v2/tablet/actions", json={"action": "pretend_success"}).status_code == 422


def test_journal_replay_and_rng_continue_identically_after_restart(live):
    client, engine, _ = live
    from app.models import DecisionsRequest, ProductionOrder
    start(client)
    engine.submit_decisions(DecisionsRequest(production_orders=[ProductionOrder(sku="SKU-01", quantity=600)]))
    for _ in range(3):
        engine.next_turn()
    from app.simulation import SimulationEngine
    resumed = SimulationEngine()
    assert resumed.journal.events == engine.journal.events
    assert resumed.journal.state == engine.state.model_dump(mode="json")
    engine.persist = False  # compare two continuations without two writers on the same database
    assert engine.next_turn().model_dump() == resumed.next_turn().model_dump()
    assert engine.journal.events == resumed.journal.events


def test_new_game_keeps_prior_journal_rows_and_resets_live_history(live):
    client, engine, database = live
    start(client)
    client.post("/api/v2/tablet/next-turn")
    old_generation = engine.generation
    with sqlite3.connect(database.DB_PATH) as connection:
        old_count = connection.execute("SELECT count(*) FROM game_journal WHERE generation=?", (old_generation,)).fetchone()[0]
    fresh = start(client)
    assert fresh["clock"]["period"] == 1
    assert len(fresh["history"]) == 1
    with sqlite3.connect(database.DB_PATH) as connection:
        assert connection.execute("SELECT count(*) FROM game_journal WHERE generation=?", (old_generation,)).fetchone()[0] == old_count


def test_rejected_new_game_does_not_change_rng_or_current_game(live):
    client, engine, _ = live
    start(client)
    engine.next_turn()
    before_state = engine.state.model_dump()
    before_rng = engine.rng.getstate()
    response = client.post("/api/v2/tablet/new-game", json={"company_name": "Invalid", "scenario_id": "unknown", "rules_confirmed": True})
    assert response.status_code == 422
    assert engine.state.model_dump() == before_state
    assert engine.rng.getstate() == before_rng


def test_repeated_market_hazards_are_recorded_each_time_with_random_cause(live, monkeypatch):
    client, engine, _ = live
    from app.agents import MarketEvent
    start(client)
    monkeypatch.setattr(engine.market_agent, "generate_event", lambda rng: MarketEvent(code="materials_price_hike", description="Hausse identique", cost_multiplier=1.1))
    client.post("/api/v2/tablet/next-turn")
    result = client.post("/api/v2/tablet/next-turn").json()
    occurrences = [event for event in result["events"] if event["message"] == "Hausse identique"]
    assert {event["period"] for event in occurrences} == {2, 3}
    assert len(occurrences) == 2
    assert all(event["cause"] == "alea" for event in occurrences)
    assert any(event["path"] and "prices" in event["path"] and event["cause"] == "alea" for event in engine.journal.events)


def test_legacy_routes_remain_compatible(live):
    client, engine, _ = live
    assert client.get("/api/state").status_code == 200
    assert client.post("/api/new-game", json={"company_name": "Legacy"}).status_code == 200
    assert client.post("/api/decisions", json={"production_orders": [{"sku": "SKU-01", "quantity": 50}]}).status_code == 200
    assert client.post("/api/next-turn").status_code == 200
    assert client.get("/api/tablet/compare?sku=MAT-01&quantity=500").status_code == 200
    assert client.get("/api/v2/tablet").json()["raw"] == engine.journal.state
