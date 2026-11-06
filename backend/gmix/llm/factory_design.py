"""Conception de l'usine par l'IA (ADR 0010, annexe §7) : brief du formateur -> paramètres `GameParams` validés.

Un seul appel `factory.design` à sortie JSON contrainte par le pack (énumérations : le modèle ne peut pas inventer un
identifiant ni un nombre hors bornes). Le brief est une donnée non fiable : une injection lexicale évite tout appel.
Sortie invalide : 2 réparations au plus (erreurs seules renvoyées, pas la sortie fautive), puis repli déterministe
sur `default_params` marqué `fallback`. Aucune exception ne sort : un worker publie le résultat.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from gmix.game.npc import looks_like_injection
from gmix.game.spec import TEXT_CHARS, GameParams, default_params, forbidden_in_text, load_pack
from gmix.llm.ollama import OllamaError
from gmix.llm.prompts import load_prompt
from gmix.llm.service import BudgetExceeded, LLMService, ModelUnavailable

TASK = "factory.design"
MAX_REPAIRS = 2
MAX_UNMET = 2


@dataclass(slots=True)
class FactoryDesign:
    params: dict[str, Any]  # GameParams.model_dump(mode="json"), toujours valide
    fallback: bool  # True : paramètres par défaut du pack, la sortie du modèle n'a pas servi
    reasons: list[str] = field(default_factory=list)  # pourquoi les tentatives ou le repli (français)
    attempts: int = 0  # appels au modèle (1 = valide du premier coup)
    unmet: list[str] = field(default_factory=list)  # demandes que l'usine ne simule pas
    model: str | None = None
    prompt_version: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0
    brief_sha256: str = ""


def _lines(items: dict[str, Any], desc: str = "description") -> str:
    return "\n".join(f"- {k} : {v['label'] if 'label' in v else v['title']} — {v.get(desc, v.get('detail', ''))}"
                     for k, v in items.items())  # fmt: skip


def _kept_lines(keep: dict[str, Any]) -> str:
    """Choix imposés au modèle, « clé : valeur » (sans graine ni pack, qui ne sont pas des choix)."""
    return (
        "\n".join(f"- {k} : {json.dumps(v, ensure_ascii=False)}" for k, v in keep.items() if k not in ("seed", "pack"))
        or "aucun"
    )


def _variables(
    pack: dict[str, Any], brief: str, keep: dict[str, Any] | None = None, note: str | None = None
) -> dict[str, str]:
    sites = _network_sites(pack)
    tunables = "\n".join(f"- {k} : {v['label']}" for k, v in pack["tunables"].items())
    events = "\n".join(f"- {k} : {v['title']} — {v['description']}" for k, v in pack["events"].items())
    return {
        "brief": brief.replace("<<<", "").replace(">>>", ""),
        "kept": _kept_lines(keep or {}).replace("<<<", "").replace(">>>", ""),
        "note": (note or "aucune").replace("<<<", "").replace(">>>", ""),
        "themes": _lines(pack["themes"]),
        "modules": _lines(pack["modules"]),
        "extra_agents": _lines(
            {k: {"title": v["title"], "description": v["description"]} for k, v in pack.get("extra_agents", {}).items()}
        )
        or "aucun",  # fmt: skip
        "difficulties": _lines(pack["difficulties"], "detail"),
        "tunables": tunables,
        "events": events,
        "events_levels": "\n".join(f"- {k} : {v['label']}" for k, v in pack["events_levels"].items()),
        "tones": "\n".join(f"- {k} : {v['label']}" for k, v in pack["agent_tones"].items()),
        "network": "\n".join(f"- {k} : {' ou '.join(v['distances'])}" for k, v in sites.items()) or "aucun choix",
    }


def _network_sites(pack: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in pack.get("network", {}).get("sites", {}).items() if len(v["distances"]) > 1}


def design_schema(pack: dict[str, Any], keep: dict[str, Any] | None = None) -> dict[str, Any]:
    """Schéma JSON du format contraint, construit depuis le pack (aucune valeur en dur), sans les clés gardées."""

    def enum(values: Any) -> dict[str, Any]:
        return {"type": "string", "enum": list(values)}

    def obj(props: dict[str, Any]) -> dict[str, Any]:
        return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}

    low, high, _ = pack["limits"]["weeks"]
    props: dict[str, Any] = {
        "on_topic": {"type": "boolean"},
        "theme": enum(pack["themes"]),
        "modules": {"type": "array", "items": enum(pack["modules"]), "minItems": 1, "maxItems": len(pack["modules"])},
        "extra_agents": {"type": "array", "items": enum(pack.get("extra_agents", {})), "maxItems": 3},
        "agent_tone": enum(pack["agent_tones"]),
        "difficulty": enum(pack["difficulties"]),
        "weeks": {"type": "integer", "minimum": low, "maximum": high},
        "events": enum(pack["events_levels"]),
        "tunings": obj({k: enum(pack["difficulties"]) for k in pack["tunables"]}),
        "event_plan": {
            "type": "array",
            "maxItems": 3,
            "items": obj(
                {"week": {"type": "integer", "minimum": 2, "maximum": high}, "event_id": enum(pack["events"])}
            ),
        },  # fmt: skip
        "unmet": {
            "type": "array",
            "maxItems": MAX_UNMET,
            "items": {"type": "string", "pattern": f"^[{TEXT_CHARS}]{{10,120}}$"},  # liste blanche bornée (annexe 0008)
        },  # fmt: skip
    }
    for p in pack.get("params", []):
        if p["type"] == "int":
            props[f"option_{p['id']}"] = {"type": "integer", "minimum": p["min"], "maximum": p["max"]}
    if sites := _network_sites(pack):
        props["network"] = obj({k: enum(v["distances"]) for k, v in sites.items()})
    keep = keep or {}
    drop = {k for k in keep if k in props} | (
        {p for p in props if p.startswith("option_")} if "options" in keep else set()
    )
    return obj({k: v for k, v in props.items() if k not in drop})


def _params_from(
    pack_id: str, pack: dict[str, Any], data: dict[str, Any], seed: int, keep: dict[str, Any]
) -> GameParams:
    base = default_params(pack_id)
    options = {**base["options"], **{k[7:]: v for k, v in data.items() if k.startswith("option_")}}
    difficulty = data.get("difficulty", keep.get("difficulty"))
    tunings = {k: v for k, v in (data.get("tunings") or {}).items() if v != difficulty}  # égal au profil = sans effet
    chosen = {k: data[k] for k in ("theme", "modules", "extra_agents", "agent_tone", "difficulty", "weeks", "events",
                                   "event_plan", "network") if k in data}  # fmt: skip
    return GameParams.model_validate(
        {**base, **chosen, "options": options, "tunings": tunings, "seed": seed, **keep}
    )  # keep l'emporte


def _errors(
    pack_id: str, pack: dict[str, Any], data: dict[str, Any], seed: int, keep: dict[str, Any]
) -> tuple[GameParams | None, list[str]]:
    errors = [f"unmet : pas de chiffre ni de lien ({u[:30]}…)" for u in data.get("unmet", []) if forbidden_in_text(u)]
    try:
        params = _params_from(pack_id, pack, data, seed, keep)
    except ValidationError as exc:
        return None, errors + [f"{'.'.join(map(str, e['loc'])) or 'params'} : {e['msg']}" for e in exc.errors()]
    return (None if errors else params), errors


async def design_factory(
    llm: LLMService,
    brief: str,
    *,
    seed: int = 0,
    pack_id: str = "usine",
    keep: dict[str, Any] | None = None,
    note: str | None = None,
) -> FactoryDesign:
    """Paramètres d'usine depuis le brief d'un formateur, toujours valides (repli `fallback=True` sinon).

    `keep` : clés de `GameParams` imposées (hors schéma, identiques en sortie, repli compris) ;
    `note` : consigne libre du formateur pour une régénération (ignorée si elle ressemble à une injection).

    Appelable par un worker : `FactoryDesign.params` s'envoie tel quel à `GameParams(**params)`.
    """
    started = time.monotonic()
    pack = load_pack(pack_id)
    keep = dict(keep or {})
    out = FactoryDesign(
        params={}, fallback=True, brief_sha256=hashlib.sha256(" ".join(brief.split()).encode()).hexdigest()
    )

    def finish(params: GameParams | None) -> FactoryDesign:
        out.params = (
            params or GameParams.model_validate({**default_params(pack_id), "seed": seed, **keep})
        ).model_dump(mode="json")
        out.fallback = params is None
        out.duration_ms = int((time.monotonic() - started) * 1000)
        return out

    if looks_like_injection(brief):
        out.reasons.append("brief écarté : tentative d'injection détectée, paramètres par défaut")
        return finish(None)
    if note and looks_like_injection(note):
        out.reasons.append("consigne écartée : tentative d'injection détectée")
        note = None
    prompt = load_prompt(TASK)
    out.prompt_version = prompt.version
    schema = design_schema(pack, keep)
    base = prompt.render(**_variables(pack, brief, keep, note))
    messages = base
    for attempt in range(MAX_REPAIRS + 1):
        out.attempts = attempt + 1
        try:
            result = await llm.structured(TASK, messages, schema, seed=seed)
        except (ModelUnavailable, BudgetExceeded, OllamaError) as exc:
            out.reasons.append(f"tentative {attempt + 1} : {type(exc).__name__} ({str(exc)[:120]})")
            if not isinstance(exc, OllamaError):
                break  # modèle absent ou brief hors budget : réessayer ne change rien
            messages = prompt.render_repair(base, "- la réponse n'a pas pu être produite ; réponds plus brièvement")
            continue
        out.model = result.usage.model
        out.prompt_tokens += result.usage.prompt_tokens
        out.completion_tokens += result.usage.completion_tokens
        if result.data is None:
            errors = [f"JSON {result.error}"]
        else:
            params, errors = _errors(pack_id, pack, result.data, seed, keep)
            if not errors and params is not None:
                if result.data.get("on_topic") is False:
                    out.reasons.append("brief hors sujet (usine, chaîne logistique) : paramètres par défaut")
                    out.unmet = [u for u in result.data.get("unmet", []) if not forbidden_in_text(u)]
                    return finish(None)
                out.unmet = list(result.data.get("unmet", []))
                return finish(params)
        out.reasons.append(f"tentative {attempt + 1} : " + " | ".join(errors))
        messages = prompt.render_repair(base, "\n".join(f"- {e}" for e in errors))
    out.reasons.append("repli sur les paramètres par défaut du pack")
    return finish(None)
