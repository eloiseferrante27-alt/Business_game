"""Simulation d'usine à plusieurs produits et clients (annexe 0013 §3 bis, étape 4a de la tranche T4b) : 3 produits,
une ligne par produit, 4 clients, palettes de matière de 120 ou 150 unités. Spec construite depuis le pack usine."""

import copy
from typing import Any

import pytest

from gmix.game import factory
from gmix.game.generation import generate

from .test_t4b_contract import make_params

WINDOWS = {"c1": (360, 450), "c2": (60, 120), "c3": (200, 260), "c4": (300, 330)}
CLIENT_PRODUCT = {"c1": "p1", "c2": "p2", "c3": "p3", "c4": "p1"}


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    raw = copy.deepcopy(generate(make_params("industrie", 1, 1)))
    f = raw["factory"]
    base_product, base_component, base_offer = raw["products"][0], raw["components"][0], raw["offers"][0]
    base_machines = [m for m in f["machines"] if m["line_id"] == "l2"]
    raw["lines"] = [{**raw["lines"][0], "id": f"l{n}", "product_id": f"p{n}"} for n in (1, 2, 3)]
    f["machines"] = [m for m in f["machines"] if m["line_id"] == "l1"] + [
        {**m, "id": f"l{n}-{m['id'].split('-')[1]}", "line_id": f"l{n}"} for n in (2, 3) for m in base_machines
    ]
    raw["products"] = [{**base_product, "id": f"p{n}", "line_id": f"l{n}", "component_id": f"c{n}"} for n in (1, 2, 3)]
    raw["components"] = [
        {**base_component, "id": f"c{n}", "product_id": f"p{n}", "units_per_pallet": upp, "initial_stock": 480}
        for n, upp in ((1, 120), (2, 150), (3, 120))
    ]
    raw["offers"] = [{**base_offer, "id": f"o{n}", "component_id": f"c{n}", "lead_time": 1} for n in (1, 2, 3)]
    f["bom"] = [{"component_id": f"c{n}", "per_unit": 1.0, "product_id": f"p{n}"} for n in (1, 2, 3)]
    f["clients"] = [
        {**f["customer"], "id": cid, "name": f"Client {cid}", "product_id": pid, "demand_per_day": 30,
         "pickup_window_min": list(WINDOWS[cid]), "site_id": None}
        for cid, pid in CLIENT_PRODUCT.items()
    ]  # fmt: skip
    f["resources"] = {**f["resources"], "docks": 3}
    return raw


def play(spec: dict[str, Any], lines: tuple[str, ...], pallets: int = 0, weeks: int = 1):
    plant = factory.Plant(spec)
    fs = factory.initial_state(plant)
    for offer in spec["offers"] if pallets else []:
        factory.order_mp(plant, fs, offer, pallets)
    for line in lines:
        factory.launch_of(plant, fs, line, 10)
    timeline = report = None
    for week in range(1, weeks + 1):
        fs, timeline, report = factory.simulate(plant, fs, week)
    return plant, fs, timeline, report


def test_plant_reads_three_products_and_four_clients(spec) -> None:
    plant = factory.Plant(spec)
    assert plant.pids == ["p1", "p2", "p3"] and plant.upps == [120, 150, 120]
    assert plant.line_prod == [0, 1, 2] and [c["p"] for c in plant.clients] == [0, 1, 2, 0]


def test_every_product_has_its_own_line_and_pallets_of_its_own_size(spec) -> None:
    _, fs, _, report = play(spec, ("l1", "l2", "l3"))
    assert all(report["lines"][lid]["good"] > 0 for lid in ("l1", "l2", "l3"))
    assert [row["product_id"] for row in report["by_product"]] == ["p1", "p2", "p3"]
    assert all(row["shipped"] > 0 for row in report["by_product"])
    assert sum(row["shipped"] for row in report["by_product"]) == report["shipped"]
    assert fs["pf"]["units"] == sum(fs["pf"]["by"])


def test_parts_do_not_mix_between_products(spec) -> None:
    plant, fs, _, report = play(spec, ("l2",))
    by = fs["mp"]["by"]
    assert by["units"][0] == plant.mp0s[0] and by["units"][2] == plant.mp0s[2]  # p1 et p3 : matière intacte
    assert by["units"][1] == plant.mp0s[1] - report["consumed_mp"] and report["consumed_mp"] > 0
    assert fs["pack"]["by_conf"][0] == fs["pack"]["by_conf"][2] == 0
    assert fs["pf"]["by"][0] <= plant.pf0s[0] and fs["pf"]["by"][2] <= plant.pf0s[2]  # aucune pièce de l'autre ligne


def test_initial_order_per_material_arrives_in_pallets_of_its_material(spec) -> None:
    plant, fs, _, _ = play(spec, (), pallets=2)
    by = fs["mp"]["by"]
    for p, upp in enumerate(plant.upps):  # chaque matière reçoit ses palettes (les non-conformes vont en quarantaine)
        assert by["units"][p] - plant.mp0s[p] + by["quarantine"][p] == 2 * upp
    assert fs["pending"] == [] and fs["receiving"] == {}


def test_each_client_is_delivered_inside_its_pickup_slot(spec) -> None:
    plant, fs, timeline, _ = play(spec, ("l1", "l2", "l3"), weeks=2)
    sent = [e for e in timeline["events"] if e[1] == "expedition"]
    assert {e[3]["client_id"] for e in sent} == set(WINDOWS)
    for t, _, _, data in sent:
        assert t % plant.mpd >= WINDOWS[data["client_id"]][0]
        assert data["product_id"] == CLIENT_PRODUCT[data["client_id"]]
    for order in fs["orders"]:
        assert order["product_id"] == CLIENT_PRODUCT[order["client_id"]]


def test_simulation_is_deterministic_and_leaves_the_input_untouched(spec) -> None:
    plant = factory.Plant(spec)
    fs = factory.initial_state(plant)
    frozen = copy.deepcopy(fs)
    first = factory.simulate(plant, fs, 1)
    assert fs == frozen and first == factory.simulate(plant, fs, 1)
