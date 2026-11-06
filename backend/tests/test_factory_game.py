"""Partie d'usine (gmix.game.factory_game) et son générateur (factory_generation) : spec valide et déterministe, pilote
automatique qui termine, handlers chiffrés, budgets. Les valeurs viennent du pack usine ; aucun chiffre n'est recopié
du moteur : les attendus se calculent depuis la spec."""

import copy
import json
import time
from functools import cache
from typing import Any

import pytest

from gmix.game import engine, factory
from gmix.game.engine import GameRuleError
from gmix.game.factory_game import EVENT_EFFECTS
from gmix.game.generation import autopilot_check, generate
from gmix.game.spec import PUBLIC_ROOTS, UI_LIMITS, GameParams, SimSpec

MODULES = ["pilotage", "production", "maintenance"]
ACTOR = {"user_id": 1, "name": "Test", "role": None}


@cache
def _spec(
    theme: str = "industrie",
    difficulty: str = "equilibre",
    modules: tuple[str, ...] = tuple(MODULES),
    lines: int = 2,
    seed: int = 5,
    extra: tuple[str, ...] = (),
) -> str:
    params = GameParams(
        pack="usine", theme=theme, difficulty=difficulty, modules=list(modules), seed=seed, weeks=6,
        options={"lines": lines}, extra_agents=list(extra),
    )  # fmt: skip
    return json.dumps(generate(params))


def spec_of(**kw: Any) -> dict[str, Any]:
    return json.loads(_spec(**{k: tuple(v) if isinstance(v, list) else v for k, v in kw.items()}))


def play(spec: dict[str, Any], *, autopilot: bool) -> dict[str, Any]:
    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        state = engine.advance(spec, state, autopilot_all=autopilot)
    return state


def act(spec: dict[str, Any], state: dict[str, Any], module: str, action: str, **values: Any) -> tuple[dict, str]:
    return engine.act(spec, state, module, action, values, actor=ACTOR, manager=True, occupied_roles=set())


@pytest.mark.parametrize("seed", [1, 5, 9])
def test_debrief_series_ends_on_final_and_accumulates(seed: int) -> None:
    spec = spec_of(seed=seed)
    state = play(spec, autopilot=True)
    crit = {c["id"]: c for c in engine.debrief(spec, state)["criteria"]}
    for c in crit.values():
        assert len(c["series"]) == len(state["history"]) and c["series"][-1] == c["final"]
    stock = [h["stockouts"] for h in state["history"]]
    assert crit["stockouts"]["series"] == [sum(stock[: w + 1]) for w in range(len(stock))]
    assert crit["cash"]["series"] == [h["cash"] for h in state["history"]]


@pytest.fixture
def running() -> tuple[dict[str, Any], dict[str, Any]]:
    spec = spec_of()
    return spec, engine.start(spec, engine.initial_state(spec))


# --- génération -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("theme", ["industrie", "automobile"])
@pytest.mark.parametrize("difficulty", ["decouverte", "equilibre", "expert"])
def test_every_theme_and_difficulty_gives_a_valid_spec_the_autopilot_finishes(theme: str, difficulty: str) -> None:
    spec = spec_of(theme=theme, difficulty=difficulty)
    SimSpec.model_validate(spec)
    assert spec["meta"]["pack"] == "usine" and spec["seed"] == 5
    check = autopilot_check(spec)
    assert check["weeks"] == 6 and check["otif_mean"] >= 90 and check["final_cash"] > spec["economy"]["initial_cash"]
    assert (
        spec["targets"]["cash_final"] > spec["economy"]["initial_cash"]
    )  # objectif jamais sous la trésorerie de départ


def test_difficulty_costs_cash() -> None:
    # le TRS n'est pas testé : la charge croît avec la difficulté et fait monter le TRS (expert >= équilibré)
    cash = [autopilot_check(spec_of(difficulty=d))["final_cash"] for d in ("decouverte", "equilibre", "expert")]
    assert cash[0] > cash[1] > cash[2]


def test_same_seed_same_game_other_seed_other_game() -> None:
    assert _spec() == _spec()
    other = generate(GameParams(pack="usine", theme="industrie", modules=MODULES, seed=6, weeks=6))
    assert other != spec_of() and other["seed"] == 6


