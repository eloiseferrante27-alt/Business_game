"""Contrat de la tranche T7 (annexe 0013 §3 ter) : rôles répartis entre joueurs. Étape 1a du plan.

Référence (`fixtures/t7_reference.json`) : parties jouées avec chaque sous-ensemble de rôles tenus (`held_roles`),
prises avant toute modification du moteur ; elle complète celle de T4b (1 produit, pilote automatique total) par
des parties à 3 produits et par le moteur de base (pack atelier). Elle ne garde que `history` et l'empreinte de
`public_state`. Elle doit rester identique jusqu'à la fin de T7 (spec sans `role_plans`, ou plan à 3 rôles).

Régénérer la référence (seulement si une règle change volontairement, avec accord du game-designer) :
    cd backend; .venv\\Scripts\\python -m tests.test_t7_contract

Les tests qui exigent du code nouveau sont en xfail strict, avec l'étape qui les fera passer
(3b : pilote automatique par action et génération ; 1b : spec.py et 3a : engine, droits, sont faites).
"""

import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from gmix.game import engine
from gmix.game.generation import generate
from gmix.game.spec import GameParams, SimSpec, default_params

from .test_t4b_contract import check_bounds

FIXTURE = Path(__file__).parent / "fixtures" / "t7_reference.json"
USINE_ROLES = ("responsable_production", "chef_de_ligne", "responsable_maintenance")
THEMES = ("industrie", "automobile")
ACTOR = {"user_id": "u1", "name": "Alex"}


def params(pack: str, theme: str, seed: int, products: int) -> GameParams:
    return GameParams(**default_params(pack) | {"theme": theme, "seed": seed, "products": products})


def subsets(roles: list[str], full: bool) -> list[tuple[str, ...]]:
    """Les 2^n sous-ensembles (usine : 8) ; sinon tous, aucun, le premier seul, le dernier seul."""
    if full:
        return [c for n in range(len(roles) + 1) for c in itertools.combinations(roles, n)]
    return [tuple(roles), (), (roles[0],), (roles[-1],)]


def case_key(pack: str, theme: str, seed: int, products: int, held: tuple[str, ...]) -> str:
    return f"{pack}/{theme}/{seed}/{products}/{','.join(held) or '-'}"


def play(spec: dict[str, Any], held: tuple[str, ...]) -> dict[str, Any]:
    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        state = engine.advance(spec, state, held_roles=set(held))
    return state


def capture(spec: dict[str, Any], held: tuple[str, ...]) -> dict[str, Any]:
    state = play(spec, held)
    public = json.dumps(engine.public_state(spec, state), sort_keys=True, ensure_ascii=False)
    return {"history": json.loads(json.dumps(state["history"])), "public": hashlib.sha256(public.encode()).hexdigest()}


def all_cases() -> list[tuple[str, str, int, int]]:
    usine = [("usine", t, s, 1) for t in THEMES for s in (1, 2, 3)]
    multi = [("usine", t, 1, 3) for t in THEMES]
    return usine + multi + [("atelier", "industrie", s, 2) for s in (1, 2)]


def case_roles(pack: str, theme: str, seed: int, products: int) -> list[str]:
    return engine.role_plan(generate(params(pack, theme, seed, products)), 3)  # le plan à 3 : les rôles des modules


def build_reference() -> dict[str, Any]:
    result = {}
    for pack, theme, seed, products in all_cases():
        spec = generate(params(pack, theme, seed, products))
        for held in subsets(engine.role_plan(spec, 3), pack == "usine" and products == 1):
            result[case_key(pack, theme, seed, products, held)] = capture(spec, held)
    return json.loads(json.dumps(result))


@pytest.fixture(scope="module")
def reference() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def reference_ids() -> list[str]:
    return [f"{p}/{t}/{s}/{n}" for p, t, s, n in all_cases()]


# --- Non-régression : la référence prise avant T7 ------------------------------------------------------------------


