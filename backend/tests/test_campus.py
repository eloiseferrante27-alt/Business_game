"""Campus (ADR 0013, T5, annexe 0013 §2 bis, étape 4) : `place_campus`, trajets (`path_m`, `travel_min`), contrôles
de `check_placement` entre bâtiments. Le pack réel borne `buildings` à [1, 1, 1] jusqu'à l'étape 9 : ces tests le
portent à [1, 3, 1] en mémoire (fixture), sans toucher le fichier."""

import copy
import time
from functools import lru_cache
from typing import Any

import pytest

from gmix.game import engine, factory, factory_game, factory_generation, layout
from gmix.game import spec as spec_module
from gmix.game.generation import generate
from gmix.game.layout import LayoutError, check_placement, path_m, path_points, place_campus, travel_min
from gmix.game.spec import GameParams, SimSpec, default_params, load_pack

from .test_layout import make_spec

REAL = load_pack("usine")
SEEDS = range(1, 13)
PLANS = {  # les trois plans valides de l'usine (hall + entrepôt, hall + maintenance, les trois)
    "entrepot": ["hall_production", "entrepot"],
    "maintenance": ["hall_production", "atelier_maintenance"],
    "trois": ["hall_production", "entrepot", "atelier_maintenance"],
}


@pytest.fixture(scope="module", autouse=True)
def three_buildings():
    mp = pytest.MonkeyPatch()
    original = spec_module.load_pack
    pack = copy.deepcopy(REAL)
    pack["limits"]["buildings"] = [1, 3, 1]

    def patched(pack_id: str) -> dict[str, Any]:
        return pack if pack_id == "usine" else original(pack_id)

    for module in (spec_module, factory_generation, factory_game):
        mp.setattr(module, "load_pack", patched)
    yield pack
    mp.undo()
    gen.cache_clear()


@lru_cache
def gen(seed: int, buildings: int | None = None, plan: str | None = None) -> dict[str, Any]:
    extra: dict[str, Any] = {"buildings": buildings}
    if plan:
        extra = {"world_plan": [layout_plan(a, plan) for a in PLANS[plan]]}
    params = GameParams(**default_params("usine") | {"seed": seed, "weeks": 4} | extra)
    return generate(params)


def layout_plan(archetype: str, plan: str) -> dict[str, Any]:
    """Plan complet : l'entrepôt et l'atelier prennent leurs départements, le hall le reste."""
    rooms = REAL["building_archetypes"][archetype]["rooms"]
    listed = {d for r in rooms.values() for d in r["blocks"]}
    all_listed = {
        d for a in PLANS[plan][1:] for r in REAL["building_archetypes"][a]["rooms"].values() for d in r["blocks"]
    }
    interior = [d["id"] for d in REAL["departments"] if not d.get("external")]
    ids = (
        [d for d in interior if d in listed]
        if archetype != "hall_production"
        else [d for d in interior if d not in all_listed]
    )
    return {"archetype": archetype, "department_ids": ids}


# --- trajets ------------------------------------------------------------------------------------------------------


def tiny_spec() -> dict[str, Any]:
    """Deux bâtiments à la main : b1 (pièces r1 et r2) et b2 (pièce r3), entrées au nord, un chemin droit."""
    rooms = [
        {"id": "b1.r1", "building_id": "b1", "area": [0, 0, 10, 10], "doors": [[10, 5]]},
        {"id": "b1.r2", "building_id": "b1", "area": [10, 0, 20, 10], "doors": [[10, 5]]},
        {"id": "b2.r3", "building_id": "b2", "area": [30, 0, 40, 10], "doors": [[35, 0]]},
    ]
    return {
        "departments": [
            {"id": "a", "area": [0, 0, 10, 10], "room_id": "b1.r1"},
            {"id": "a2", "area": [2, 2, 4, 4], "room_id": "b1.r1"},
            {"id": "b", "area": [10, 0, 20, 10], "room_id": "b1.r2"},
            {"id": "c", "area": [30, 0, 40, 10], "room_id": "b2.r3"},
            {"id": "lost", "area": [0, 0, 1, 1]},
        ],
        "world": {
            "buildings": [
                {"id": "b1", "area": [0, 0, 20, 10], "entrance": [10, 0]},
                {"id": "b2", "area": [30, 0, 40, 10], "entrance": [35, 0]},
            ],
            "rooms": rooms, "bounds": [0, 0, 40, 10],
        },
        "factory": {"logistics": {"walk_m_per_min": 75, "forklift_m_per_min": 100}},
    }  # fmt: skip


