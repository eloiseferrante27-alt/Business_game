"""Pièces de rechange du pack usine (annexe 0013 §3 quater) : stock par type de machine, attente de pièce, commandes,
coûts. Les tests construisent la spec avec `spares` à la main et pilotent `_Sim` événement par événement."""

import copy
import heapq
import json
import math
from typing import Any

import pytest
from pydantic import ValidationError

from gmix.game import engine, factory, factory_game
from gmix.game.factory_game import initial_state as game_state
from gmix.game.generation import generate
from gmix.game.spec import COUNTERS, GameParams, SimSpec, Timeline, load_pack

SPARES = {"price": 150.0, "lead_days": 1, "service_level": 0.99}


def _base() -> dict[str, Any]:
    return generate(GameParams(pack="usine", theme="industrie", modules=["pilotage", "production", "maintenance"],
                               difficulty="equilibre", seed=5, weeks=6, options={"lines": 2}))  # fmt: skip


def _spec(**spares: Any) -> dict[str, Any]:
    spec = _base()
    spec["factory"]["spares"] = SPARES | spares
    return spec


def _sim(spec: dict[str, Any], fs: dict[str, Any] | None = None) -> tuple[factory.Plant, factory._Sim]:
    plant = factory.Plant(spec)
    return plant, factory._Sim(plant, copy.deepcopy(fs or factory.initial_state(plant)), 1, {})


def _pop(sim: factory._Sim, kind: str) -> None:
    """Joue le prochain événement `kind` du tas."""
    ev = next(e for e in sorted(sim.h) if e[3] == kind)
    sim.h.remove(ev)
    heapq.heapify(sim.h)
    sim.disp[kind](ev[0], ev[4], ev[5])


def _kinds(sim: factory._Sim, kind: str) -> list[list[Any]]:
    return [e for e in sim.events if e[1] == kind]


def test_poisson_stock_is_smallest_s_meeting_service_level() -> None:
    for mean, level in [(0.05, 0.99), (0.4, 0.99), (3.0, 0.95)]:
        s = factory._poisson_stock(mean, level)

        def tail(k: int, mean: float = mean) -> float:
            return 1 - sum(math.exp(-mean) * mean**j / math.factorial(j) for j in range(k))

        assert s >= 1 and tail(s) <= 1 - level and (s == 1 or tail(s - 1) > 1 - level)


def test_initial_state_stock_is_s_star_per_type() -> None:
    plant, sim = _sim(_spec())
    fs = factory.initial_state(plant)
    assert set(plant.types) == set(plant.mtype) and plant.s_star
    assert fs["spares"]["stock"] == fs["spares"]["target"] == plant.s_star
    assert fs["settings"]["spares"] is None and fs["spares"]["reserved"] == []


def test_stock_available_repair_takes_mttr_and_uses_a_piece() -> None:
    plant, sim = _sim(_spec())
    t = plant.mtype[0]
    before = sim.sp["stock"][t]
    sim._rstart(100.0, 0, 0)
    assert sim.sp["stock"][t] == before - 1 and sim.sp_stat["used"] == 1
    assert [e for e in sim.h if e[3] == "rep"][0][0] == pytest.approx(100.0 + sim.M[0].mttr)
    assert not _kinds(sim, "attente_piece")


