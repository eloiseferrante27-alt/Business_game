"""Partie d'usine à plusieurs produits et clients (annexe 0013 §3 bis, étape 4b de la tranche T4b) : génération,
pilote automatique, vue publique, bilan et faits des agents, à 3 produits et 4 clients. Bornes du pack patchées en
mémoire (elles restent à [1, 1, 1] jusqu'à l'étape 7)."""

import copy
import json
from typing import Any

import pytest

from gmix.game import engine, factory
from gmix.game.engine import money
from gmix.game.generation import autopilot_check, generate
from gmix.game.spec import GameParams, SimSpec, default_params

from .test_t4b_contract import patched_limits

ACTOR = {"user_id": 1, "name": "Test", "role": None}


def make(monkeypatch, theme: str = "industrie", **options: Any) -> dict[str, Any]:
    patched_limits(monkeypatch, products=[1, 3, 1], clients=[1, 4, 1])
    return generate(GameParams(**default_params("usine") | {"theme": theme, "seed": 5} | options))


def play(spec: dict[str, Any]) -> dict[str, Any]:
    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        state = engine.advance(spec, state, autopilot_all=True)
    return state


@pytest.fixture(scope="module")
def game():  # les bornes patchées restent en place pendant tout le module
    with pytest.MonkeyPatch.context() as mp:
        spec = make(mp, products=3, clients=4)
        yield spec, play(spec)


def test_three_products_four_clients_game_is_valid_and_finishes_under_the_autopilot(game) -> None:
    spec, state = game
    SimSpec.model_validate(spec)
    assert [p["id"] for p in spec["products"]] == ["p1", "p2", "p3"]
    assert [c["id"] for c in spec["components"]] == ["c1", "c2", "c3"]
    assert [ln["product_id"] for ln in spec["lines"]] == ["p1", "p2", "p3"]
    assert [(c["id"], c["product_id"]) for c in spec["factory"]["clients"]] == [
        ("c1", "p1"), ("c2", "p2"), ("c3", "p3"), ("c4", "p1")
    ]  # fmt: skip
    assert state["status"] == "finished" and len(state["history"]) == spec["meta"]["weeks"]
    check = autopilot_check(spec)
    assert check["weeks"] == spec["meta"]["weeks"] and check["otif_mean"] > 0


def test_offers_are_one_per_material_and_supplier(game) -> None:
    spec, _ = game
    offers = spec["offers"]
    per_material = {c["id"]: [o["id"] for o in offers if o["component_id"] == c["id"]] for c in spec["components"]}
    assert per_material == {"c1": ["o1", "o2", "o3"], "c2": ["o4", "o5", "o6"], "c3": ["o7", "o8", "o9"]}
    assert [c.get("units_per_pallet") for c in spec["components"]][0] is None


def test_demand_of_a_product_is_shared_between_its_clients(game) -> None:
    spec, _ = game
    days = spec["factory"]["clock"]["days_per_turn"]
    share = {c["id"]: c["demand_per_day"] for c in spec["factory"]["clients"]}
    assert share["c1"] + share["c4"] == spec["products"][0]["demand"] // days
    assert share["c2"] == spec["products"][1]["demand"] // days
    assert share["c3"] == spec["products"][2]["demand"] // days
    assert spec["factory"]["customer"]["demand_per_day"] == share["c1"]