def test_path_in_a_room_is_manhattan_and_inside_a_building_goes_through_the_doors() -> None:
    spec = tiny_spec()
    assert path_m(spec, "a", "a2") == pytest.approx(4)
    # b1.r1 -> b1.r2 : (5,5) -> porte (10,5) -> (15,5)
    assert path_m(spec, "a", "b") == pytest.approx(10)
    assert path_points(spec, "a", "b")[0] == [5.0, 5.0] and path_points(spec, "a", "b")[-1] == [15.0, 5.0]


def test_path_between_buildings_goes_out_by_the_entrances() -> None:
    spec = tiny_spec()
    # (5,5) -> porte (10,5) -> entrée (10,0) ; dehors de (10,0) à (35,0) par la rue au nord ; (35,0) -> (35,5) -> (35,5)
    expected = (5 + 5) + (25) + 5
    got = path_m(spec, "a", "c")
    assert expected - 3 <= got <= expected + 3  # chemin à cellules de 1 m : l'écart tient au pas de la grille
    assert path_m(spec, "c", "a") == pytest.approx(got)


def test_a_third_building_in_between_forces_a_detour() -> None:
    spec = tiny_spec()
    free = path_m(spec, "a", "c")
    walled = copy.deepcopy(spec)
    walled["world"]["buildings"].append({"id": "b3", "area": [21, -6, 29, 4], "entrance": [25, 4]})  # barre la rue
    assert path_m(walled, "a", "c") > free + 5


def _in_other_room(spec: dict[str, Any], pts: list[list[float]], keep: set[str]) -> list[str]:
    """Pièces hors `keep` dont l'intérieur est traversé par la polyligne (échantillon tous les 0,25 m)."""
    hit = set()
    for p, q in zip(pts, pts[1:], strict=False):
        n = max(1, int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) / 0.25))
        for k in range(n + 1):
            x, z = p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n
            hit |= {r["id"] for r in spec["world"]["rooms"]
                    if r["id"] not in keep and r["area"][0] + 0.01 < x < r["area"][2] - 0.01
                    and r["area"][1] + 0.01 < z < r["area"][3] - 0.01}  # fmt: skip
    return sorted(hit)


def test_a_path_never_crosses_another_room() -> None:
    spec = tiny_spec()  # b1.r1 et b1.r2 se touchent par la porte (10, 5) ; l'entrée (10, 0) est sur leur mur commun
    assert _in_other_room(spec, path_points(spec, "a", "c"), {"b1.r1", "b2.r3"}) == []
    for plan in PLANS:
        for seed in (1, 2, 3, 4):
            sp = gen(seed, plan=plan)
            for a, b, _ in layout.TIMED_LINKS.values():
                pts = path_points(sp, a, b)
                rooms = {d["id"]: d["room_id"] for d in sp["departments"]}
                assert _in_other_room(sp, pts, {rooms[a], rooms[b]}) == [], (plan, seed, a, b)


def test_a_walled_in_door_has_no_path() -> None:
    spec = tiny_spec()
    spec["world"]["buildings"][0]["entrance"] = [20, 5]  # contre la pièce r2, que le chemin ne peut pas traverser
    with pytest.raises(LayoutError, match="muré|aucun chemin"):
        path_points(spec, "a", "c")


def test_protected_path_checks_the_whole_path_even_next_to_an_entrance() -> None:
    rule = {"id": "r", "a": "x", "b": "y", "crossings_max": 9, "one_way": False, "barrier": True}
    spec = {"world": {"links": [{"from_site": "x", "to_site": "y", "points": [[10, 0], [10, 8]]}],
                      "buildings": [{"id": "b1", "area": [0, 0, 20, 10], "entrance": [10, 0]}],
                      "rooms": [{"id": "b1.r1", "building_id": "b1", "area": [0, 0, 20, 10], "doors": [[10, 8]]}],
                      }}  # fmt: skip
    post = {"role": "poste", "position": [11, 0.5], "asset": "prop_post"}
    assert len(layout._protected_path(rule, spec, lambda n: [(0, 0, 1, 1)], [post])) == 1
    fence = {"role": "barriere", "position": [11, 3], "asset": "prop_fence"}
    assert layout._protected_path(rule, spec, lambda n: [(0, 0, 1, 1)], [post, fence]) == []


