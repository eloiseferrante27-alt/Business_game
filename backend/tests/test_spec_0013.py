"""Contrats de l'ADR 0013 (tranche T2, annexe 0013 §7) : tous les champs sont facultatifs, les specs v2 existantes
restent valides, et chaque nouvelle règle de `SimSpec` / `GameParams` / `DesignRequest` a son refus testé.
Le cas de la VAN (100 000, 30 000, 5 ans, 8 % -> 19 781,30) est pour D2 : `gmix.game.finance` n'existe pas encore."""

import copy
import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from gmix.game import spec as spec_module
from gmix.game.generation import generate
from gmix.game.spec import (
    DesignRequest,
    GameParams,
    Room,
    SimSpec,
    TrainerExcerpt,
    default_params,
    load_pack,
)

from .test_spec_contract import PACK, designed_spec, factory_spec, machine, params, usine_pack  # noqa: F401

INTERIOR = [
    "reception",
    "stock_mp",
    "production",
    "qualite",
    "emballage",
    "maintenance",
    "pilotage",
    "quai",
    "entrepot_pf",
]
DOC = uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def campus_pack(usine_pack, monkeypatch):  # noqa: F811  # pack local + archétype, ambiance et bornes de l'ADR 0013
    real = spec_module.load_pack

    def patched(pack_id: str) -> dict[str, Any]:
        pack = copy.deepcopy(real(pack_id))
        pack["limits"] |= {"suppliers": [3, 8, 3], "buildings": [1, 3, 1]}
        pack["building_archetypes"] = {
            "hall": {"label": "Hall", "rooms": {"atelier": {"label": "Atelier", "blocks": INTERIOR}}}
        }
        pack["ambiances"] = {"hiver": {"label": "Hiver", "styles": ["brique"]}}
        return pack

    monkeypatch.setattr(spec_module, "load_pack", patched)


def refused(raw: dict[str, Any], *words: str) -> None:
    with pytest.raises(ValidationError) as caught:
        SimSpec.model_validate(raw)
    assert all(word in str(caught.value) for word in words), str(caught.value)


# --- 1. Non-régression -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("pack_id", ["atelier", "usine"])
def test_real_packs_generate_specs_without_the_new_fields(pack_id: str) -> None:
    load_pack.cache_clear()
    spec = SimSpec.model_validate(generate(GameParams(**default_params(pack_id))))
    assert (spec.world.buildings, spec.world.rooms, spec.finance, spec.trainer_excerpts) == ([], [], None, [])
    assert (spec.version, spec.world.ambiance) == (2, None)


def test_hand_written_v2_spec_stays_valid(usine_pack) -> None:  # noqa: F811
    spec = SimSpec.model_validate(factory_spec())
    assert spec.version == 2 and spec.factory is not None
    assert (spec.factory.clients, spec.factory.logistics.walk_m_per_min) == ([], None)


# --- 2. GameParams -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "words"),
    [
        ({"suppliers": 5}, "non réglable"),
        ({"clients": 2}, "non réglable"),
        ({"buildings": 2}, "non réglable"),
        ({"ambiance": "xx"}, "ambiance inconnue"),
        ({"world_plan": [{"archetype": "xx", "department_ids": ["ligne"]}]}, "archétype inconnu"),
        (
            {"world_plan": [{"archetype": "xx", "department_ids": ["ligne"]}] * 2},
            "un seul bâtiment",
        ),
    ],
)
def test_game_params_refuse_world_choices_the_pack_does_not_declare(usine_pack, changes, words) -> None:  # noqa: F811
    with pytest.raises(ValidationError, match=words):
        GameParams(**params(**changes))


def test_game_params_check_the_pack_bounds_and_the_plan(campus_pack) -> None:
    assert GameParams(**params(suppliers=5, buildings=2, ambiance="hiver")).suppliers == 5
    with pytest.raises(ValidationError, match="entre 3 et 8"):
        GameParams(**params(suppliers=2))
    plan = [{"archetype": "hall", "department_ids": INTERIOR}]
    assert len(GameParams(**params(world_plan=plan, buildings=1)).world_plan) == 1
    with pytest.raises(ValidationError, match="1 bâtiments pour 2 imposés"):
        GameParams(**params(world_plan=plan, buildings=2))