def test_empty_stock_waits_then_repairs_on_arrival() -> None:
    spec = _spec(lead_days=2)
    plant, sim = _sim(spec)
    t, mpd = plant.mtype[0], plant.mpd
    sim.sp["stock"][t] = 0
    sim.tech_busy = 1
    sim._rstart(100.0, 0, 0)
    assert sim.sp["waiting"][t] == [[100.0, 0]] and sim.tech_busy == 0 and sim.sp_stat["missing"] == 1
    arrival = (100.0 // mpd + 2) * mpd
    assert _kinds(sim, "attente_piece")[0][3]["duration_min"] == pytest.approx(arrival - 100.0)
    assert sim.sp["transit"][t] == plant.s_star[t] + 1  # cible + la machine qui attend
    assert not [e for e in sim.h if e[3] == "rep"]
    _pop(sim, "spare")
    assert sim.sp["reserved"] == [0] and sim.sp["waiting"][t] == [] and sim.tech_busy == 1
    assert sim.sp_stat["wait_min"] == pytest.approx(arrival - 100.0)
    _pop(sim, "rstart")  # le technicien revient : la pièce réservée, pas de nouveau prélèvement
    assert sim.sp["reserved"] == [] and sim.sp["stock"][t] == 0
    assert [e for e in sim.h if e[3] == "rep"][0][0] == pytest.approx(arrival + plant.walk_t + sim.M[0].mttr)


def test_two_machines_of_a_type_wait_in_fifo_order() -> None:
    spec = _spec()
    for m in spec["factory"]["machines"][:2]:
        m["type"] = "tx"
    plant, sim = _sim(spec)
    assert plant.mtype[0] == plant.mtype[1] == "tx"
    sim.sp["stock"]["tx"] = 0
    sim.tech_busy = 2
    sim._rstart(100.0, 0, 0)
    sim._rstart(110.0, 1, 0)
    assert sim.sp["waiting"]["tx"] == [[100.0, 0], [110.0, 1]] and len(_kinds(sim, "attente_piece")) == 2
    _pop(sim, "spare")
    assert sim.sp["reserved"] == [0] and sim.sp["waiting"]["tx"] == [[110.0, 1]]
    _pop(sim, "spare")
    assert sim.sp["reserved"] == [0, 1] and sim.sp["waiting"]["tx"] == []


def _quiet(spec: dict[str, Any]) -> dict[str, Any]:
    for m in spec["factory"]["machines"]:
        m["mtbf_h"] = 1e9  # aucune panne : seuls les achats et la possession comptent
    return spec


def test_order_cost_and_holding_cost() -> None:
    spec = _quiet(_spec(price=200.0))
    plant = factory.Plant(spec)
    fs = factory.initial_state(plant)
    fs["settings"]["spares"] = {"cible": "toutes", "pieces": 3}
    _, _, rep = factory.simulate(plant, fs, 1)
    sp, n = rep["spares"], sum(3 - s for s in plant.s_star.values())
    assert sp["bought"] == n and sp["purchase"] == 200.0 * n and sp["used"] == 0
    # stock moyen pondéré : S* jusqu'à l'ouverture du jour 2, puis 3 par type
    area = sum(s * plant.mpd + 3 * (plant.T - plant.mpd) for s in plant.s_star.values())
    assert sp["holding"] == pytest.approx(plant.hold_rate * 200.0 * area / plant.T, abs=0.01)
    assert rep["costs"]["spares"] == pytest.approx(sp["purchase"] + sp["holding"], abs=0.01)


@pytest.mark.parametrize("cible", ["aucune", "goulot", "toutes"])
def test_player_target_follows_cible_and_pieces(cible: str) -> None:
    spec = _quiet(_spec())
    plant = factory.Plant(spec)
    fs = factory.initial_state(plant)
    fs["settings"]["spares"] = {"cible": cible, "pieces": 2}
    new, _, rep = factory.simulate(plant, fs, 1)
    covered = {"aucune": set(), "goulot": {plant.mtype[b] for b in plant.bottleneck}, "toutes": set(plant.types)}
    assert new["spares"]["target"] == {t: 2 if t in covered[cible] else 0 for t in plant.types}
    assert rep["spares"]["bought"] == sum(max(2 - plant.s_star[t], 0) for t in covered[cible])
    for t in plant.types:  # un surplus s'use sans être recommandé
        assert new["spares"]["stock"][t] == (max(2, plant.s_star[t]) if t in covered[cible] else plant.s_star[t])


def test_pilot_week_keeps_s_star_and_weeks_chain() -> None:
    spec = _spec()
    plant = factory.Plant(spec)
    fs = factory.initial_state(plant)
    for week in (1, 2, 3):
        fs, _, rep = factory.simulate(plant, fs, week)
        assert json.loads(json.dumps(fs)) == fs  # état JSON, dates relatives
        assert fs["spares"]["target"] == plant.s_star
        assert all(v >= 0 for v in fs["spares"]["stock"].values())
        sp = fs["spares"]  # position (stock + en route - en attente) toujours reconstituée à la cible
        assert all(sp["stock"][t] + sp["transit"][t] - len(sp["waiting"][t]) >= sp["target"][t] for t in sp["stock"])
        assert rep["spares"]["bought"] >= rep["spares"]["used"] - sum(plant.s_star.values()) * (week == 1)


def test_spec_without_spares_keeps_state_and_report_shape() -> None:
    spec = _base()
    assert spec["factory"]["spares"] == SPARES  # le pack usine en déclare maintenant
    del spec["factory"]["spares"]
    plant = factory.Plant(spec)
    fs = factory.initial_state(plant)
    assert "spares" not in fs and "spares" not in fs["settings"]
    new, tl, rep = factory.simulate(plant, fs, 1)
    assert "spares" not in new and "spares" not in rep and "spares" not in rep["costs"]
    assert not [e for e in tl["events"] if e[1] == "attente_piece"]
    assert "spares" not in game_state(spec)["fs"]["settings"]


# --- contrat (annexe 0013 §3 quater) ------------------------------------------------------------------------------


def test_contract_example_is_valid_and_roundtrips() -> None:
    spec = _base()
    spec["factory"]["spares"] = dict(SPARES, price=150)
    spec["factory"]["costs"]["damage_per_failure"] = 50
    back = SimSpec.model_validate(spec).model_dump(mode="json")
    assert back["factory"]["spares"] == {"price": 150, "lead_days": 1, "service_level": 0.99}
    assert back["factory"]["costs"]["damage_per_failure"] == 50


@pytest.mark.parametrize(
    ("field", "value"),
    [("lead_days", 0), ("lead_days", 6), ("service_level", 0), ("service_level", 1), ("price", -1)],
)
def test_contract_refusals(field: str, value: float) -> None:
    spec = _spec(**{field: value})
    with pytest.raises(ValidationError) as err:
        SimSpec.model_validate(spec)
    assert ("factory", "spares", field) in [tuple(e["loc"][-3:]) for e in err.value.errors()]


def test_contract_attente_piece_event_needs_duration() -> None:
    base = {"week": 1, "days": 5, "minutes_per_day": 480, "day_start_h": 8, "frame_min": 60,
            "states": list(factory.STATES), "machines": ["l1-m1"], "counters": list(COUNTERS),
            "frames": []}  # fmt: skip
    ok = Timeline.model_validate(base | {"events": [[10, "attente_piece", "l1-m1", {"duration_min": 300}]]})
    assert ok.events[0][1] == "attente_piece"
    with pytest.raises(ValidationError, match="duration_min"):
        Timeline.model_validate(base | {"events": [[10, "attente_piece", "l1-m1", {}]]})


# --- couche jeu : action, pilote, alerte, faits, vue publique --------------------------------------------------------


def _game() -> tuple[dict[str, Any], dict[str, Any]]:
    spec = _base()
    return spec, engine.start(spec, game_state(spec))


def test_generation_pays_the_part_apart_from_the_damage() -> None:
    spec = _base()
    assert spec["factory"]["spares"] == SPARES and spec["factory"]["costs"]["damage_per_failure"] == 50


def test_handler_sets_settings_and_counts_the_pieces_to_order() -> None:
    spec, state = _game()
    plant = factory.Plant(spec)
    message = factory_game._h_spares(spec, state, {"cible": "toutes", "pieces": 6})
    assert state["fs"]["settings"]["spares"] == {"cible": "toutes", "pieces": 6}
    k = sum(6 - n for n in state["fs"]["spares"]["stock"].values())
    assert f"{k} pièce(s) commandée(s), livrée(s) demain à 8 h" in message and factory_game.money(k * 150) in message
    assert plant.types and "toutes les machines, 6 par type" in message
    assert "rien à commander" in factory_game._h_spares(spec, state, {"cible": "aucune", "pieces": 3})


def test_unplayed_action_hands_the_stock_back_to_the_pilot() -> None:
    spec, state = _game()
    state["fs"]["settings"]["spares"] = {"cible": "aucune", "pieces": 1}
    plant = factory.Plant(spec)
    factory_game._autopilot(spec, plant, state, {"pieces_rechange"})
    assert state["fs"]["settings"]["spares"] == {"cible": "aucune", "pieces": 1}
    factory_game._autopilot(spec, plant, state, set())
    assert state["fs"]["settings"]["spares"] is None


def test_waiting_machine_alert_and_facts_and_public_view(monkeypatch: pytest.MonkeyPatch) -> None:
    spec, state = _game()
    plant = factory.Plant(spec)
    state = factory_game.advance(spec, state, set())
    t = plant.mtype[0]
    state["fs"]["spares"]["waiting"][t] = [[-100.0, 0]]
    state["fs"]["spares"]["transit"][t] += 1
    state["fs"]["events"].append([plant.mpd * 2 - 50, 0, 1, "spare", t, 0])  # livrée à l'ouverture du jour suivant
    due = factory_game._waiting_spares(plant, state["fs"])
    day = factory_game.DAY_NAMES[(state["fs"]["day"] + 1) % plant.days]
    assert due == {plant.mids[0]: (day, state["fs"]["spares"]["target"][t])}
    pack = copy.deepcopy(load_pack("usine"))
    pack["alerts"].append(
        {
            "id": "spare_missing",
            "level": "critical",
            "department_id": "maintenance",
            "module_id": "maintenance",
            "text": "{machine} attend sa pièce, livrée {day} à 8 h.",
        }
    )
    monkeypatch.setattr(factory_game, "load_pack", lambda _: pack)
    view = factory_game.public_state(spec, state)
    alert = next(a for a in view["alerts"] if a["id"].startswith("spare_missing"))
    assert alert["action"]["action_id"] == "pieces_rechange" and alert["action"]["values"]["cible"] == "toutes"
    assert not any(a.get("action") and a["action"]["action_id"] == "priorite_reparation" for a in view["alerts"])
    spares = view["factory"]["stocks"]["spares"]
    assert {s["type"] for s in spares} == set(plant.types) and view["factory"]["spares_week"]["used"] >= 0
    facts = " ".join(f for _, f in factory_game._facts_maintenance(spec, state, view))
    assert "Pièces de rechange en stock" in facts


def test_used_piece_is_reordered_at_once_with_lead_days() -> None:
    plant, sim = _sim(_spec(lead_days=3))
    t, mpd = plant.mtype[0], plant.mpd
    sim._rstart(100.0, 0, 0)
    sp = sim.sp
    assert sp["stock"][t] == plant.s_star[t] - 1 and sp["transit"][t] == 1 and sim.sp_stat["bought"] == 1
    assert [e[0] for e in sim.h if e[3] == "spare"] == [(100.0 // mpd + 3) * mpd]
    sim._rstart(110.0, 0, 0)  # une deuxième pièce : une deuxième commande, jamais de doublon
    assert sp["stock"][t] + sp["transit"][t] == plant.s_star[t] and sim.sp_stat["bought"] == 2


def _alert_for(machine: int, chosen: dict[str, Any]) -> dict[str, Any]:
    spec, state = _game()
    plant = factory.Plant(spec)
    state = factory_game.advance(spec, state, set())
    state["fs"]["settings"]["spares"] = chosen
    t = plant.mtype[machine]
    state["fs"]["spares"]["waiting"][t] = [[-100.0, machine]]
    state["fs"]["spares"]["transit"][t] += 1
    state["fs"]["events"].append([plant.mpd * 2 - 50, 0, 1, "spare", t, 0])
    view = factory_game.public_state(spec, state)
    return next(a for a in view["alerts"] if a["id"].startswith("spare_missing"))["action"]["values"]


def test_alert_keeps_the_player_target_when_it_covers_the_type() -> None:
    plant = factory.Plant(_base())
    covered = plant.bottleneck[0]
    assert _alert_for(covered, {"cible": "goulot", "pieces": 2})["cible"] == "goulot"
    assert _alert_for(covered, {"cible": "aucune", "pieces": 2})["cible"] == "toutes"


def test_history_keeps_the_pieces_week_by_week_for_the_debrief() -> None:
    spec, state = _game()
    for _ in range(2):
        state = factory_game.advance(spec, state, set())
    assert [set(h["spares"]) for h in state["history"]] == [
        {"used", "missing", "wait_min", "bought", "purchase", "holding"}
    ] * 2
    deb = factory_game.debrief(spec, state)["spares"]
    assert [w["week"] for w in deb["weeks"]] == [1, 2]
    assert deb["total"]["used"] == sum(h["spares"]["used"] for h in state["history"])