def test_path_errors_and_travel_minutes() -> None:
    spec = tiny_spec()
    with pytest.raises(LayoutError, match="inconnu"):
        path_m(spec, "a", "zz")
    with pytest.raises(LayoutError, match="sans pièce"):
        path_m(spec, "a", "lost")
    assert travel_min(spec, "a", "c", "marche") == pytest.approx(path_m(spec, "a", "c") / 75)
    assert travel_min(spec, "a", "c", "chariot") == pytest.approx(path_m(spec, "a", "c") / 100)
    spec["factory"]["logistics"] = {"walk_m_per_min": None, "forklift_m_per_min": None}
    with pytest.raises(LayoutError, match="vitesses"):
        travel_min(spec, "a", "c", "marche")


def test_timed_links_are_the_three_passages_of_the_engine() -> None:
    assert layout.TIMED_LINKS == {
        "kit": ("stock_mp", "production", "chariot"),
        "repair": ("maintenance", "production", "marche"),
        "pallet": ("emballage", "entrepot_pf", "chariot"),
    }


# --- default_plan -------------------------------------------------------------------------------------------------


def test_default_plan_gives_every_interior_department_once() -> None:
    interior = {d["id"] for d in REAL["departments"] if not d.get("external")}
    for n in (1, 2, 3):
        plan = layout.default_plan(REAL, n, 7)
        assert len(plan) == n and plan[0]["archetype"] == "hall_production"
        housed = [d for b in plan for d in b["department_ids"]]
        assert sorted(housed) == sorted(interior)
    assert layout.default_plan(REAL, 3, 7) == layout.default_plan(REAL, 3, 7)
    assert {tuple(b["archetype"] for b in layout.default_plan(REAL, 2, s)) for s in range(12)} == {
        ("hall_production", "entrepot"), ("hall_production", "atelier_maintenance")
    }  # fmt: skip
    with pytest.raises(LayoutError):
        layout.default_plan(REAL, 4, 1)


# --- place_campus -------------------------------------------------------------------------------------------------


def valid(spec: dict[str, Any]) -> None:
    SimSpec.model_validate(spec)
    assert check_placement(spec, load_pack("usine")) == []


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("buildings", [1, 2, 3])
def test_every_seed_and_building_count_gives_a_valid_world(seed: int, buildings: int) -> None:
    spec = gen(seed, buildings)
    valid(spec)
    world = spec["world"]
    assert len(world["buildings"]) == (buildings if buildings > 1 else 0)
    assert world["template"] == ("campus" if buildings > 1 else "usine")
    assert (spec["factory"]["logistics"]["walk_m_per_min"] is not None) == (buildings > 1)


@pytest.mark.parametrize("plan", PLANS)
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_each_valid_plan_of_the_factory(plan: str, seed: int) -> None:
    spec = gen(seed, plan=plan)
    valid(spec)
    assert [b["archetype"] for b in spec["world"]["buildings"]] == PLANS[plan]


def test_campus_world_shape() -> None:
    spec = gen(3, 3)
    world = spec["world"]
    b1 = world["buildings"][0]
    assert set(b1) == {"id", "archetype", "label", "area", "entrance", "style", "walls", "door"}
    assert (b1["walls"], b1["door"]) == ("prop_wall_panel", "prop_door_industrial")
    assert world["ambiance"] == "zone_industrielle" and world["size"] == [
        b1["area"][2] - b1["area"][0],
        b1["area"][3] - b1["area"][1],
    ]
    assert world["decor"]["items"]
    rooms = {r["id"]: r for r in world["rooms"]}
    interior = {d["id"] for d in spec["departments"] if not d["external"]}
    assert {r["department_ids"][0] for r in rooms.values()} == interior  # une pièce par département
    assert all(d["room_id"] in rooms for d in spec["departments"] if d["id"] in interior)
    assert all(b["area"][3] == world["buildings"][0]["area"][3] for b in world["buildings"])  # quais côté camions
    assert world["spawn"][1] < b1["area"][1]  # devant l'entrée de b1, au nord