# --- 3. DesignRequest --------------------------------------------------------------------------------------------

BRIEF = "Former des BTS au goulot de la ligne."


def test_design_request_refuses_buildings_on_a_pack_without_the_limit(usine_pack) -> None:  # noqa: F811
    with pytest.raises(ValueError, match="non réglable"):
        DesignRequest(pack="usine", brief=BRIEF, fixed={"buildings": 2})


def test_design_request_accepts_buildings_when_the_pack_declares_the_limit(campus_pack) -> None:
    assert DesignRequest(pack="usine", brief=BRIEF, fixed={"buildings": 2}).fixed == {"buildings": 2}


def test_design_request_domain_and_documents(usine_pack) -> None:  # noqa: F811
    with pytest.raises(ValueError, match="n'appartient pas"):
        DesignRequest(pack="usine", brief=BRIEF, domain="finance-entreprise")
    assert DesignRequest(pack="usine", brief=BRIEF, domain="supply-chain").domain == "supply-chain"
    docs = [uuid.uuid4() for _ in range(6)]
    assert len(DesignRequest(pack="usine", brief=BRIEF, document_ids=docs[:5]).document_ids) == 5
    with pytest.raises(ValueError, match="en double"):
        DesignRequest(pack="usine", brief=BRIEF, document_ids=[docs[0], docs[0]])
    with pytest.raises(ValidationError):
        DesignRequest(pack="usine", brief=BRIEF, document_ids=docs)


# --- 4. Campus ---------------------------------------------------------------------------------------------------


def campus_spec() -> dict[str, Any]:
    spec = factory_spec()
    spec["world"] |= {
        "template": "campus", "ambiance": "hiver",
        "buildings": [{"id": "b1", "archetype": "hall", "label": "Hall A", "area": (-20, -20, 20, 10),
                       "entrance": (0, 10), "style": "brique"}],
        "rooms": [{"id": "b1.atelier", "building_id": "b1", "kind": "atelier", "label": "Atelier",
                   "area": (-15, -18, 15, 8), "department_ids": ["production", "pilotage"], "doors": [(0, 8)]}],
    }  # fmt: skip
    for department in spec["departments"][:2]:
        department["room_id"] = "b1.atelier"
    return spec


def test_campus_spec_is_valid_and_round_trips(campus_pack) -> None:
    spec = SimSpec.model_validate(campus_spec())
    assert [d.room_id for d in spec.departments] == ["b1.atelier", "b1.atelier", None]
    assert SimSpec.model_validate(spec.model_dump(mode="json")) == spec


@pytest.mark.parametrize(
    ("mutation", "words"),
    [
        (lambda s: s["world"].update(template="usine"), ("hors d'un world.template",)),
        (lambda s: s["world"].update(rooms=[]), ("pur décor",)),
        (lambda s: s["world"]["rooms"][0].update(department_ids=["production"]), ("dans aucune pièce", "pilotage")),
        (lambda s: s["departments"][1].update(room_id=None), ("room_id None au lieu de",)),
        (lambda s: s["world"]["rooms"][0].update(area=(-30, -18, 15, 8)), ("hors du bâtiment",)),
        (lambda s: s["world"]["rooms"][0].update(kind="bureau"), ("non permis",)),
        (lambda s: s["world"]["buildings"][0].update(style="verre"), ("style inconnu",)),
        (lambda s: s["world"]["buildings"][0].update(archetype="tour"), ("archétype inconnu",)),
        (lambda s: s["world"].update(ambiance="ete"), ("ambiance inconnue",)),
        (lambda s: s["world"]["rooms"][0].update(department_ids=["production", "pilotage", "fournisseur"]),
         ("département intérieur inconnu",)),
        (lambda s: s["world"].update(buildings=[], template="usine"), ("pièces sans bâtiment",)),
        (lambda s: s["world"].update(buildings=[]), ("campus", "sans bâtiment")),
    ],
)  # fmt: skip
def test_campus_spec_refuses_each_rule(campus_pack, mutation, words: tuple[str, ...]) -> None:
    raw = campus_spec()
    mutation(raw)
    refused(raw, *words)