@pytest.mark.parametrize("case", all_cases(), ids=reference_ids())
def test_games_with_held_roles_are_identical_to_the_reference(reference, case) -> None:
    spec = generate(params(*case))
    pack, _, _, products = case
    for held in subsets(engine.role_plan(spec, 3), pack == "usine" and products == 1):
        key = case_key(*case, held)
        actual = capture(spec, held)
        assert actual["history"] == reference[key]["history"], key
        assert actual["public"] == reference[key]["public"], key


def test_reference_covers_every_subset(reference) -> None:
    expected = {case_key(*c, h) for c in all_cases() for h in subsets(case_roles(*c), c[0] == "usine" and c[3] == 1)}
    assert set(reference) == expected
    assert sum(1 for k in reference if k.startswith("usine/industrie/1/1/")) == 8


# --- Exemples du §3 ter -------------------------------------------------------------------------------------------


def t7_spec() -> dict[str, Any]:
    """Spec usine générée, plus les deux rôles et les deux plans de l'exemple valide du §3 ter."""
    spec = copy.deepcopy(generate(params("usine", "industrie", 1, 1)))
    spec["roles"] = [r for r in spec["roles"] if r["id"] in USINE_ROLES]  # on repart des 3 rôles des modules
    spec["roles"] += [
        {"id": "acheteur", "title": "Acheteur·se", "mission": "Commander la matière à temps",
         "module_id": "pilotage", "actions": ["commander_mp"]},
        {"id": "ordonnanceur", "title": "Ordonnanceur·se", "mission": "Lancer les OF à temps",
         "module_id": "pilotage", "actions": ["lancer_of"]},
    ]  # fmt: skip
    plan4 = ["acheteur", "ordonnanceur", "chef_de_ligne", "responsable_maintenance"]
    spec["role_plans"] = [{"players": 3, "roles": list(USINE_ROLES)}, {"players": 4, "roles": plan4}]
    return spec


def refused(raw: dict[str, Any], *words: str) -> None:
    with pytest.raises(ValidationError) as caught:
        SimSpec.model_validate(raw)
    assert all(word in str(caught.value) for word in words), str(caught.value)


def test_valid_t7_spec_is_reread_without_lost_key() -> None:
    raw = t7_spec()
    raw["modules"][0]["actions"][0]["autopilot"] = "MP commandée au fournisseur standard"
    reread = SimSpec.model_validate(raw).model_dump(mode="json")
    assert not set(json.loads(json.dumps(raw))) - set(reread)
    assert [p["players"] for p in reread["role_plans"]] == [3, 4]
    assert next(r for r in reread["roles"] if r["id"] == "acheteur")["actions"] == ["commander_mp"]
    assert reread["modules"][0]["actions"][0]["autopilot"] == "MP commandée au fournisseur standard"


def _role(raw: dict[str, Any], role_id: str) -> dict[str, Any]:
    return next(r for r in raw["roles"] if r["id"] == role_id)


def _unknown_action(raw: dict[str, Any]) -> None:
    _role(raw, "acheteur")["actions"] = ["x"]


def _plan4_without_ordonnanceur(raw: dict[str, Any]) -> None:
    raw["role_plans"][1]["roles"].remove("ordonnanceur")


def _plan4_with_production(raw: dict[str, Any]) -> None:
    raw["role_plans"][1]["roles"].append("responsable_production")


def _duplicate_plan(raw: dict[str, Any]) -> None:
    raw["role_plans"][0]["players"] = 4


def _zero_players(raw: dict[str, Any]) -> None:
    raw["role_plans"][0]["players"] = 0


def _seven_players(raw: dict[str, Any]) -> None:
    raw["role_plans"][0]["players"] = 7


def _wrong_module(raw: dict[str, Any]) -> None:
    _role(raw, "acheteur")["module_id"] = "production"


def _role_in_no_plan(raw: dict[str, Any]) -> None:
    raw["roles"].append({"id": "x", "title": "X", "mission": "m", "module_id": "pilotage", "actions": ["lancer_of"]})