@pytest.mark.parametrize("modules", [["pilotage"], ["production"], ["maintenance"], MODULES])
def test_each_module_alone_then_all_together(modules: list[str]) -> None:
    spec = spec_of(modules=modules)
    assert [m["id"] for m in spec["modules"]] == modules
    assert {a["module"] for a in spec["agents"] if a.get("module")} <= set(modules)
    assert autopilot_check(spec)["weeks"] == 6


@pytest.mark.parametrize("lines", [1, 2, 3])
def test_one_to_three_lines(lines: int) -> None:
    spec = spec_of(lines=lines)
    assert len(spec["lines"]) == lines and len(spec["factory"]["machines"]) == 4 * lines
    assert autopilot_check(spec)["weeks"] == 6


def test_the_player_bar_holds_at_most_the_limit_and_the_extra_agent_is_added() -> None:
    spec = spec_of(extra=["direction"])
    bar = [t for t in spec["tools"] if t.get("audience", "joueur") == "joueur" and t.get("bar", True)]
    assert len(bar) <= UI_LIMITS["tools"]
    assert any(a["id"] == "agent_direction" for a in spec["agents"])
    SimSpec.model_validate(spec)


def test_the_world_is_placed_and_every_agent_has_a_route() -> None:
    spec = spec_of()
    assert spec["world"]["objects"] and all(a["route"] for a in spec["agents"])
    assert {m["id"] for m in spec["factory"]["machines"]} <= {s["ref"] for s in spec["stations"]}
    assert all(s["position"] != [0.0, 0.0] for s in spec["stations"])  # postes replacés par le placeur


def test_event_effects_are_known_and_a_planned_event_is_honoured() -> None:
    spec = spec_of()
    assert spec["events"] and all(set(e["effects"]) <= EVENT_EFFECTS for e in spec["events"])
    planned = copy.deepcopy(spec)
    planned["params"]["event_plan"] = [{"week": 2, "event_id": spec["events"][0]["id"]}]
    state = engine.advance(planned, engine.start(planned, engine.initial_state(planned)))
    assert state["event"] == spec["events"][0]["id"]


def test_a_pack_that_does_not_exist_is_refused_with_a_readable_message() -> None:
    params = GameParams(pack="usine", theme="industrie", modules=MODULES).model_copy(update={"pack": "nul"})
    with pytest.raises(Exception, match="nul"):
        generate(params)


# --- parties ---------------------------------------------------------------------------------------------------


def test_a_passive_player_falls_below_the_otif_target_and_loses_cash() -> None:
    spec = spec_of(difficulty="equilibre")
    state = play(spec, autopilot=False)
    otif = sum(h["otif"] for h in state["history"]) / len(state["history"])
    assert otif < spec["targets"]["otif"] - 20 and state["cash"] < spec["economy"]["initial_cash"]


def test_the_public_state_has_the_declared_roots_and_stays_in_budget() -> None:
    spec = spec_of(lines=3, difficulty="expert")
    state = engine.start(spec, engine.initial_state(spec))
    assert set(engine.public_state(spec, state)) == PUBLIC_ROOTS
    durations = []
    for _ in range(3):  # meilleur de trois : la machine peut être chargée
        start = time.perf_counter()
        advanced = engine.advance(spec, state)
        durations.append(time.perf_counter() - start)
    state = advanced
    assert min(durations) < 0.15, durations
    view = engine.public_state(spec, state)
    assert len(json.dumps(view)) < 64_000 and view["factory"] and view["briefings"]
    assert view["stocks"] == view["components"] == view["lines"] == view["pending"] == []
    assert 0 <= state["history"][0]["trs"] <= 100  # pourcentage, pas une fraction ni x100


def test_generation_stays_within_its_time_budget() -> None:
    """La génération joue toute la partie en pilote automatique (calage de l'objectif de trésorerie) : son coût est
    celui du noyau, proportionnel à lignes x semaines (cProfile : 98 % dans `factory.run`, ~85 000 fins de cycle pour
    3 lignes x 12 semaines). Partie courante (2 lignes, 6 semaines) : sous 1 s. Pire cas (3 lignes, 12 semaines,
    expert, aléas fréquents) : 0,8 à 1,05 s au repos, donc 2 s de limite quand la machine est chargée. Chaque appel
    a sa graine, car `autopilot_check` garde le résultat d'une même spec."""
    generate(GameParams(pack="usine", theme="industrie", modules=MODULES, seed=1))  # chauffe : catalogues, pack
    usual = GameParams(pack="usine", theme="industrie", modules=MODULES, weeks=6, seed=2)
    worst = GameParams(
        pack="usine", theme="industrie", modules=MODULES, weeks=12, options={"lines": 3}, seed=3,
        difficulty="expert", events="frequents",
    )  # fmt: skip
    for params, limit in ((usual, 1.0), (worst, 2.0)):
        durations = []
        for attempt in range(3):  # meilleur de trois (graines distinctes : le résultat est mis en cache par spec)
            start = time.perf_counter()
            generate(params.model_copy(update={"seed": params.seed + 10 * attempt}))
            durations.append(time.perf_counter() - start)
        assert min(durations) < limit, durations