def test_same_seed_same_world_and_different_seeds_differ() -> None:
    again = generate(GameParams(**default_params("usine") | {"seed": 5, "weeks": 4, "buildings": 3}))
    assert again == gen(5, 3)
    prints = {n: {layout.world_fingerprint(gen(s, n)["world"]) for s in SEEDS} for n in (2, 3)}
    assert len(prints[3]) >= 8 and len(prints[2]) >= 6


def test_single_building_is_the_reference_game() -> None:
    reference, one = gen(4, None), gen(4, 1)
    assert reference | {"params": None} == one | {"params": None}
    world = reference["world"]
    assert (world["template"], world["buildings"], world["rooms"], world["ambiance"]) == ("usine", [], [], None)
    assert reference["factory"]["logistics"]["walk_m_per_min"] is None
    assert all(d["room_id"] is None for d in reference["departments"])


def test_forklift_route_goes_around_the_buildings() -> None:
    spec = gen(2, plan="entrepot")
    route = spec["world"]["forklift_route"]
    assert len(route) > 7  # les points de trajet entre bâtiments sont insérés
    assert all(len(p) == 2 for p in route)


def test_the_world_uses_the_pack_style_of_the_ambiance() -> None:
    styles = set(REAL["ambiances"]["zone_industrielle"]["styles"])
    assert all(b["style"] in styles for b in gen(6, 3)["world"]["buildings"])


# --- repli, échec, zonage, durée ---------------------------------------------------------------------------------


def test_reference_layout_after_refused_draws_then_layout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # hall + atelier : la référence des plans avec entrepôt est refusée par postes_proteges_chariots (bureau à 1,3 m)
    spec, plan = make_spec() | {"seed": 4}, layout.default_plan(REAL, 2, 4)
    real, calls = layout.check_placement, []

    def refuse_draws(s: dict[str, Any], pack: dict[str, Any]) -> list[str]:
        calls.append(1)
        return ["tirage refusé"] if len(calls) <= layout.CAMPUS_TRIES else real(s, pack)

    monkeypatch.setattr(layout, "check_placement", refuse_draws)
    start = time.perf_counter()
    bundle = place_campus(spec, REAL, plan, 4)
    print(f"\n{layout.CAMPUS_TRIES} tirages refusés puis référence : {time.perf_counter() - start:.2f} s")
    assert len(calls) == layout.CAMPUS_TRIES + 1
    assert [b["id"] for b in bundle["world"]["buildings"]] == ["b1", "b2"]  # référence : ordre du plan
    monkeypatch.setattr(layout, "check_placement", lambda s, p: ["toujours refusé"])
    with pytest.raises(LayoutError, match="référence est refusée"):
        place_campus(spec, REAL, plan, 4)
    with pytest.raises(LayoutError, match="au moins deux"):
        place_campus(spec, REAL, plan[:1], 4)


def test_a_group_too_large_for_its_archetype_is_an_error() -> None:
    plan = [{"archetype": "atelier_maintenance", "department_ids": ["production"]},
            {"archetype": "hall_production", "department_ids": ["maintenance"]}]  # fmt: skip
    with pytest.raises(LayoutError):
        place_campus(make_spec(), REAL, plan, 1)


def test_zoning_and_timed_links_are_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = gen(1, plan="trois")
    pack = load_pack("usine")
    monkeypatch.setattr(layout, "TIMED_LINKS", {})
    msgs = check_placement(spec, pack)
    assert any("passage non chronométré entre bâtiments : stock_mp -> production" in m for m in msgs)
    assert any("emballage -> entrepot_pf" in m for m in msgs)
    monkeypatch.undo()
    tight = copy.deepcopy(pack)
    tight["values"]["zonage.marche_max_maintenance_m"]["value"] = 10
    assert any("max_walk_m" in m and "10 m au plus" in m for m in check_placement(spec, tight))
    joined = copy.deepcopy(spec)  # réception et quai dans deux bâtiments : `together` refusé
    room = next(r for r in joined["world"]["rooms"] if r["id"].endswith(".quai"))
    other = next(b["id"] for b in joined["world"]["buildings"] if b["id"] != room["building_id"])
    for d in joined["departments"]:
        if d["id"] == "quai":
            d["room_id"] = f"{other}.quai"
    room["id"], room["building_id"] = f"{other}.quai", other
    assert any("quai" in m and "together" in m for m in check_placement(joined, pack))