def _duplicate_action_id(raw: dict[str, Any]) -> None:
    raw["modules"][1]["actions"].append(copy.deepcopy(raw["modules"][0]["actions"][0]))


def _unknown_role_in_plan(raw: dict[str, Any]) -> None:
    raw["role_plans"][1]["roles"].append("fantome")


REFUSALS = [
    (_unknown_action, ("action inconnue x",)),
    (_plan4_without_ordonnanceur, ("plan à 4 joueurs", "action lancer_of sans rôle")),
    (_plan4_with_production, ("tenue par 2 rôles",)),
    (_duplicate_plan, ("4 joueurs en double",)),
    (_zero_players, ("players",)),
    (_seven_players, ("players",)),
    (_wrong_module, ("module production sans action",)),
    (_role_in_no_plan, ("dans aucun plan",)),
    (_duplicate_action_id, ("identifiant en double",)),
    (_unknown_role_in_plan, ("rôle inconnu fantome",)),
]


@pytest.mark.parametrize(("mutate", "words"), REFUSALS, ids=[m.__name__.lstrip("_") for m, _ in REFUSALS])
def test_invalid_t7_spec_is_refused(mutate, words) -> None:
    raw = t7_spec()
    mutate(raw)
    refused(raw, *words)


def test_generate_at_the_bounds_of_limits() -> None:
    """Avant et après l'étape 3b : verte dès maintenant (pas de plan généré) et doit le rester."""
    from gmix.game.spec import load_pack

    check_bounds(load_pack("usine")["limits"])


# --- Étape 3a : fonctions pures du moteur et droits ---------------------------------------------------------------

PLAN4 = ["acheteur", "ordonnanceur", "chef_de_ligne", "responsable_maintenance"]
PLAN5 = ["acheteur", "ordonnanceur", "chef_de_ligne", "technicien_methodes", "chef_equipe_maintenance"]


def test_role_plan_picks_the_largest_plan_not_above_n() -> None:
    spec = t7_spec()
    assert engine.role_plan(spec, 4) == PLAN4
    assert engine.role_plan(spec, 6) == PLAN4  # le plus grand plan <= n
    assert engine.role_plan(spec, 3) == list(USINE_ROLES)
    assert engine.role_plan(spec, 1) == list(USINE_ROLES)  # sous le plus petit plan : le plus petit
    assert engine.role_plan(spec, 0) == list(USINE_ROLES)  # 0 se lit 1
    spec["role_plans"] = []
    assert engine.role_plan(spec, 4) == [r["id"] for r in spec["roles"]]  # sans plans : tous les rôles


def test_role_actions_and_action_owners() -> None:
    spec = t7_spec()
    assert engine.role_actions(spec, "acheteur") == {"commander_mp"}
    assert engine.role_actions(spec, "responsable_production") == {"lancer_of", "commander_mp"}  # vide : module
    assert engine.action_owners(spec, PLAN4) == {
        "commander_mp": "acheteur", "lancer_of": "ordonnanceur", "proteger_goulot": "chef_de_ligne",
        "preventif": "responsable_maintenance", "priorite_reparation": "responsable_maintenance",
    }  # fmt: skip
    owners = engine.action_owners(spec, None)  # None : module.role_id
    assert owners["lancer_of"] == "responsable_production" and owners["proteger_goulot"] == "chef_de_ligne"


def test_assign_seats_free_roles_first_then_doubles_from_the_first_role() -> None:
    six = [(f"u{i}", None) for i in range(1, 7)]
    seats = engine.assign_seats(PLAN5, six)
    assert [seats[f"u{i}"] for i in range(1, 7)] == [*PLAN5, "acheteur"]  # U2 : le 6e double acheteur
    seats = engine.assign_seats(PLAN4, [("a", "chef_de_ligne"), ("b", None), ("c", "inconnu"), ("d", None)])
    assert seats == {"a": "chef_de_ligne", "b": "acheteur", "c": "ordonnanceur", "d": "responsable_maintenance"}


