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
    suppliers: int | None = None,
) -> str:
    params = GameParams(
        pack="usine", theme=theme, difficulty=difficulty, modules=list(modules), seed=seed, weeks=6,
        options={"lines": lines}, extra_agents=list(extra), suppliers=suppliers,
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


def test_the_seed_changes_the_world_and_the_same_seed_gives_the_same_world() -> None:
    from gmix.game import layout
    from gmix.game.layout import check_placement, world_fingerprint
    from gmix.game.spec import load_pack

    pack = load_pack("usine")
    prints = {}
    for theme in ("industrie", "automobile"):
        for seed in range(1, 13):
            spec = spec_of(theme=theme, seed=seed)
            assert check_placement(spec, pack) == [], (theme, seed)
            prints[theme, seed] = world_fingerprint(spec["world"])
    assert spec_of(seed=3)["world"] == spec_of(seed=3)["world"]
    assert spec_of(seed=3)["world"]["decor"]["items"]  # le décor survit à la validation SimSpec
    bundle = layout.place_world(spec_of(seed=3), pack)
    assert bundle["world"]["decor"]["items"]
    assert bundle["world"]["decor"] == layout.place_world(spec_of(seed=3), pack)["world"]["decor"]
    assert bundle["world"]["decor"] != layout.place_world(spec_of(seed=4), pack)["world"]["decor"]
    for theme in ("industrie", "automobile"):
        assert len({prints[theme, s] for s in range(1, 13)}) >= 8, theme


def test_default_variety_is_the_reference_game_and_suppliers_come_from_the_sector() -> None:
    from gmix.game.layout import check_placement
    from gmix.game.spec import load_pack

    pack = load_pack("usine")
    ref = spec_of()
    assert {**spec_of(suppliers=3), "params": 0} == {**ref, "params": 0}
    assert len(ref["suppliers"]) == 3 and len(ref["offers"]) == 3
    assert all(m["type"] in pack["machine_types"] for m in ref["factory"]["machines"])
    for theme in ("industrie", "automobile"):
        extra = pack["themes"][theme]["extra_suppliers"]
        for n in (3, 8):  # bornes de limits.suppliers
            spec = spec_of(theme=theme, suppliers=n, seed=7)
            assert [s["name"] for s in spec["suppliers"][3:]] == [e["name"] for e in extra[: n - 3]]
            assert len(spec["offers"]) == n and check_placement(spec, pack) == []
            assert {s["supplier_id"] for s in spec["world"]["sites"] if s.get("supplier_id")} == {
                s["id"] for s in spec["suppliers"]
            }  # un site par fournisseur
            assert autopilot_check(spec)["playable"], (theme, n)
    big = spec_of(suppliers=8, seed=7)
    by_profile = {o["supplier_id"]: o["profile"] for o in big["offers"]}
    for site in big["world"]["sites"]:  # un fournisseur ajouté a le délai de son profil (site cloné)
        if site.get("supplier_id") and by_profile[site["supplier_id"]] == "economique":
            assert site["distance_class"] == "national"


def test_varied_factories_draw_machine_types_by_rank_and_keep_the_bottleneck() -> None:
    from gmix.game.spec import load_pack

    types = load_pack("usine")["machine_types"]
    for seed in range(1, 7):
        machines = spec_of(suppliers=8, seed=seed)["factory"]["machines"]
        first = [m for m in machines if m["line_id"] == "l1"]
        assert [m["cycle_min"] for m in first] == [m["cycle_min"] for m in machines if m["line_id"] == "l2"]
        for m in first:
            assert any(m["cycle_min"] == t["cycle_min"] and m["rank"] in t["ranks"] for t in types.values())
        assert first[-1]["transfer_min"] == 0 and all(m["transfer_min"] for m in first[:-1])
        assert max(first, key=lambda m: m["cycle_min"])["rank"] == 3


def test_products_and_clients_outside_the_bounds_are_refused() -> None:
    for extra in ({"products": 4, "clients": 4}, {"products": 1, "clients": 5}):
        with pytest.raises(ValueError, match="less_than_equal|entre 1 et"):
            generate(GameParams(pack="usine", theme="industrie", modules=MODULES, seed=1, **extra))


def test_three_products_four_clients_expert_is_playable() -> None:
    spec = generate(GameParams(pack="usine", theme="industrie", modules=MODULES, seed=1, products=3, clients=4,
                               difficulty="expert", buildings=3))  # fmt: skip
    check = autopilot_check(spec)
    assert check["playable"] and check["otif_mean"] >= 95


def test_the_warehouse_grows_with_the_lines_only_for_several_products() -> None:
    def pf(**kw: Any) -> int:
        params = GameParams(pack="usine", theme="industrie", modules=MODULES, seed=1, **kw)
        return generate(params)["factory"]["logistics"]["pf_capacity_pallets"]

    assert pf(products=3, clients=3) == 30 and pf(products=1, options={"lines": 3}) == 20


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

    # Temps CPU rapporté à une boucle de référence mesurée au même moment : la charge du poste (SMT, bridage, antivirus)
    # ralentit les deux de la même façon ; seuils = 1 s et 2 s au repos (boucle ~0,06 s au repos, ~0,2 s sous charge).
    def reference() -> float:
        start = time.process_time()
        sum(i % 7 for i in range(1_000_000))
        return time.process_time() - start

    for params, limit in ((usual, 15), (worst, 30)):
        ratios = []
        for attempt in range(3):  # meilleur de trois (graines distinctes : le résultat est mis en cache par spec)
            ref = min(reference() for _ in range(3))
            start = time.process_time()
            generate(params.model_copy(update={"seed": params.seed + 10 * attempt}))
            ratios.append((time.process_time() - start) / ref)
        assert min(ratios) < limit, ratios


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


def test_pitch_states_the_effective_settings() -> None:
    """Règle n° 4 : expert avec pannes et stocks réglés sur découverte ; le pitch dit ce qui est appliqué."""
    params = GameParams(
        pack="usine", theme="industrie", modules=MODULES, difficulty="expert", seed=5, weeks=6,
        tunings={"mtbf_factor": "decouverte", "mp_stock_days": "decouverte", "pf_stock_days": "decouverte"},
    )  # fmt: skip
    pitch = generate(params)["meta"]["pitch"]
    assert pitch.endswith(
        "Niveau expert : machines plus fiables, pannes du goulot au hasard, plus de défauts, "
        "fournisseurs moins fiables, demande plus variable, "
        "5 jours de matière en stock, 1,2 jour de produits finis en stock, usine chargée à 92 %, "
        "livraison promise à J+1."
    )
    assert "pannes plus fréquentes" not in pitch and "stocks bas" not in pitch
    assert "Niveau équilibré : 4 jours de matière en stock," in spec_of()["meta"]["pitch"]  # fragments vides omis


def test_texts_audit_t2_free_places_money_singular_and_offer_prices() -> None:
    from gmix.game.factory_game import _facts_stock_mp

    spec = spec_of()
    state = engine.start(spec, engine.initial_state(spec))
    view = engine.public_state(spec, state)
    mp = view["factory"]["stocks"]["mp"][0]
    text = " ".join(t for _, t in _facts_stock_mp(spec, state, view) if t.startswith("Magasin"))  # D16
    assert f"{mp['pending']} en commande" in text and "libres une fois comptées" in text
    cash = engine.num(spec["targets"]["cash_final"], 0) + " €"  # D7 : espace des milliers
    assert " " in cash and any(f"au moins {cash}" in r["text"] for r in spec["game_rules"])
    one = GameParams(pack="usine", theme="industrie", modules=["pilotage"], seed=5, weeks=6)
    assert "assure le module pilotage pour" in generate(one)["meta"]["pitch"]  # D13
    assert "assure les modules" in spec["meta"]["pitch"]
    labels = [o["label"] for o in spec["offers"]]  # D15
    assert len(set(labels)) == len(labels)
    assert all(f"{o['unit_cost']:.2f}".replace(".", ",") + " €/u." in o["label"] for o in spec["offers"])


def test_initial_order_only_when_stock_is_below_lead_plus_one_day() -> None:
    """Règle n° 5a : expert (2,5 j < 3 + 1) : commande déjà en route, arrivée au jour 2 ; équilibré : aucune."""
    assert not spec_of()["factory"].get("initial_order")
    spec = spec_of(difficulty="expert", lines=3)
    first = spec["factory"]["initial_order"]
    offer = next(o for o in spec["offers"] if o["id"] == first["offer_id"])
    plant = factory.Plant(spec)
    mp_day = spec["components"][0]["safety_stock"]  # arrondi de la consommation d'un jour
    assert offer["profile"] == "standard" and first["arrival_day"] == 2
    assert 1 <= first["pallets"] <= 6 and abs(first["pallets"] * plant.upp - 1.5 * mp_day) < 2 * plant.upp
    fs = engine.initial_state(spec)["fs"]
    assert [(po["pallets"], po["due_day"]) for po in fs["pending"]] == [(first["pallets"], 2)]


def test_initial_order_arrives_and_is_paid_at_reception() -> None:
    spec = spec_of(difficulty="expert")
    state = engine.start(spec, engine.initial_state(spec))
    paid = state["cash"]
    state = engine.advance(spec, state, autopilot_all=False)  # joueur passif : seule la commande de départ arrive
    assert state["snap"]["report"]["reception"]["trucks"] == 1 and state["cash"] != paid


def test_stockout_margin_scales_with_the_number_of_lines() -> None:
    """Règle n° 5b : marge de 6 donnée pour 2 lignes ; expert à 3 lignes : 9 jours-ligne."""
    partial = lambda **kw: next(c for c in spec_of(**kw)["criteria"] if c["id"] == "stockouts")["partial"]  # noqa: E731
    assert (partial(difficulty="expert", lines=2), partial(difficulty="expert", lines=3)) == (6, 9)
    assert partial(difficulty="expert", lines=1) == 3


def test_passive_wins_warns_when_a_do_nothing_player_reaches_the_targets() -> None:
    """D17 : sans module Pilotage, le pilotage est automatique et le passif gagne ; la partie de référence résiste."""
    j04 = autopilot_check(spec_of(modules=["production", "maintenance"], difficulty="equilibre"))
    assert j04["passive_wins"] and "Pilotage" in j04["warnings"][0]
    reference = autopilot_check(spec_of())
    assert not reference["passive_wins"] and reference["warnings"] == []


def test_line_trs_excludes_breaks_from_planned_time() -> None:
    """Règle n° 4 (fiche OEE) : TRS de ligne = bons produits / (débit théorique x temps hors arrêts et pauses)."""
    spec = spec_of()
    plant = factory.Plant(spec)
    state = engine.advance(spec, engine.start(spec, engine.initial_state(spec)), autopilot_all=True)
    report = state["snap"]["report"]
    lid = plant.line_ids[0]
    mins = report["machines"][plant.mids[plant.bottleneck[0]]]["minutes"]
    planned_h = (plant.T - mins["arret"] - mins["pause"]) / 60
    expected = min(1.0, report["lines"][lid]["good"] / (report["lines"][lid]["theoretical_h"] * planned_h)) * 100
    assert mins["pause"] > 0 and state["snap"]["lines"][lid]["trs"] == pytest.approx(expected)


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


def test_overdraft_alert_proposes_no_action_the_factory_lacks(running) -> None:
    spec, state = running
    state["cash"] = -1
    alert = next(a for a in engine.public_state(spec, state)["alerts"] if a["id"] == "cash:negative")
    assert alert["action"] is None  # pas de module finance dans l'usine : pas d'action « decouvert »


def test_a_broken_bottleneck_raises_the_critical_alert_from_the_pack(running) -> None:
    from gmix.game import factory_game

    spec, state = running
    view = engine.public_state(spec, state)
    machines = view["factory"]["machines"]
    for m in machines:
        m["state"], m["bottleneck"] = "panne", False
    machines[0]["bottleneck"] = True
    tpl = {t["id"]: t for t in factory_game.load_pack(spec["meta"]["pack"])["alerts"]}
    alerts = {a["id"]: a for a in factory_game._alerts(spec, state, view)}
    goulot, other = alerts[f"breakdown:{machines[0]['id']}"], alerts[f"breakdown:{machines[1]['id']}"]
    assert goulot["level"] == tpl["breakdown_goulot"]["level"] == "critical"
    assert goulot["text"] == tpl["breakdown_goulot"]["text"].format(machine=machines[0]["name"])[:120]
    assert other["level"] == tpl["breakdown"]["level"] == "warning" and other["text"].endswith("en panne.")


def test_no_events_with_an_event_plan_is_refused() -> None:
    plan = [{"week": 2, "event_id": "retard_transport"}]
    with pytest.raises(GameRuleError, match="plan d'aléas"):
        generate(GameParams(pack="usine", theme="industrie", modules=MODULES, events="aucun", event_plan=plan, seed=1))


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
    assert "avec 90 % de produits bons" in text and "risque de panne croît avec l'âge" in text
    assert "elle a baissé sur" in text and "aurait" not in text and "None" not in text


def test_factory_lessons_all_targets_met_names_the_figures() -> None:
    spec = spec_of()
    state = play(spec, autopilot=True)
    met = {"stockouts": 0, "otif": 100.0, "trs": 100.0, "good_share": None}
    state["history"] = [{**h, **met} for h in state["history"]]
    state["cash"] = spec["targets"]["cash_final"]
    line = engine.debrief(spec, state)["lessons"][0]  # puis les leçons sur les pannes des goulots
    assert line.startswith("Objectifs atteints : aucune ligne arrêtée faute de matière, OTIF moyen de 100 %")


def test_factory_lessons_all_targets_met_omits_missing_figures() -> None:
    spec = spec_of()
    state = play(spec, autopilot=True)
    met = {"stockouts": 0, "otif": None, "trs": None, "good_share": None}
    state["history"] = [{**h, **met} for h in state["history"]]
    state["cash"] = spec["targets"]["cash_final"]
    line = engine.debrief(spec, state)["lessons"][0]  # puis les leçons sur les pannes des goulots
    assert line.startswith("Objectifs atteints") and "None" not in line and "OTIF" not in line and "TRS" not in line


def test_stockout_fact_is_a_total_over_lines():
    from gmix.game.factory_game import _facts_stock_mp

    mp = {"capacity_pallets": 10, "pallets": 5, "pending": 0, "reorder_point": 1}
    rep = {"lines": {k: {"stockout_min": v} for k, v in {"a": 445, "b": 445, "c": 516.6}.items()}}
    facts = _facts_stock_mp({}, {"snap": {"report": rep}}, {"factory": {"stocks": {"mp": [mp]}}})
    assert facts[0] == (True, "Les 3 lignes ont été arrêtées 1 407 minutes au total faute de matière.")


@pytest.mark.parametrize("difficulty", ["decouverte", "expert"])
def test_factory_texts_shown_to_the_player_use_french_numbers(difficulty: str) -> None:
    import re

    spec = spec_of(difficulty=difficulty)
    texts = [spec["meta"]["pitch"]]
    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        state = engine.advance(spec, state, autopilot_all=True)
        view = engine.public_state(spec, state)
        texts += [_texts([view["briefings"], view["alerts"]])]
    texts.append(_texts(engine.debrief(spec, state)))
    blob = re.sub(r"§\s?[\d.]+|https?://\S+|\S+oldid=\d+", "", "\n".join(texts))  # renvois et liens : pas des nombres
    assert not re.search(r"\d\.\d", blob), re.findall(r".{20}\d\.\d.{10}", blob)[:3]  # décimale à point
    big = r"(?<![\w ,./-])\d{4,}"  # millier sans espace ; dates, références (L3121-16) exclues
    assert not re.search(big, blob), re.findall(r".{20}" + big + ".{10}", blob)[:3]


def _texts(node: Any) -> str:
    if isinstance(node, str):
        return node + " | "
    items = node.values() if isinstance(node, dict) else node if isinstance(node, list) else []
    return "".join(_texts(x) for x in items)


def test_initial_order_survives_a_json_roundtrip_with_float_numbers() -> None:
    """Godot relit toute spec en flottants (4 -> 4.0) : SimSpec doit les ramener à des entiers, sinon 500."""
    from gmix.game.spec import SimSpec

    spec = json.loads(json.dumps(spec_of(difficulty="expert")))
    order = spec["factory"]["initial_order"]
    order.update(pallets=float(order["pallets"]), arrival_day=float(order["arrival_day"]))
    valid = SimSpec.model_validate(spec).model_dump(mode="json")
    assert all(type(valid["factory"]["initial_order"][k]) is int for k in ("pallets", "arrival_day"))
    original = SimSpec.model_validate(spec_of(difficulty="expert")).model_dump(mode="json")
    assert autopilot_check(valid) == autopilot_check(original)


# --- pannes évitées par le préventif (P1) -------------------------------------------------------------------------


def _wear_state(spec: dict[str, Any], expected: float, failures: int, preventive: int, shape: float | None = None):
    """Partie fictive : une semaine, chaque goulot avec `expected` pannes attendues et `failures` observées."""
    spec = copy.deepcopy(spec)
    plant = factory.Plant(spec)
    if shape is not None:
        for i in plant.bottleneck:
            spec["factory"]["machines"][i]["weibull_shape"] = shape
    wear = {plant.mids[i]: {"run_h": 30.0, "expected": expected, "failures": failures, "down_h": float(failures),
                            "preventive": preventive} for i in plant.bottleneck}  # fmt: skip
    return spec, {"history": [{"wear": wear, "preventive": preventive * len(wear), "lost": 0}]}


def _wear_texts(spec: dict[str, Any], state: dict[str, Any]) -> str:
    from gmix.game import factory_game

    return " ".join(factory_game._wear_lessons(spec, state))


def test_wear_with_preventive_says_how_many_failures_were_avoided() -> None:
    spec, state = _wear_state(spec_of(lines=1), expected=20, failures=5, preventive=1)
    text = _wear_texts(spec, state)
    assert "5 pannes pour 20 attendues" in text and "évité environ 15" in text and "Préventif : 50 €" in text


def test_the_avoided_failures_threshold_is_two_square_roots_of_the_expected_ones() -> None:
    from gmix.game import factory_game

    for failures, shown in ((12, False), (11, True)):  # attendues 20 : seuil 2 x racine(20) = 8,94 ; évitées 8 et 9
        spec, state = _wear_state(spec_of(lines=1), expected=20, failures=failures, preventive=1)
        assert (factory_game.bottleneck_wear(spec, state)[0]["avoided"] is not None) is shown
        assert ("dans les variations du hasard" in _wear_texts(spec, state)) is not shown


def test_wear_without_preventive_says_the_failures_were_expected() -> None:
    spec, state = _wear_state(spec_of(lines=1), expected=20, failures=20, preventive=0)
    text = _wear_texts(spec, state)
    assert "attendues d'après son MTBF, sans préventif" in text and "autant que prévu" not in text
    assert "un entretien régulier en aurait évité" in text and "Préventif :" not in text


def test_random_failures_are_never_said_to_be_avoided() -> None:
    spec, state = _wear_state(spec_of(lines=1), expected=20, failures=0, preventive=1, shape=1.0)
    text = _wear_texts(spec, state)
    assert "au hasard" in text and "avec préventif" in text and "évité environ" not in text


def test_unquantifiable_avoided_cost_is_null_and_never_zero_euros() -> None:
    spec, state = _wear_state(spec_of(lines=1), expected=20, failures=19, preventive=1)
    assert factory_game_balance(spec, state)["avoided_cost"] is None
    text = _wear_texts(spec, state)
    assert "non chiffrables" in text and "environ 0 €" not in text


def test_the_debrief_and_the_maintenance_agent_carry_the_bottleneck_failures() -> None:
    spec = spec_of()
    state = play(spec, autopilot=True)
    plant = factory.Plant(spec)
    bottlenecks = engine.debrief(spec, state)["bottlenecks"]
    assert sum(b["lines"] for b in bottlenecks) == len(plant.bottleneck)
    assert all(b["expected"] > 0 and b["failures"] >= 0 and b["down_h"] >= 0 for b in bottlenecks)
    briefings = json.dumps(engine.public_state(spec, state)["briefings"], ensure_ascii=False)
    assert "attendue(s) sans entretien d'après son MTBF" in briefings


def test_every_number_of_the_preventive_texts_is_a_debrief_field() -> None:
    import re

    from gmix.game.engine import money, num

    spec, state = _wear_state(spec_of(lines=1), expected=20, failures=5, preventive=1)
    state["history"][0]["lost"] = 3
    debrief = {"bottlenecks": factory_game_wear(spec, state), "preventive": factory_game_balance(spec, state)}
    b, p = debrief["bottlenecks"][0], debrief["preventive"]
    assert p["avoided_cost"] == b["avoided_cost"] > 0 and b["expected_without_preventive"] == 20
    allowed = {num(b["failures"], 0), num(b["expected_without_preventive"]), num(b["avoided"], 0),
               num(b["avoided"] * b["mttr_h"], 0), money(p["cost"]), money(p["avoided_cost"]),
               str(p["lost"])}  # fmt: skip
    for text in _wear_texts(spec, state).split(". "):
        for n in re.findall(r"\d+(?: \d{3})*(?:,\d+)?(?: €)?", text):
            assert n in allowed, (n, text)


def factory_game_wear(spec, state):
    from gmix.game import factory_game

    return factory_game.bottleneck_wear(spec, state)


def factory_game_balance(spec, state):
    from gmix.game import factory_game

    return factory_game.preventive_balance(spec, state)


def test_wear_texts_say_repairs_and_damages_and_trs_lesson_has_no_pause() -> None:
    spec, state = _wear_state(spec_of(lines=1), expected=20, failures=5, preventive=1)
    assert "réparations et dégâts évités : environ" in _wear_texts(spec, state)
    spec = spec_of()
    from gmix.game import factory_game

    state = play(spec, autopilot=True)
    for h in state["history"]:
        h["trs"] = 1.0  # sous la cible : la leçon TRS s'affiche
    lessons = factory_game._lessons(spec, state)
    trs = [t for t in lessons if t.startswith("TRS moyen")]
    assert trs and all("pause" not in t and "attentes, ralentissements" in t for t in trs)
