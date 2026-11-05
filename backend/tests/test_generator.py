import copy
import importlib

import pytest

from app import generator
from app.scenario import load_scenario


def test_reference_world_passes_its_domain_rules():
    assert generator.validate(load_scenario("default")) == []


def test_same_seed_same_world_and_seeds_differ():
    assert generator.generate(seed=7) == generator.generate(seed=7)
    assert generator.generate(seed=7)["stock_items"] != generator.generate(seed=8)["stock_items"]


@pytest.mark.parametrize("seed", range(30))
def test_every_seed_gives_a_coherent_world(seed):
    world = generator.generate(seed=seed)  # generate() lève WorldError si validate() trouve un problème
    offers = {}
    for supplier in world["suppliers"]:
        for sku in supplier["prices"]:
            offers[sku] = offers.get(sku, 0) + 1
    purchased = [i["sku"] for i in world["stock_items"] if i["category"] in ("MP", "PDR")]
    assert all(offers.get(sku, 0) >= 2 for sku in purchased)
    zones = list(world["layout"]["zones"].values())
    for i, a in enumerate(zones):  # aucune zone ne chevauche une autre
        for b in zones[i + 1:]:
            assert abs(a["x"] - b["x"]) * 2 >= a["w"] + b["w"] or abs(a["z"] - b["z"]) * 2 >= a["d"] + b["d"]


def test_parameters_are_honoured():
    world = generator.generate(seed=3, products=4, machines=5)
    assert len(world["products"]) == len(world["lines"]) == 4
    assert len(world["routing"]["machines"]) == 5
    assert world["generation"] == {"domain": "supply_chain", "seed": 3, "params": {"products": 4, "machines": 5}, "pack_version": 1}
    with pytest.raises(ValueError):
        generator.generate(seed=3, products=99)


def test_validation_reports_broken_worlds():
    world = copy.deepcopy(load_scenario("default"))
    world["routing"]["machines"][0]["mttr_hours"] = 500
    world["suppliers"] = [s for s in world["suppliers"] if s["id"] != "SUP-04"]  # MAT-04 n'a plus qu'une offre
    world["stock_items"][0]["reorder_point"] = 10
    issues = " ".join(generator.validate(world))
    assert "MTTR" in issues and "MAT-04 : 1 offre" in issues and "point de commande 10" in issues
    del world["routing"]
    assert generator.validate(world)[0].startswith("Champ manquant")


def test_engine_plays_a_generated_world(tmp_path, monkeypatch):
    import app.scenario as scenario
    for path in scenario.SCENARIO_DIR.glob("*.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    monkeypatch.setattr(scenario, "SCENARIO_DIR", tmp_path)
    monkeypatch.setenv("GMIX_DB_PATH", str(tmp_path / "gmix.db"))
    scenario.load_scenario.cache_clear()
    world = generator.generate(seed=11, products=3)
    generator.save(world)
    assert world["id"] in {s["id"] for s in scenario.list_scenarios()}

    import app.database as database
    importlib.reload(database)
    import app.simulation as simulation
    importlib.reload(simulation)
    from app.models import DecisionsRequest, NewGameRequest, ProductionOrder

    sim = simulation.SimulationEngine()
    sim.new_game(NewGameRequest(company_name="Test", scenario_id=world["id"]))
    assert [line.product_sku for line in sim.state.production_lines] == ["SKU-01", "SKU-02", "SKU-03"]
    mp_before = sim.stock("MAT-02").quantity
    sim.submit_decisions(DecisionsRequest(production_orders=[ProductionOrder(sku="SKU-02", quantity=200)]))
    sim.next_turn()
    assert sim.stock("MAT-02").quantity < mp_before          # le kit généré sort du stock MP
    assert sim.state.last_week["packed"] > 0                 # et le flux v3 va jusqu'à l'emballage
    for _ in range(3):
        sim.next_turn()
    assert sim.state.current_week == 5
    scenario.load_scenario.cache_clear()
