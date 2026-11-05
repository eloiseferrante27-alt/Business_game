"""Placeur déterministe (gmix.game.layout, ADR 0009) : placement, règles du pack, retouches du formateur, délais."""

import copy
import time
from typing import Any

import pytest

from gmix.assets_catalog import AssetCatalog, load_assets_catalog
from gmix.game import layout
from gmix.game.spec import LayoutEdit, load_pack

PACK = load_pack("usine")
BUDGET_S = 0.05


def make_spec(lines: int = 3, network: dict[str, str] | None = None) -> dict[str, Any]:
    """Spec minimale lue par le placeur : machines, capacités, offres, agents et postes."""
    machines = [
        {"id": f"l{ln}-m{r}", "line_id": f"l{ln}", "rank": r, "name": f"M{r}", "asset": "prop_machine"}
        for ln in range(1, lines + 1)
        for r in range(1, 5)
    ]
    return {
        "params": {"network": network or {}},
        "lines": [{"id": f"l{ln}"} for ln in range(1, lines + 1)],
        "factory": {
            "machines": machines, "bom": [{"component_id": "c1", "per_unit": 1}, {"component_id": "c2", "per_unit": 1}],
            "logistics": {"mp_capacity_pallets": 24, "pf_capacity_pallets": 20},
        },
        "offers": [{"supplier_id": f"s_{p}", "profile": p} for p in ("rapide", "standard", "economique")],
        "agents": [{"id": "agent_reception", "department_id": "reception"}, {"id": "agent_x"}],
        "stations": [
            {"id": "st_rec", "kind": "poste_reception", "department_id": "reception", "ref": None},
            {"id": "st_m1", "kind": "machine", "department_id": "production", "ref": "l1-m1"},
        ],
    }  # fmt: skip