def _act_t7(spec: dict[str, Any], role: str | None, action: str, plan: list[str]) -> str:
    state = engine.start(spec, engine.initial_state(spec))
    offer = spec["offers"][0]
    values = {"lancer_of": {"line": spec["lines"][0]["id"], "quantity": 10},
              "commander_mp": {"offer": offer["id"], "pallets": offer["min_order"]}}.get(action, {})  # fmt: skip
    module = next(m["id"] for m in spec["modules"] if any(a["id"] == action for a in m["actions"]))
    return engine.act(spec, state, module, action, values, actor=ACTOR | {"role": role}, manager=False, plan=plan)[1]


def test_act_refused_for_another_role_of_the_plan() -> None:
    spec = t7_spec()
    with pytest.raises(engine.GameRuleError, match="Cette action revient au rôle « Ordonnanceur·se »"):
        _act_t7(spec, "acheteur", "lancer_of", PLAN4)
    with pytest.raises(engine.GameRuleError, match="Choisissez un rôle"):
        _act_t7(spec, None, "commander_mp", PLAN4)


def test_act_allowed_for_the_role_that_owns_the_action_in_the_plan() -> None:
    assert _act_t7(t7_spec(), "acheteur", "commander_mp", PLAN4)  # module pilotage, rôle acheteur : permis


# --- Étape 3b : pilote automatique par action, génération ----------------------------------------------------------


def test_played_actions_follow_the_held_roles_and_the_actions_of_the_week() -> None:
    spec = t7_spec()
    state = engine.start(spec, engine.initial_state(spec))
    assert engine.played_actions(spec, state, False, None) == {a["id"] for m in spec["modules"] for a in m["actions"]}
    assert engine.played_actions(spec, state, True, None) == set()
    assert engine.played_actions(spec, state, False, {"acheteur"}) == {"commander_mp"}
    state["log"].append({"week": state["week"], "kind": "decision", "module": "production",
                         "action": "proteger_goulot"})  # fmt: skip
    assert engine.played_actions(spec, state, False, {"acheteur"}) == {"commander_mp", "proteger_goulot"}


def test_generated_usine_spec_declares_the_role_plans() -> None:
    spec = SimSpec.model_validate(generate(params("usine", "industrie", 1, 1))).model_dump(mode="json")
    assert [p["players"] for p in spec["role_plans"]] == [1, 2, 3, 4, 5]
    assert any(r["id"] == "acheteur" for r in spec["roles"])


def test_atelier_spec_has_no_role_plans() -> None:
    assert not generate(params("atelier", "industrie", 1, 2)).get("role_plans")


@pytest.mark.parametrize("held", subsets(list(USINE_ROLES), True), ids=lambda h: ",".join(h) or "-")
def test_spec_with_role_plans_keeps_the_plan_of_three_roles_identical(reference, held) -> None:
    """Invariant du §3 ter : plans déclarés, 3 rôles du plan à 3 tenus -> même `history` et même `public_state`."""
    expected = reference[case_key("usine", "industrie", 1, 1, held)]
    assert capture(t7_spec(), held) == expected


if __name__ == "__main__":
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(json.dumps(build_reference(), ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"{FIXTURE} : {FIXTURE.stat().st_size} octets")


@pytest.mark.parametrize(
    ("held", "cash", "stockouts", "otif"),
    [((), 179597, 0, 100.0), (("acheteur",), 41596, 10, 20.0), (("ordonnanceur",), -866, 0, 0.0),
     (("acheteur", "ordonnanceur"), 7054, 0, 0.0)],
)  # fmt: skip
def test_one_pilotage_action_held_keeps_the_rule_of_the_other(held, cash, stockouts, otif) -> None:
    """Revue T7 : un seul des deux gestes de pilotage tenu (sans décision) : l'autre garde sa règle automatique.
    `acheteur` seul : plus d'achat, OF automatiques (ruptures) ; `ordonnanceur` seul : achats auto, plus d'OF."""
    last = play(t7_spec(), held)["history"][-1]
    assert (last["cash"], last["stockouts"], last["otif"]) == (cash, stockouts, otif)