def test_a_department_is_housed_in_one_room_only(campus_pack) -> None:
    raw = campus_spec()
    raw["world"]["rooms"].append({**raw["world"]["rooms"][0], "id": "b1.depot", "department_ids": ["production"]})
    refused(raw, "logé dans b1.atelier et b1.depot")


# --- 5. Identifiants ---------------------------------------------------------------------------------------------


def test_building_room_and_excerpt_ids_are_checked() -> None:
    room = {"building_id": "b1", "kind": "atelier", "label": "Atelier", "area": (0, 0, 4, 4),
            "department_ids": ["ligne"], "doors": [(0, 0)]}  # fmt: skip
    assert Room(id="b1.atelier", **room).id == "b1.atelier"
    with pytest.raises(ValidationError):
        Room(id="b5.atelier", **room)
    building = {"archetype": "hall", "label": "Hall", "area": (0, 0, 4, 4), "entrance": (0, 0), "style": "brique"}
    from gmix.game.spec import Building

    assert Building(id="b4", **building).id == "b4"
    with pytest.raises(ValidationError):
        Building(id="x1", **building)
    for bad in ("autre#1", f"{DOC}#0", f"{DOC}#x", str(DOC)):
        with pytest.raises(ValidationError):
            TrainerExcerpt(id=bad, document_id=DOC, title="Cours", text="Un passage.")
    assert TrainerExcerpt(id=f"{DOC}#1", document_id=DOC, title="Cours", text="Un passage.").validated is False


# --- 6. Passages du formateur ------------------------------------------------------------------------------------


def excerpt(n: int = 1, **extra: Any) -> dict[str, Any]:
    return {"id": f"{DOC}#{n}", "document_id": str(DOC), "title": "Cours", "text": "Un passage cité tel quel."} | extra


def with_excerpts(*excerpts: dict[str, Any], cited: list[str] | None = None) -> dict[str, Any]:
    raw = designed_spec()
    raw["trainer_excerpts"] = list(excerpts)
    raw["design"]["objectives"][0]["excerpt_ids"] = cited if cited is not None else [e["id"] for e in excerpts]
    return raw


def test_a_cited_excerpt_is_valid_even_when_not_validated(usine_pack) -> None:  # noqa: F811
    spec = SimSpec.model_validate(with_excerpts(excerpt()))
    assert [e.validated for e in spec.trainer_excerpts] == [False]  # brouillon ; l'API relit la base à la publication
    assert SimSpec.model_validate(with_excerpts(excerpt(validated=True))).trainer_excerpts[0].validated


def test_excerpts_must_be_cited_and_citations_known(usine_pack) -> None:  # noqa: F811
    raw = designed_spec()
    raw["trainer_excerpts"] = [excerpt()]
    refused(raw, "cité par aucun objectif")
    refused(with_excerpts(excerpt(), cited=[f"{DOC}#1", f"{DOC}#2"]), "absent de trainer_excerpts", f"{DOC}#2")
    refused(with_excerpts(excerpt(), excerpt()), "en double")
    raw = with_excerpts(excerpt())
    raw["design"]["objectives"][0]["excerpt_ids"] += [f"{DOC}#2", f"{DOC}#3"]
    with pytest.raises(ValidationError):  # 2 citations au plus par objectif
        SimSpec.model_validate(raw)


# --- 7. Finance --------------------------------------------------------------------------------------------------

FINANCE = {"customer_terms_days": 30, "supplier_terms_days": 45, "overdraft_limit": 5000, "discount_rate_year": 0.08}
DSO = {"id": "dso", "label": "Délai clients", "op": "<=", "target": 45}


def finance_spec(**changes: Any) -> dict[str, Any]:
    raw = factory_spec()
    raw["finance"] = FINANCE | changes
    return raw


def test_finance_spec_is_valid_and_opens_the_finance_indicators(usine_pack) -> None:  # noqa: F811
    raw = finance_spec()
    raw["criteria"] = [DSO]
    assert SimSpec.model_validate(raw).finance is not None
    raw = factory_spec()
    raw["criteria"] = [DSO]
    refused(raw, "critère dso", "indicateur inconnu")