def test_demand_split_gives_the_extra_unit_to_the_first_clients(monkeypatch) -> None:
    spec = make(monkeypatch, products=1, clients=3)
    d = spec["products"][0]["demand"] // spec["factory"]["clock"]["days_per_turn"]
    got = [c["demand_per_day"] for c in spec["factory"]["clients"]]
    assert got == [d // 3 + (k < d % 3) for k in range(3)] and sum(got) == d


def test_initial_orders_are_placed_per_material(game) -> None:
    spec, _ = game
    f = spec["factory"]
    expected = ([f["initial_order"]] if f.get("initial_order") else []) + f["initial_orders"]
    plant = factory.Plant(spec)
    pending = engine.initial_state(spec)["fs"]["pending"]
    assert sorted(po["offer_id"] for po in pending) == sorted(o["offer_id"] for o in expected)
    assert all(po["component_id"] in plant.comps for po in pending)


def test_public_state_has_one_row_per_product_and_per_material(game) -> None:
    spec, state = game
    view = engine.public_state(spec, state)["factory"]
    assert [m["component_id"] for m in view["stocks"]["mp"]] == ["c1", "c2", "c3"]
    assert [r["product_id"] for r in view["by_product"]] == ["p1", "p2", "p3"]
    assert all(set(r) == {"product_id", "name", "quantity", "pallets", "shipped", "otif"} for r in view["by_product"])
    assert view["stocks"]["pf"]["quantity"] == sum(r["quantity"] for r in view["by_product"])
    assert {o["client_id"] for o in view["orders"]["customer"]} <= {"c1", "c2", "c3", "c4"}
    assert all(o["product_id"] for o in view["orders"]["customer"])
    assert len(json.dumps(engine.public_state(spec, state))) < 64_000  # budget du plan


def test_report_by_product_is_complete_and_matches_the_game(game) -> None:
    spec, state = game
    report = engine.debrief(spec, state)["by_product"]
    assert [r["product_id"] for r in report] == ["p1", "p2", "p3"]
    assert all(r["shipped"] > 0 and r["name"] and r["otif"] is not None for r in report)
    for i, row in enumerate(report):
        assert row["shipped"] == sum(h["by_product"][i]["shipped"] for h in state["history"])
    assert all(len(h["by_product"]) == 3 for h in state["history"])


def test_revenue_is_the_sum_by_product_of_shipped_times_price(game) -> None:
    spec, state = game
    price = {p["id"]: p["price"] for p in spec["products"]}
    shipped = {p: 0 for p in price}
    state = engine.start(spec, engine.initial_state(spec))
    state = engine.advance(spec, state, autopilot_all=True)
    for row in state["history"][0]["by_product"]:
        shipped[row["product_id"]] += row["shipped"]
    assert state["last"]["revenue"] == round(sum(shipped[p] * price[p] for p in price))


def test_order_action_uses_the_pallet_of_the_material_of_the_offer(game) -> None:
    spec, _ = game
    state = engine.start(spec, engine.initial_state(spec))
    offer = next(o for o in spec["offers"] if o["component_id"] == "c2")
    plant = factory.Plant(spec)
    values = {"offer": offer["id"], "pallets": offer["min_order"]}
    new, summary = engine.act(spec, state, "pilotage", "commander_mp", values, actor=ACTOR, manager=True,
                              occupied_roles=set())  # fmt: skip
    po = new["fs"]["pending"][-1]
    price = round(po["pallets"] * plant.upps[1] * offer["unit_cost"], 2)  # palette de 150, pas celle de c1
    assert po["component_id"] == "c2" and plant.upps[1] != plant.upps[0] and f"{money(price)}" in summary


def test_agents_say_the_facts_by_product_and_the_client_only_speaks_of_c1(game) -> None:
    spec, state = game
    briefings = engine.public_state(spec, state)["briefings"]
    mp_facts = briefings["agent_stock_mp"]["facts"]
    assert all(c["name"] in " ".join(mp_facts) for c in spec["components"])
    wh = briefings["agent_entrepot_pf"]["facts"]
    assert any(all(p["name"] in fact for p in spec["products"]) for fact in wh)
    c1_open = [
        o for o in engine.public_state(spec, state)["factory"]["orders"]["customer"]
        if o["client_id"] == "c1" and o["status"] != "livree"
    ]  # fmt: skip
    assert f"{len(c1_open)} commande(s) attendue(s) chez nous." in briefings["agent_client"]["facts"]


def test_one_product_with_three_clients_is_playable(monkeypatch) -> None:
    spec = make(monkeypatch, products=1, clients=3)
    assert {c["product_id"] for c in spec["factory"]["clients"]} == {"p1"}
    assert {s["id"] for s in spec["world"]["sites"] if s["kind"] == "client"} == {"client", "client_b", "client_c"}
    assert play(spec)["status"] == "finished"


def test_same_seed_same_multi_game(monkeypatch) -> None:
    a = make(monkeypatch, products=3, clients=4, difficulty="decouverte")
    b = make(monkeypatch, products=3, clients=4, difficulty="decouverte")
    assert a == b and copy.deepcopy(a) == b


@pytest.mark.parametrize("theme", ["industrie", "automobile"])
def test_discovery_has_no_stockout_and_a_high_otif_at_three_products(monkeypatch, theme) -> None:
    check = autopilot_check(make(monkeypatch, theme, products=3, clients=4, difficulty="decouverte"))
    assert check["otif_mean"] >= 95 and check["stockout_weeks"] == 0 and check["final_cash"] > 0
