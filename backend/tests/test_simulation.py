import json
import sqlite3

import pytest


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("GMIX_DB_PATH", str(tmp_path / "gmix.db"))
    import importlib
    import app.database as database
    importlib.reload(database)
    import app.simulation as simulation
    importlib.reload(simulation)
    from app.models import NewGameRequest
    sim = simulation.SimulationEngine()
    sim.new_game(NewGameRequest(company_name="Test"))
    return sim


def test_unified_stock_has_three_parts_with_same_parameters(engine):
    categories = {item.category for item in engine.state.stocks}
    assert {"MP", "SF", "PF", "PDR"} <= categories
    for item in engine.state.stocks:
        assert item.minimum <= item.capacity_max
        assert item.quantity <= item.capacity_max


def test_world_has_nine_blocks_and_agents(engine):
    assert len(engine.state.blocks) == 9
    block_ids = {block.id for block in engine.state.blocks}
    assert all(agent.block_id in block_ids for agent in engine.state.agents)
    roles = {agent.role for agent in engine.state.agents}
    assert {"chauffeur_fournisseur", "chauffeur_livreur", "chauffeur_client", "magasinier_logistique", "responsable_production"} <= roles


def test_same_seed_gives_same_game(engine):
    from app.models import DecisionsRequest, NewGameRequest, ProductionOrder
    def play():
        engine.new_game(NewGameRequest(company_name="Test"))
        engine.submit_decisions(DecisionsRequest(production_orders=[ProductionOrder(sku="SKU-01", quantity=400)]))
        for _ in range(4):
            engine.next_turn()
        return engine.state.kpis.model_dump()
    assert play() == play()


def test_material_follows_the_v3_path(engine):
    from app.models import DecisionsRequest, ProductionOrder
    mp_before = engine.stock("MAT-01").quantity
    engine.submit_decisions(DecisionsRequest(production_orders=[ProductionOrder(sku="SKU-01", quantity=300)]))
    engine.next_turn()
    report = engine.state.last_week
    assert engine.stock("MAT-01").quantity < mp_before          # kit sorti du stock MP
    assert report["semi_finished"] > 0                          # passage par le stock SF
    assert report["produced"] + report["quality_losses"] > 0     # contrôle qualité
    assert report["packed"] > 0                                  # emballage


def test_purchase_needs_a_supplier_that_sells_the_material(engine):
    from app.models import DecisionsRequest, SupplierOrder
    with pytest.raises(ValueError):
        engine.submit_decisions(DecisionsRequest(orders=[SupplierOrder(supplier_id="SUP-05", sku="MAT-01", quantity=10)]))
    engine.submit_decisions(DecisionsRequest(orders=[SupplierOrder(supplier_id="SUP-01", sku="MAT-01", quantity=10)]))
    assert engine.state.purchase_orders[0].unit_price == 3.50


def test_supplier_truck_arrives_at_unloading_dock(engine):
    from app.models import DecisionsRequest, SupplierOrder
    engine.submit_decisions(DecisionsRequest(orders=[SupplierOrder(supplier_id="SUP-07", sku="MAT-PDR", quantity=2)]))
    seen = []
    for _ in range(4):
        engine.next_turn()
        seen += [truck.block_id for truck in engine.state.trucks if truck.kind == "fournisseur"]
    assert seen and set(seen) == {"quai_dechargement"}


def test_customer_orders_use_two_delivery_modes(engine):
    for _ in range(3):
        engine.next_turn()
    modes = {order.mode for order in engine.state.customer_orders}
    assert modes == {"livraison", "enlèvement"}
    assert all(truck.block_id in {"quai_dechargement", "logistique_transport"} for truck in engine.state.trucks)


def test_comparator_sorts_by_total_cost(engine):
    quotes = engine.quotes("MAT-01", 500)
    assert [quote.supplier_id for quote in quotes] == ["SUP-03", "SUP-01", "SUP-02"]
    assert quotes[0].total_cost == 1650.0


def test_old_v1_save_is_archived_not_loaded(tmp_path, monkeypatch):
    db = tmp_path / "gmix.db"
    monkeypatch.setenv("GMIX_DB_PATH", str(db))
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE game_snapshot (id INTEGER PRIMARY KEY CHECK (id = 1), state_json TEXT NOT NULL, pending_orders_json TEXT NOT NULL)")
    connection.execute("INSERT INTO game_snapshot VALUES (1, ?, '[]')", (json.dumps({"current_week": 7, "started": True}),))
    connection.commit()
    connection.close()
    import importlib
    import app.database as database
    importlib.reload(database)
    import app.simulation as simulation
    importlib.reload(simulation)
    sim = simulation.SimulationEngine()
    assert sim.state.current_week == 1 and sim.state.started is False
    archived = sqlite3.connect(db).execute("SELECT COUNT(*) FROM archived_snapshot").fetchone()[0]
    assert archived == 1