def invest(**extra: Any) -> dict[str, Any]:
    return {"id": "tour_neuf", "label": "Tour", "machine_id": "l1-m1", "capex": 1000, "life_years": 5,
            "annual_cash_flow": 300} | extra  # fmt: skip


@pytest.mark.parametrize(
    ("changes", "words"),
    [
        ({"investments": [invest(machine_id="l9-m9")]}, ("machine inconnue", "l9-m9")),
        ({"investments": [invest(effects={"vitesse": 1.1})]}, ("effet vitesse inconnu",)),
        ({"investments": [invest(effects={"mtbf_h": 0})]}, ("effet mtbf_h", "non positif")),
        ({"loan_offers": [{"id": "pret_a", "kind": "emprunt", "label": "Prêt", "rate_year": 0.05, "max_principal": 1,
                           "weeks": 4}] * 2}, ("offre de prêt", "en double")),
    ],
)  # fmt: skip
def test_finance_refuses_each_rule(usine_pack, changes, words: tuple[str, ...]) -> None:  # noqa: F811
    refused(finance_spec(**changes), *words)


def test_finance_bounds_and_requirements(usine_pack, sim_spec) -> None:  # noqa: F811
    with pytest.raises(ValidationError):
        SimSpec.model_validate(finance_spec(customer_terms_days=61))
    refused(sim_spec | {"finance": FINANCE}, "moteur factory requis")
    raw = factory_spec()
    raw["modules"][0]["actions"].append({"id": "investir", "label": "Investir", "fields": []})
    refused(raw, "action investir", "module finance absent")
    raw["finance"] = FINANCE
    SimSpec.model_validate(raw)


# --- 8. Usine variée ---------------------------------------------------------------------------------------------


def two_products() -> dict[str, Any]:
    raw = factory_spec()
    raw["products"].append({**raw["products"][0], "id": "p2", "name": "Vanne", "line_id": "l2"})
    raw["lines"][1]["product_id"] = "p2"
    raw["factory"]["bom"] = [{"component_id": "c1", "per_unit": 1, "product_id": p} for p in ("p1", "p2")]
    return raw


def client(n: int, **extra: Any) -> dict[str, Any]:
    return {"id": f"c{n}", "name": f"Client {n}", "product_id": "p1", "demand_per_day": 20, "variability": 0.1,
            "promised_days": 3} | extra  # fmt: skip


def test_several_products_need_a_line_and_a_bill_of_materials_each(usine_pack) -> None:  # noqa: F811
    assert len(SimSpec.model_validate(two_products()).products) == 2
    raw = two_products()
    raw["lines"][1]["product_id"] = "p1"
    refused(raw, "produit p2 sans ligne")
    raw = two_products()
    raw["factory"]["bom"].pop()
    refused(raw, "produit p2 sans nomenclature")
    raw = two_products()
    raw["factory"]["bom"][0]["product_id"] = "zz"
    refused(raw, "composant ou produit inconnu")


def test_clients_and_speeds(usine_pack) -> None:  # noqa: F811
    raw = factory_spec()
    raw["factory"]["clients"] = [client(1), client(2)]
    assert len(SimSpec.model_validate(raw).factory.clients) == 2
    raw["factory"]["clients"] = [client(1), client(1)]
    refused(raw, "identifiants de client en double")
    raw["factory"]["clients"] = [client(1, product_id="zz")]
    refused(raw, "client c1", "produit ou site inconnus")
    raw["factory"]["clients"] = [client(1, site_id="nulle_part")]
    refused(raw, "client c1")
    raw["factory"]["clients"] = [client(n) for n in (1, 2, 3, 4)] + [client(1)]
    with pytest.raises(ValidationError):
        SimSpec.model_validate(raw)
    raw = factory_spec()
    raw["factory"]["logistics"]["walk_m_per_min"] = 70
    refused(raw, "se renseignent ensemble")
    raw["factory"]["logistics"]["forklift_m_per_min"] = 120
    refused(raw, "si et seulement si")
    raw = factory_spec()
    raw["factory"]["machines"][0] = machine(1, 1, type="m3")  # Machine.type : clé du pack, facultative
    SimSpec.model_validate(raw)
    raw["factory"]["machines"][0] = machine(1, 1, type="zz")
    refused(raw, "type inconnu du pack")
