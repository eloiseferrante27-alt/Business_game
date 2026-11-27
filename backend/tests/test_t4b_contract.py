"""Contrat de la tranche T4b (annexe 0013 §3 bis et §7, point 10) : plusieurs produits et clients.

Étape 1 du plan : la référence de la partie à 1 produit et 1 client est capturée avant toute modification du moteur
(`fixtures/t4b_reference.json`) ; ces tests prouvent qu'elle reste identique (`capture` retire les clés que T4b ajoute,
complément 9). Les exemples nouveaux du §7.10 (bornes cibles, un client par produit) sont verts depuis l'étape 4b.

Régénérer la référence (seulement si une règle change volontairement, avec accord du game-designer) :
    cd backend; .venv\\Scripts\\python -m tests.test_t4b_contract
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from gmix.game import engine
from gmix.game import spec as spec_module
from gmix.game.generation import autopilot_check, generate
from gmix.game.layout import world_fingerprint
from gmix.game.spec import GameParams, SimSpec, default_params, load_pack

from .test_spec_0013 import client, two_products
from .test_spec_contract import factory_spec, usine_pack  # noqa: F401

FIXTURE = Path(__file__).parent / "fixtures" / "t4b_reference.json"
THEMES = ("industrie", "automobile")
SEEDS = (1, 2, 3)
BUILDINGS = (1, 3)
DROPPED = ("provenance", "panels")  # le pack change en T4b : ces deux clés sont hors comparaison


def case_key(theme: str, seed: int, buildings: int) -> str:
    return f"{theme}/{seed}/{buildings}"


def make_params(theme: str, seed: int, buildings: int) -> GameParams:
    return GameParams(**default_params("usine") | {"theme": theme, "seed": seed, "buildings": buildings})


def capture(theme: str, seed: int, buildings: int) -> dict[str, Any]:
    spec = generate(make_params(theme, seed, buildings))
    state = engine.start(spec, engine.initial_state(spec))
    week2 = None
    while state["status"] == "running":
        state = engine.advance(spec, state, autopilot_all=True)
        if len(state["history"]) == 2:
            week2 = copy.deepcopy(state)  # état « ancien » : sert à tester la mise à niveau (T4b) sur la forme actuelle
    spec = copy.deepcopy(spec)
    factory = spec.get("factory") or {}
    if factory.get("initial_orders") == []:  # clés vides de SimSpec.model_dump (complément 9)
        del factory["initial_orders"]
    for comp in spec.get("components", []):
        if comp.get("units_per_pallet") is None:
            comp.pop("units_per_pallet", None)
    result = {
        "spec": {k: v for k, v in spec.items() if k not in DROPPED},
        "world_fingerprint": world_fingerprint(spec["world"]),
        "autopilot_check": autopilot_check(spec),
        "history": state["history"],
        "public_state": engine.public_state(spec, state),
        "state_week2": week2,
    }
    result = json.loads(json.dumps(result))  # forme JSON, comme en base : tuples en listes
    drop_new_keys(result)
    return result


def drop_new_keys(value: Any) -> None:
    """Clés que la tranche T4b ajoute même à 1 produit et 1 client (complément 9) : `by_product` (vue, historique),
    `client_id` et `product_id` des commandes de la vue publique."""
    if isinstance(value, dict):
        value.pop("by_product", None)
        orders = (value.get("orders") or {}).get("customer") if isinstance(value.get("orders"), dict) else None
        for order in orders or []:
            order.pop("client_id", None)
            order.pop("product_id", None)
        for child in value.values():
            drop_new_keys(child)
    elif isinstance(value, list):
        for child in value:
            drop_new_keys(child)


def build_reference() -> dict[str, Any]:
    return {case_key(t, s, b): capture(t, s, b) for t in THEMES for s in SEEDS for b in BUILDINGS}


def _reference() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reference() -> dict[str, Any]:
    return _reference()


# --- Non-régression : 1 produit, 1 client -------------------------------------------------------------------------


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("buildings", BUILDINGS)
def test_one_product_one_client_game_is_identical_to_the_reference(reference, theme, seed, buildings) -> None:
    expected = reference[case_key(theme, seed, buildings)]
    actual = capture(theme, seed, buildings)
    for key in expected:  # une clé par assertion : l'écart est nommé
        assert actual[key] == expected[key], key


def test_reference_covers_every_case(reference) -> None:
    assert set(reference) == {case_key(t, s, b) for t in THEMES for s in SEEDS for b in BUILDINGS}
    assert all(case["state_week2"]["week"] == 3 or case["state_week2"] for case in reference.values())


# --- generate aux bornes de limits ---------------------------------------------------------------------------------


def patched_limits(monkeypatch, **limits: list[int]) -> None:
    real = spec_module.load_pack

    def patched(pack_id: str) -> dict[str, Any]:
        pack = copy.deepcopy(real(pack_id))
        pack["limits"] |= limits
        return pack

    monkeypatch.setattr(spec_module, "load_pack", patched)
    from gmix.game import factory_game, factory_generation

    for module in (factory_generation, factory_game):
        monkeypatch.setattr(module, "load_pack", patched)


def bound_cases(limits: dict[str, list[int]]) -> list[dict[str, int]]:
    """Min, max et défaut de chaque clé (une à la fois), puis toutes au max."""
    keys = [k for k in ("products", "suppliers", "clients", "buildings", "weeks") if k in limits]
    cases = [{k: limits[k][i]} for k in keys for i in (0, 1, 2)]
    return cases + [{k: limits[k][1] for k in keys}]


def check_bounds(limits: dict[str, list[int]]) -> None:
    for case in bound_cases(limits):
        for theme in THEMES:
            params = GameParams(**default_params("usine") | {"theme": theme, "seed": 2} | case)
            spec = generate(params)
            reread = SimSpec.model_validate(spec).model_dump(mode="json")
            lost = set(json.loads(json.dumps(spec))) - set(reread)
            assert not lost, f"{case} {theme} : clés perdues {sorted(lost)}"


def test_generate_at_the_bounds_of_the_real_pack() -> None:
    check_bounds(load_pack("usine")["limits"])


def test_generate_at_the_target_bounds_of_t4b(monkeypatch) -> None:
    target = {"products": [1, 3, 1], "clients": [1, 4, 1]}
    patched_limits(monkeypatch, **target)
    check_bounds(spec_module.load_pack("usine")["limits"])  # le module patché, pas l'import direct


# --- GameParams -------------------------------------------------------------------------------------------------


def test_clients_at_least_one_per_product(monkeypatch) -> None:
    patched_limits(monkeypatch, products=[1, 3, 1], clients=[1, 4, 1])
    with pytest.raises(ValueError, match="au moins un par produit"):
        GameParams(**default_params("usine") | {"products": 3, "clients": 2})


def test_products_without_clients_gives_one_client_each(monkeypatch) -> None:
    patched_limits(monkeypatch, products=[1, 3, 1], clients=[1, 4, 1])
    spec = generate(GameParams(**default_params("usine") | {"products": 3, "seed": 1}))
    assert len(spec["factory"]["clients"]) == 3


def test_workshop_with_four_products_is_valid() -> None:
    spec = generate(GameParams(**default_params("atelier") | {"products": 4, "seed": 1}))
    assert len(SimSpec.model_validate(spec).products) == 4


# --- SimSpec : refus de la tranche T4b ---------------------------------------------------------------------------


def refused(raw: dict[str, Any], *words: str) -> None:
    with pytest.raises(ValidationError) as caught:
        SimSpec.model_validate(raw)
    assert all(word in str(caught.value) for word in words), str(caught.value)


def test_bill_of_materials_one_article_per_product(usine_pack) -> None:  # noqa: F811
    raw = factory_spec()
    raw["factory"]["bom"].append({"component_id": "c1", "per_unit": 2})
    refused(raw, "une seule matière")


def test_component_not_shared_between_products(usine_pack) -> None:  # noqa: F811
    raw = two_products()
    raw["factory"]["bom"][1]["component_id"] = "c1"
    refused(raw, "partagée")


def test_client_slot_inside_the_day(usine_pack) -> None:  # noqa: F811
    raw = factory_spec()
    raw["factory"]["clients"] = [client(1, pickup_window_min=[0, 500])]
    refused(raw, "créneau d'enlèvement", "480")


def test_every_product_has_a_client(usine_pack) -> None:  # noqa: F811
    raw = two_products()
    raw["factory"]["clients"] = [client(1)]
    refused(raw, "produit p2 sans client")


def test_units_per_pallet_of_a_component(usine_pack) -> None:  # noqa: F811
    raw = factory_spec()
    raw["components"][0]["units_per_pallet"] = 120
    assert SimSpec.model_validate(raw).components[0].units_per_pallet == 120
    raw["components"][0]["units_per_pallet"] = 0
    refused(raw, "units_per_pallet")


def test_initial_orders_refuse_unknown_offer_and_second_order_of_a_component(usine_pack) -> None:  # noqa: F811
    raw = two_products()
    order = {"offer_id": "o2", "pallets": 2, "arrival_day": 1}
    raw["factory"]["initial_orders"] = [order]
    assert len(SimSpec.model_validate(raw).factory.initial_orders) == 1
    raw["factory"]["initial_orders"] = [order | {"offer_id": "o99"}]
    refused(raw, "o99")
    raw["factory"]["initial_order"] = order | {"offer_id": "o1"}
    raw["factory"]["initial_orders"] = [order | {"offer_id": "o1"}]
    refused(raw, "c1")


if __name__ == "__main__":
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(json.dumps(build_reference(), ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"{FIXTURE} : {FIXTURE.stat().st_size} octets")