def test_autopilot_check_is_not_replayed_for_the_same_spec() -> None:
    spec = spec_of(seed=11)
    autopilot_check(spec)  # déjà joué par `generate`, puis rejoué par l'API sur la même spec
    start = time.perf_counter()
    again = autopilot_check(spec | {"targets": {**spec["targets"], "cash_final": 1.0}})
    assert time.perf_counter() - start < 0.05 and again == autopilot_check(spec)


def test_tunings_take_the_value_of_another_profile() -> None:
    base = spec_of(difficulty="decouverte")
    params = GameParams(
        pack="usine", theme="industrie", modules=MODULES, difficulty="decouverte", seed=5, weeks=6,
        tunings={"mp_stock_days": "expert"},
    )  # fmt: skip
    stock = lambda spec: engine.initial_state(spec)["fs"]["mp"]["units"]  # noqa: E731
    assert stock(generate(params)) < stock(base)  # le profil expert part avec moins de matière


# --- handlers : un résultat chiffré et un refus par règle -----------------------------------------------------------


def test_launch_of_announces_lots_and_units(running) -> None:
    spec, state = running
    plant = factory.Plant(spec)
    new, summary = act(spec, state, "pilotage", "lancer_of", line=spec["lines"][0]["id"], lots=5)
    assert f"5 lots, soit {5 * plant.lot_size} produits" in summary
    assert new["fs"] != state["fs"] and new["log"][-1]["action"] == "lancer_of"


def test_order_mp_is_paid_at_reception_and_refuses_what_the_rules_forbid(running) -> None:
    spec, state = running
    plant = factory.Plant(spec)
    offer = min(spec["offers"], key=lambda o: o["min_order"])
    pallets = max(offer["min_order"], 1)
    price = round(pallets * plant.upp * offer["unit_cost"] * state["cost_index"], 2)
    new, summary = act(spec, state, "pilotage", "commander_mp", offer=offer["id"], pallets=pallets)
    assert new["cash"] == state["cash"] and f"{pallets} palettes" in summary  # payée à la livraison, pas à la commande
    assert new["fs"]["pending"][-1]["unit_price"] == round(offer["unit_cost"] * state["cost_index"], 4)
    with pytest.raises(GameRuleError, match="Trésorerie insuffisante"):
        act(
            spec,
            copy.deepcopy(state) | {"cash": price - 1},
            "pilotage",
            "commander_mp",
            offer=offer["id"],
            pallets=pallets,
        )
    full = copy.deepcopy(spec)
    full["factory"]["logistics"]["mp_capacity_pallets"] = 0
    with pytest.raises(GameRuleError, match="place"):
        act(full, state, "pilotage", "commander_mp", offer=offer["id"], pallets=pallets)
    strict = copy.deepcopy(spec)
    for o in strict["offers"]:
        o["min_order"] = 3
    with pytest.raises(GameRuleError, match="au moins 3 palettes"):
        act(strict, state, "pilotage", "commander_mp", offer=offer["id"], pallets=2)
    with pytest.raises(GameRuleError, match="entre"):
        act(spec, state, "pilotage", "commander_mp", offer=offer["id"], pallets=99)


def test_reception_pays_the_accepted_pallets_only(running) -> None:
    """Un camion de 6 palettes, un taux de non-conformité de 50 % : les palettes mises en quarantaine ne sont pas
    facturées (avoir) et le débit tombe à la réception, au prix figé à la commande."""
    spec, state = running
    spec = copy.deepcopy(spec)
    spec["factory"]["logistics"]["supplier_nonconform_rate"] = 0.5
    plant = factory.Plant(spec)
    offer = spec["offers"][0] | {"lead_time": 1}
    state = copy.deepcopy(state)
    factory.order_mp(plant, state["fs"], offer, 6, cost_index=1.1)
    new = engine.advance(spec, state)
    rec = new["snap"]["report"]["reception"]
    assert rec["pallets"] == 6 and 0 < rec["quarantined"] < 6 * plant.upp  # la graine tire quelques palettes refusées
    paid = new["last"]["costs"]["mp"]
    assert paid == round(rec["accepted"] * offer["unit_cost"] * 1.1)
    assert paid < round(6 * plant.upp * offer["unit_cost"] * 1.1)