def test_buildings_too_close_or_off_the_grid_are_refused() -> None:
    spec = copy.deepcopy(gen(1, 2))
    left, right = sorted(spec["world"]["buildings"], key=lambda b: b["area"][0])
    shift = left["area"][2] + 2 - right["area"][0]  # 2 m d'allée seulement
    right["area"][0] += shift
    right["area"][2] += shift
    right["entrance"][0] += shift
    msgs = check_placement(spec, load_pack("usine"))
    assert any("moins d'une cellule" in m for m in msgs)
    left["area"][0] += 1  # hors de la grille de 4 m
    assert any("pas aligné sur la grille" in m for m in check_placement(spec, load_pack("usine")))


# --- le moteur lit les trajets (étapes 5, 6 et 8) --------------------------------------------------------------


def _plant_and_fs(buildings: int) -> tuple[factory.Plant, dict[str, Any]]:
    plant = factory.Plant(gen(5, buildings))
    fs = factory.initial_state(plant)
    factory.launch_of(plant, fs, plant.line_ids[0], 10)
    return plant, fs


def test_single_building_reference_numbers_do_not_change() -> None:
    spec = gen(5, 1)
    plant = factory.Plant(spec)
    assert (plant.kit_t, plant.walk_t, plant.pal_h) == (0.0, spec["factory"]["logistics"]["repair_travel_min"], None)
    state = engine.start(spec, engine.initial_state(spec))
    seen = []
    for _ in range(3):
        state = engine.advance(spec, state, autopilot_all=True)
        seen.append((state["cash"], state["history"][-1]["otif"], state["history"][-1]["trs"]))
    assert seen == [(38962.0, 100.0, 84.4), (52158.0, 100.0, 81.9), (67936.0, 100.0, 83.7)]
    assert "transit" not in state["fs"]["fk"]


def test_kit_and_technician_durations_follow_the_trips() -> None:
    plant, fs = _plant_and_fs(3)
    spec = gen(5, 3)
    t_kit = travel_min(spec, "stock_mp", "production", "chariot")
    assert plant.kit_t == pytest.approx(t_kit) and plant.walk_t == pytest.approx(
        travel_min(spec, "maintenance", "production", "marche")
    )
    sim = factory._Sim(plant, copy.deepcopy(fs), 1, {})
    sim.run()
    kits = [e[0] for e in sim.events if e[1] == "kit_livre"]
    kit_min = spec["factory"]["logistics"]["kit_min"]
    assert kits[0] == pytest.approx(kit_min + t_kit, abs=0.01)  # remis à 8 + t
    assert kits[1] == pytest.approx(kits[0] + t_kit + kit_min + t_kit, abs=0.02)  # chariot libre à 8 + 2t


def test_pallet_in_transit_is_delivered_and_saved_across_turns() -> None:
    plant, fs = _plant_and_fs(3)
    assert plant.pal_h == 1 and plant.pal_t > 0
    fs["fk"], fs["seq"] = {"busy": 1, "transit": 1}, 3
    fs["events"] = [[0.5, 0, 1, "pdel", 0, 0], [1.0, 0, 2, "fkfree", 0, 0]]
    sim = factory._Sim(plant, copy.deepcopy(fs), 1, {})
    sim.run()
    assert [e[0] for e in sim.events if e[1] == "palette"][:1] == [0.5] and sim.transit == 0
    fs["events"] = [[plant.T + 10.0, 0, 1, "pdel", 0, 0], [plant.T + 11.0, 0, 2, "fkfree", 0, 0]]
    saved, _, _ = factory.simulate(plant, fs, 1)
    assert saved["fk"] == {"busy": 1, "transit": 1}
    assert [(e[0], e[3]) for e in saved["events"] if e[3] in ("pdel", "fkfree")] == [(10.0, "pdel"), (11.0, "fkfree")]
    after, _, _ = factory.simulate(plant, saved, 2)
    assert after["fk"]["transit"] == 0 and after["fk"]["busy"] == 0


def test_campus_pallets_take_the_forklift_and_arrive() -> None:
    plant, fs = _plant_and_fs(3)
    sim = factory._Sim(plant, copy.deepcopy(fs), 1, {})
    sim.run()
    assert sim.packed["pallets"] >= 1 and sim.transit in (0, 1)


def test_pack_coverage_counts_walls_and_doors() -> None:
    needed = layout.required_assets(REAL)
    assert {"prop_wall_panel", "prop_door_industrial"} <= needed
    assert layout.pack_coverage("usine")["ratio"] == 1.0