def spec_with_plan(bundle: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """La spec telle que l'API la complétera : départements (aire, grille) et monde posé."""
    return spec | {
        "departments": [
            {k: d[k] for k in ("id", "label", "external", "block", "area", "grid")} for d in bundle["departments"]
        ],
        "world": bundle["world"],
    }  # fmt: skip


def pack_without(*, element: str | None = None, rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pack = copy.deepcopy(PACK)
    if element:  # retire un élément du pack (isoler une règle de placement)
        for dep in pack["departments"]:
            dep["elements"] = [e for e in dep.get("elements", []) if e.get("label") != element]
    if rules is not None:
        pack["placement_rules"] = rules
    return pack


@pytest.fixture(scope="module")
def bundle() -> dict[str, Any]:
    return layout.place_world(make_spec(), PACK)


# --- placement --------------------------------------------------------------------------------------------------


def test_same_spec_gives_the_same_world_within_the_time_budget() -> None:
    spec = make_spec()
    layout.place_world(spec, PACK)  # chauffe : catalogue des empreintes chargé une fois
    start = time.perf_counter()
    first = layout.place_world(spec, PACK)
    assert time.perf_counter() - start < BUDGET_S
    assert first == layout.place_world(copy.deepcopy(spec), PACK)
    assert first != layout.place_world(make_spec(lines=1), PACK)


def test_every_machine_has_an_object_and_a_station_and_nothing_overlaps(bundle: dict[str, Any]) -> None:
    refs = {o["ref"] for o in bundle["world"]["objects"]}
    assert {f"machine:l{ln}-m{r}" for ln in (1, 2, 3) for r in range(1, 5)} <= refs
    ids = [o["id"] for o in bundle["world"]["objects"]]
    assert len(ids) == len(set(ids))
    assert {s["id"] for s in bundle["stations"]} == {"st_rec", "st_m1"}
    assert bundle["agents"]["agent_reception"]["route"] and "agent_x" not in bundle["agents"]
    assert pytest.approx(bundle["world"]["bounds"][1]) == -15  # le hall commence à -15, les sites sont au sud


def test_racks_follow_the_capacity_and_raw_material_refs(bundle: dict[str, Any]) -> None:
    racks = [
        o for o in bundle["world"]["objects"] if o["asset"] == "prop_pallet_rack" and o["department_id"] == "stock_mp"
    ]
    assert len(racks) == 4  # 24 emplacements / 6 par rack
    assert {r["ref"] for r in racks} == {"mp:c1", "mp:c2"}


def test_the_reference_plan_places_every_pack_element(bundle: dict[str, Any]) -> None:
    assert layout.check_placement(spec_with_plan(bundle, make_spec()), PACK) == []


def test_a_line_that_does_not_fit_is_refused() -> None:
    with pytest.raises(layout.LayoutError, match="ne tient pas"):
        layout.place_world(make_spec(lines=7), PACK)


def test_without_network_there_is_no_external_site() -> None:
    pack = copy.deepcopy(PACK)
    del pack["network"]
    b = layout.place_world(make_spec(), pack)
    assert b["world"]["sites"] == [] and b["world"]["links"] == []
    assert [d["id"] for d in b["departments"] if d["external"]] == []


def test_sites_and_links_come_from_the_network(bundle: dict[str, Any]) -> None:
    sites = {s["id"]: s for s in bundle["world"]["sites"]}
    assert list(sites)[0] == "usine" and sites["usine"]["area"] == [-24, -15, 24, 15]
    assert (
        sites["fournisseur_economique"]["distance_class"] == "national" and sites["fournisseur_economique"]["km"] == 800
    )
    assert sites["fournisseur_economique"]["supplier_id"] == "s_economique"
    assert {link["from_site"] for link in bundle["world"]["links"]} == set(sites) - {"usine"}
    assert all(link["to_site"] == "usine" and link["points"][-1] == [0.0, 15] for link in bundle["world"]["links"])
    b = layout.place_world(make_spec(network={"fournisseur_economique": "import"}), PACK)
    far = {s["id"]: s for s in b["world"]["sites"]}["fournisseur_economique"]
    assert far["km"] == 1300 and far["transit_days"] == 3


# --- délais -----------------------------------------------------------------------------------------------------


def test_lead_time_is_prep_plus_driving_days_between_1_and_8() -> None:
    spec = make_spec()
    assert [
        layout.site_lead_days(spec, PACK, s)
        for s in ("fournisseur_rapide", "fournisseur_standard", "fournisseur_economique")
    ] == [1, 3, 5]
    assert (
        layout.site_lead_days(make_spec(network={"fournisseur_economique": "import"}), PACK, "fournisseur_economique")
        == 6
    )
    assert layout.lead_days(0, 1, 70, 9) == 1  # plancher
    assert layout.lead_days(7, 5000, 70, 9) == 8  # plafond


# --- règles de placement ----------------------------------------------------------------------------------------


def rule(kind: str, **kw: Any) -> dict[str, Any]:
    return {"id": f"r_{kind}", "kind": kind} | kw


def violations(bundle: dict[str, Any], r: dict[str, Any], pack: dict[str, Any] | None = None) -> list[str]:
    base = pack_without(element="Préparation des commandes", rules=[r]) if pack is None else pack
    return layout.check_placement(spec_with_plan(bundle, make_spec()), base)


def test_adjacent_rule(bundle: dict[str, Any]) -> None:
    assert violations(bundle, rule("adjacent", a="reception", b="quai")) == []
    assert "r_adjacent" in violations(bundle, rule("adjacent", a="reception", b="qualite"))[0]


def test_flow_rule(bundle: dict[str, Any]) -> None:
    assert violations(bundle, rule("flow", blocks=["reception", "stock_mp", "production"])) == []
    assert "r_flow" in violations(bundle, rule("flow", blocks=["reception", "pilotage"]))[0]


def test_separated_rule(bundle: dict[str, Any]) -> None:
    assert violations(bundle, rule("separated", a="quarantine", b="mp", min_m=2.5)) == []
    assert "r_separated" in violations(bundle, rule("separated", a="quarantine", b="mp", min_m=500))[0]
    assert "introuvable" in violations(bundle, rule("separated", a="nulle_part", b="mp", min_m=1))[0]


def test_near_rule(bundle: dict[str, Any]) -> None:
    assert violations(bundle, rule("near", a="reception", b="quai", max_m=3)) == []
    assert "r_near" in violations(bundle, rule("near", a="reception", b="qualite", max_m=3))[0]


def test_aisle_min_rule(bundle: dict[str, Any]) -> None:
    assert violations(bundle, rule("aisle_min", min_m=2.5)) == []
    assert "r_aisle_min" in violations(bundle, rule("aisle_min", min_m=4))[0]


def test_facing_rule(bundle: dict[str, Any]) -> None:
    assert violations(bundle, rule("facing", block="pilotage", role="affichage", toward="front")) == []
    spec = spec_with_plan(copy.deepcopy(bundle), make_spec())
    for o in spec["world"]["objects"]:
        if o["department_id"] == "pilotage" and o["role"] == "affichage":
            o["rotation"] = (o["rotation"] + 180) % 360
    pack = pack_without(
        element="Préparation des commandes", rules=[rule("facing", block="pilotage", role="affichage", toward="front")]
    )
    assert "r_facing" in layout.check_placement(spec, pack)[0]


def test_integrity_reports_overlaps_and_objects_outside_the_grid(bundle: dict[str, Any]) -> None:
    spec = spec_with_plan(copy.deepcopy(bundle), make_spec())
    objs = [o for o in spec["world"]["objects"] if o["department_id"] == "production" and o["cell"]]
    objs[1]["cell"] = list(objs[0]["cell"])
    objs[2]["cell"] = [999, 0]
    msgs = layout.check_placement(spec, pack_without(element="Préparation des commandes", rules=[]))
    assert any("se chevauchent" in m for m in msgs) and any("sort de la grille" in m for m in msgs)


# --- retouches du formateur -------------------------------------------------------------------------------------


def free_cell(bundle: dict[str, Any], dept_id: str, skip: int = 0) -> list[int]:
    """Une cellule du bloc sans objet ni allée ni devant de poste (hors halo, pour ne rien supposer)."""
    dep = next(d for d in bundle["departments"] if d["id"] == dept_id)
    taken = {tuple(c) for c in dep["grid"]["reserved"]}
    for o in bundle["world"]["objects"]:
        if o.get("department_id") == dept_id and o.get("cell"):
            c, r = o["cell"]
            taken |= {(c + i, r + j) for i in range(o["cells"][0]) for j in range(o["cells"][1])}
    free = [[c, r] for r in range(dep["grid"]["rows"]) for c in range(dep["grid"]["cols"]) if (c, r) not in taken]
    return free[skip]


def edit(bundle: dict[str, Any], *edits: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return layout.apply_edits(bundle, [LayoutEdit(**e) for e in edits], PACK)


def only_reason(bundle: dict[str, Any], e: dict[str, Any]) -> str:
    new, rejected = layout.apply_edits(bundle, [e], PACK)
    assert len(rejected) == 1 and rejected[0]["index"] == 0 and rejected[0]["message"]
    assert new["world"] == bundle["world"]  # une retouche refusée ne change rien
    return rejected[0]["reason"]


def test_add_move_and_remove_a_decor_object(bundle: dict[str, Any]) -> None:
    c1, c2 = free_cell(bundle, "reception"), free_cell(bundle, "reception", skip=40)
    new, rejected = edit(bundle, {"op": "add", "department_id": "reception", "asset": "furn_plant", "cell": c1})
    assert rejected == []
    plant = next(o for o in new["world"]["objects"] if o["id"] == "reception.ajout.0")
    assert plant["role"] == "decor" and plant["ref"] is None and plant["cell"] == c1
    moved, rejected = layout.apply_edits(
        new, [LayoutEdit(op="move", object_id=plant["id"], cell=tuple(c2), rot=90)], PACK
    )
    assert rejected == []
    plant = next(o for o in moved["world"]["objects"] if o["id"] == plant["id"])
    assert plant["cell"] == c2 and plant["rotation"] == 90
    gone, rejected = layout.apply_edits(moved, [LayoutEdit(op="remove", object_id=plant["id"])], PACK)
    assert rejected == [] and all(o["id"] != plant["id"] for o in gone["world"]["objects"])
    assert len(bundle["world"]["objects"]) == len(gone["world"]["objects"])  # l'entrée n'est pas modifiée


def test_each_rejection_reason(bundle: dict[str, Any]) -> None:
    dep = next(d for d in bundle["departments"] if d["id"] == "reception")
    objs = [o for o in bundle["world"]["objects"] if o["department_id"] == "reception"]
    desk = next(o for o in objs if o["role"] == "poste")
    jack = next(o for o in objs if o["role"] == "engin")
    door = next(o for o in bundle["world"]["objects"] if o["role"] == "porte")
    front = layout._edge_cell(*desk["cell"], *desk["cells"], *layout.ROT_VEC[int(desk["rotation"])])
    aisle = bundle["aisles"]["reception"][0]
    add = {"op": "add", "department_id": "reception", "asset": "furn_plant"}
    assert only_reason(bundle, {"op": "move", "object_id": "nul", "cell": [0, 0]}) == "cible_inconnue"
    assert (
        only_reason(bundle, add | {"asset": "prop_machine", "cell": free_cell(bundle, "reception")})
        == "asset_non_permis"
    )
    assert only_reason(bundle, add | {"cell": [dep["grid"]["cols"], 0]}) == "hors_bloc"
    assert only_reason(bundle, add | {"cell": list(front)}) == "devant_poste"
    assert only_reason(bundle, add | {"cell": aisle}) == "allee"
    assert only_reason(bundle, add | {"cell": jack["cell"]}) == "occupe"
    assert only_reason(bundle, {"op": "remove", "object_id": jack["id"]}) == "role_fixe"
    assert (
        only_reason(bundle, {"op": "move", "object_id": door["id"], "cell": free_cell(bundle, door["department_id"])})
        == "role_fixe"
    )


def test_moving_a_workstation_recomputes_its_station_position(bundle: dict[str, Any]) -> None:
    desk = next(o for o in bundle["world"]["objects"] if o["department_id"] == "reception" and o["role"] == "poste")
    before = next(s for s in bundle["stations"] if s["id"] == "st_rec")["position"]
    for k in range(0, 200, 7):  # première cellule où le poste tient (devant libre, hors allée)
        new, rejected = layout.apply_edits(
            bundle, [{"op": "move", "object_id": desk["id"], "cell": free_cell(bundle, "reception", k)}], PACK
        )
        if not rejected:
            break
    assert not rejected and next(s for s in new["stations"] if s["id"] == "st_rec")["position"] != before


def test_two_hundred_edits_are_applied_within_the_time_budget(bundle: dict[str, Any]) -> None:
    a, b = free_cell(bundle, "reception"), free_cell(bundle, "reception", skip=40)
    plant = {"op": "add", "department_id": "reception", "asset": "furn_plant", "cell": a}
    edits = [plant] + [{"op": "move", "object_id": "reception.ajout.0", "cell": (b, a)[i % 2]} for i in range(199)]
    layout.apply_edits(bundle, edits, PACK)  # chauffe
    start = time.perf_counter()
    new, rejected = layout.apply_edits(bundle, edits, PACK)
    assert time.perf_counter() - start < BUDGET_S and rejected == []
    with pytest.raises(ValueError, match="200"):
        layout.apply_edits(bundle, edits + [plant], PACK)


def test_recompile_layout_updates_world_routes_and_keeps_the_input(bundle: dict[str, Any]) -> None:
    spec = spec_with_plan(bundle, make_spec()) | {"layout_edits": []}
    spec["agents"] = [a | {"route": [[0, 0]]} for a in spec["agents"]]
    before = copy.deepcopy(spec)
    cell = free_cell(bundle, "reception")
    add = {"op": "add", "department_id": "reception", "asset": "furn_plant", "cell": cell}
    new, rejected = layout.recompile_layout(spec, PACK, [add, {"op": "remove", "object_id": "nul"}])
    assert spec == before  # l'entrée n'est pas modifiée
    assert [r["index"] for r in rejected] == [1] and len(new["layout_edits"]) == 2
    assert any(o["id"] == "reception.ajout.0" for o in new["world"]["objects"])
    assert next(a for a in new["agents"] if a["id"] == "agent_reception")["route"] != [[0, 0]]
    assert next(s for s in new["stations"] if s["id"] == "st_rec")["position"] != [0.0, 0.0]


# --- assets du pack ---------------------------------------------------------------------------------------------


def test_usine_pack_assets_are_all_in_the_catalog() -> None:
    cover = layout.pack_coverage("usine")
    assert cover["ratio"] == 1.0 and cover["missing"] == []
    assert {"prop_machine", "bld_factory_plant", "veh_box_truck"} <= set(cover["required"])
    assert "furn_plant" not in cover["required"]  # la palette du formateur n'est pas exigée


def test_an_asset_to_source_counts_as_missing() -> None:
    cat = load_assets_catalog().model_dump()
    next(a for a in cat["assets"] if a["id"] == "veh_box_truck")["status"] = "a_sourcer"
    cover = layout.pack_coverage("usine", AssetCatalog(**cat))
    assert cover["missing"] == ["veh_box_truck"] and cover["ratio"] < 1


# --- chemin protégé (annexe 0010 §8) -------------------------------------------------------------------------------


def _path_world(links: list[dict[str, Any]], objects: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    def at(ref: str, x: float) -> dict[str, Any]:
        return {"id": ref, "ref": ref, "position": [x, 0.0], "rotation": 0, "cells": [2, 2], "role": "stockage"}

    return {
        "departments": [],
        "world": {"links": links, "forklift_route": [], "objects": [at("a", 0), at("b", 10), *(objects or [])]},
    }  # noqa: E501


def _link(lid: str, a: str, b: str, points: list[list[float]]) -> dict[str, Any]:
    return {"id": lid, "type": "route", "from_site": a, "to_site": b, "points": points}


def test_protected_path_rule_gives_three_control_messages() -> None:
    r = {
        "id": "chemin",
        "kind": "protected_path",
        "a": "a",
        "b": "b",
        "barrier": True,
        "crossings_max": 0,
        "one_way": True,
    }
    pack = {"placement_rules": [r], "departments": []}
    main = _link("l1", "a", "b", [[0.0, 0.0], [10.0, 0.0]])
    assert layout.check_placement(_path_world([]), pack) == ["règle chemin : aucune circulation entre a et b."]
    assert layout.check_placement(_path_world([main]), pack) == []
    cross = _link("l2", "c", "d", [[5.0, -3.0], [5.0, 3.0]])
    assert (
        "croise 1 fois une autre circulation, 0 au plus" in layout.check_placement(_path_world([main, cross]), pack)[0]
    )
    back = _link("l3", "b", "a", [[10.0, 0.0], [0.0, 0.0]])
    assert layout.check_placement(_path_world([main, back]), pack) == [
        "règle chemin : le chemin a -> b est à double sens."
    ]
    desk = {
        "id": "p1",
        "position": [5.0, 1.0],
        "rotation": 0,
        "asset": "prop_desk",
        "role": "poste",
        "label": "Poste test",
    }
    msg = layout.check_placement(_path_world([main], [desk]), pack)
    assert len(msg) == 1 and "« Poste test » à 1.0 m du chemin a -> b, sans barrière" in msg[0]
    fence = {"id": "g1", "position": [5.0, 1.2], "rotation": 0, "asset": "prop_safety_barrier", "role": "barriere"}
    assert layout.check_placement(_path_world([main], [desk, fence]), pack) == []