def test_the_autopilot_never_overdraws_the_cash_with_raw_material(running) -> None:
    spec, state = running
    state = copy.deepcopy(state)
    for _ in range(6):
        if state["status"] != "running":
            break
        state = engine.advance(spec, state, autopilot_all=True)
        assert state["cash"] >= 0
    po = copy.deepcopy(running[1])
    offer = spec["offers"][0]
    plant = factory.Plant(spec)
    factory.order_mp(plant, po["fs"], offer, 6, po["cost_index"])
    due = 6 * plant.upp * offer["unit_cost"] * po["cost_index"]
    po["cash"] = round(due * 1.5, 2)  # assez pour une commande, pas pour deux
    with pytest.raises(GameRuleError, match="déjà engagés"):
        act(spec, po, "pilotage", "commander_mp", offer=offer["id"], pallets=6)


def test_an_autopilot_order_keeps_its_supplier_lead_time_from_the_day_it_is_placed() -> None:
    """Le pilote commande au jour d du tour : l'échéance doit être jour de commande + délai, jamais antérieure."""
    spec = spec_of()
    placed: list[tuple[int, dict[str, Any]]] = []
    original = factory._Sim._auto

    def spy(self: Any, now: float, d: int, x: Any) -> None:
        before = len(self.fs["pending"])
        original(self, now, d, x)
        placed.extend((self.fs["day"] + d, po) for po in self.fs["pending"][before:])

    factory._Sim._auto = spy
    try:
        play(spec, autopilot=True)
    finally:
        factory._Sim._auto = original
    lead = {o["id"]: o["lead_time"] for o in spec["offers"]}
    assert placed and all(po["due_day"] == day + lead[po["offer_id"]] for day, po in placed)


def test_protect_keeps_a_single_relief_and_rejects_an_unknown_mode(running) -> None:
    spec, state = running
    one, two = (line["id"] for line in spec["lines"][:2])
    state, _ = act(spec, state, "production", "proteger_goulot", line=one, mode="releve_pauses")
    state, summary = act(spec, state, "production", "proteger_goulot", line=two, mode="releve_pauses")
    protect = state["fs"]["settings"]["protect"]
    assert protect[two] == "releve_pauses" and protect[one] == "aucune" and "retirée" in summary
    state, _ = act(spec, state, "production", "proteger_goulot", line=one, mode="tampon_avant")
    assert state["fs"]["settings"]["protect"][one] == "tampon_avant"
    with pytest.raises(GameRuleError, match="choix inconnu"):
        act(spec, state, "production", "proteger_goulot", line=one, mode="magie")


def test_preventive_and_repair_priority_are_stored(running) -> None:
    spec, state = running
    line = spec["lines"][0]["id"]
    state, summary = act(spec, state, "maintenance", "preventif", line=line, cible="goulot")
    assert state["fs"]["settings"]["preventive"][line] == "goulot" and "le goulot" in summary
    state, summary = act(spec, state, "maintenance", "priorite_reparation", ordre="goulot")
    assert state["fs"]["settings"]["priority"] == "goulot" and "goulots d'abord" in summary


def test_an_action_outside_the_game_is_refused(running) -> None:
    spec, state = running
    with pytest.raises(GameRuleError, match="inconnue"):
        act(spec, state, "finance", "fixer_prix")
    with pytest.raises(GameRuleError, match="pas en cours"):
        act(spec, engine.initial_state(spec), "pilotage", "lancer_of", line="l1", lots=1)


# --- alertes, critères et droits de l'usine (annexe 0010) ---------------------------------------------------------


def test_factory_spec_carries_criteria_rules_departments_and_rule_provenance() -> None:
    spec = spec_of()
    assert {c["id"] for c in spec["criteria"]} == {"otif", "trs", "stockouts", "cash"}
    assert next(c for c in spec["criteria"] if c["id"] == "cash")["target"] >= spec["economy"]["initial_cash"]
    deps = {d["id"] for d in spec["departments"]}
    assert all(r["department_id"] in deps for r in spec["roles"])
    assert any(k.startswith("placement_rules.") for k in spec["provenance"])
    assert autopilot_check(spec)["criteria"]


def test_factory_alerts_are_validated_facts(running) -> None:
    from gmix.game.spec import Alert

    spec, state = running
    state["cash"] = -1
    state["fs"]["settings"]["priority"] = "arrivee"
    alerts = engine.public_state(spec, state)["alerts"]
    assert "cash:negative" in {a["id"] for a in alerts} and len(alerts) <= 8
    for a in alerts:
        Alert.model_validate(a)
    view = engine.public_state(spec, play(spec, autopilot=True))
    assert view["alerts"] == [] or all(Alert.model_validate(a) for a in view["alerts"])
    assert [e["kind"] for e in play(spec, autopilot=True)["log"]].count("auto") > 0


def test_passive_player_misses_the_stockout_criterion_and_cash_partial_is_the_starting_cash() -> None:
    spec = spec_of(difficulty="expert")
    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        state = engine.advance(spec, state)  # joueur passif : aucune action, pas de pilote
    verdicts = {c["id"]: c for c in engine.debrief(spec, state)["criteria"]}
    cash = next(c for c in spec["criteria"] if c["id"] == "cash")
    assert cash["partial"] == spec["economy"]["initial_cash"] < cash["target"]
    assert verdicts["stockouts"]["verdict"] == "non_atteint"  # aucun produit sorti de la partie
    empty = [dict(h, good_share=None, stockouts=0) for h in state["history"]]
    quiet = dict(state, history=empty)
    assert {c["id"]: c["verdict"] for c in engine.debrief(spec, quiet)["criteria"]}["stockouts"] == "non_atteint"


def test_trs_low_alert_comes_from_the_pack() -> None:
    spec = spec_of()
    state = engine.start(spec, engine.initial_state(spec))
    state = engine.advance(spec, state)
    state["snap"]["lines"]["l1"]["trs"] = 50.0
    alerts = engine.public_state(spec, state)["alerts"]
    low = next(a for a in alerts if a["id"] == "trs_low:l1")
    assert low["level"] == "warning" and low["module_id"] == "production" and low["action"] is None
    assert "50" in low["text"] and "73" in low["text"]


def test_factory_lessons_state_computed_facts_only() -> None:
    spec = spec_of()
    state = play(spec, autopilot=True)
    n = len(state["history"])
    state["history"] = [
        {**h, "stockouts": 2, "delays": 1, "otif": 10.0, "trs": 10.0, "good_share": 90.0, "cash": 1000 - i}
        for i, h in enumerate(state["history"])
    ]
    state["cash"] = 0
    out = engine.debrief(spec, state)["lessons"]
    text = " ".join(out)
    assert f"{2 * n} jour(s)-ligne arrêté(s) faute de matière, sur {n} semaine(s)" in text and "palettes" in text
    assert f"{n} commande(s) client en retard ; {n} des semaines concernées" in text
    assert "avec 90.0 % de produits bons" in text and "risque de panne croît avec l'âge" in text
    assert "elle a baissé sur" in text and "aurait" not in text and "None" not in text


def test_factory_lessons_all_targets_met_names_the_figures() -> None:
    spec = spec_of()
    state = play(spec, autopilot=True)
    met = {"stockouts": 0, "otif": 100.0, "trs": 100.0, "good_share": None}
    state["history"] = [{**h, **met} for h in state["history"]]
    state["cash"] = spec["targets"]["cash_final"]
    (line,) = engine.debrief(spec, state)["lessons"]
    assert line.startswith("Objectifs atteints : aucune ligne arrêtée faute de matière, OTIF moyen de 100.0 %")


def test_factory_lessons_all_targets_met_omits_missing_figures() -> None:
    spec = spec_of()
    state = play(spec, autopilot=True)
    met = {"stockouts": 0, "otif": None, "trs": None, "good_share": None}
    state["history"] = [{**h, **met} for h in state["history"]]
    state["cash"] = spec["targets"]["cash_final"]
    (line,) = engine.debrief(spec, state)["lessons"]
    assert line.startswith("Objectifs atteints") and "None" not in line and "OTIF" not in line and "TRS" not in line
