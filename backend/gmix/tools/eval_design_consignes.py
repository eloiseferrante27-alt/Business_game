"""Respect des consignes du formateur par `factory.design` (vrai modèle, aucune doublure), sur les 10 briefs du
protocole docs/audits/protocole-jeux-ia.md (ai/evals/design.consignes.jsonl) : paramètres conçus seulement.

Usage (depuis backend\\) : python -m gmix.tools.eval_design_consignes --label a [--model main] [--runs 1] [--no-guard]
Par jeu, 5 points : niveau, ton, aléas, secteur et imposés, unmet. Rapport et conceptions :
ai/evals/results/design-consignes-<date>/<label>.md et .json. `--model` remplace l'alias de la tâche le temps de
l'essai ; `GMIX_AI_DIR` pointe vers une copie de ai/ pour essayer un prompt sans toucher l'original.
Fermer Godot avant : il occupe le GPU.
"""

import argparse
import asyncio
import json
import re
import statistics
from dataclasses import asdict
from datetime import date
from typing import Any

import httpx

from gmix.game.spec import FACTORY_SECTIONS, load_pack
from gmix.llm import factory_design
from gmix.llm.factory_design import TASK, FactoryDesign, degenerate, design_factory, design_schema
from gmix.llm.service import LLMService
from gmix.settings import get_settings

POINTS = ("niveau", "ton", "aleas", "secteur", "unmet")
_UNMET_WORDS = {
    "marketing": r"marketing|digital|r[ée]seaux|campagne|publicit|communication",
    "objectif": r"objectif|tr[ée]sorerie|livraison|otif|fix[ée]",
}


def score(case: dict, d: FactoryDesign, keep: dict, pack: dict) -> dict[str, bool]:
    """Les 5 points du jeu ; une consigne absente du cas compte pour acquise (point sans objet)."""
    p, ex = d.params, case["expect"]
    plan = p["event_plan"]
    late = all(e["week"] > p["weeks"] * 2 / 3 for e in plan)  # « dernières semaines » : dernier tiers
    played = set(p["modules"])
    aleas = (
        p["events"] in ex.get("events_in", [p["events"]])
        and (not plan if ex.get("plan") == "empty" else True)
        and (bool(plan) and late if ex.get("plan") == "late" else True)
        and all(e["week"] <= p["weeks"] and played & set(pack["events"][e["event_id"]]["modules"]) for e in plan)
    )
    sector = (
        p["theme"] == ex.get("theme", p["theme"])
        and p["weeks"] >= ex.get("weeks_min", 0)
        and p["options"]["lines"] == ex.get("lines", p["options"]["lines"])
        and all(p[k] == v for k, v in keep.items())
    )
    kind = ex.get("unmet", "any")
    unmet = not any(degenerate(u) for u in d.unmet) and (
        not d.unmet if kind == "empty" else bool(re.search(_UNMET_WORDS[kind], " ".join(d.unmet), re.I))
    )
    return {
        "niveau": p["difficulty"] in ex.get("niveau", [p["difficulty"]]),
        "ton": p["agent_tone"] in ex.get("ton", [p["agent_tone"]]),
        "aleas": aleas,
        "secteur": sector and not d.fallback,
        "unmet": unmet and not d.fallback,
    }


async def loaded(base_url: str) -> list[dict[str, Any]]:
    """Modèles chargés par Ollama (/api/ps) : taille totale et part en VRAM."""
    async with httpx.AsyncClient(timeout=10) as client:
        data = (await client.get(f"{base_url}/api/ps")).json()
    return [{k: m.get(k) for k in ("name", "size", "size_vram", "context_length")} for m in data.get("models", [])]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--model", help="alias de models.yaml pour factory.design (essai seulement)")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--no-guard", action="store_true", help="désactive le refus des unmet dégénérés")
    args = parser.parse_args()
    settings = get_settings()
    if args.no_guard:
        factory_design.degenerate = lambda _t: False
    cases = [
        json.loads(line)
        for line in (settings.gmix_ai_dir / "evals" / "design.consignes.jsonl").read_text("utf-8").splitlines()
        if line
    ]
    pack = load_pack("usine")
    llm = LLMService.from_settings(with_cache=False)
    if args.model:
        llm.catalog.tasks[TASK].model = args.model
    rows: list[tuple[dict, FactoryDesign, dict[str, bool], dict]] = []
    changed: list[bool] = []
    try:
        await design_factory(llm, "Un atelier de soudure pour des BTS.", seed=0)  # chauffe : chargement hors mesure
        for run in range(args.runs):
            done: dict[str, FactoryDesign] = {}
            for case in cases:
                seed = case["seed"] + run
                if regen := case.get("regen"):  # keep = paramètres du jeu d'origine moins la section (comme le worker)
                    origin = done[regen["from"]].params
                    redo = FACTORY_SECTIONS[regen["section"]] & set(design_schema(pack)["properties"])
                    keep = {k: v for k, v in origin.items() if k not in redo}
                    current = {k: origin[k] for k in redo}  # comme le worker, après correction D14
                    d = await design_factory(
                        llm, case["brief"], seed=seed, keep=keep, note=regen["note"], current=current
                    )
                    changed.append(not d.fallback and any(d.params[k] != v for k, v in current.items()))
                else:
                    keep = case.get("fixed", {})
                    d = await design_factory(llm, case["brief"], seed=seed, keep=keep)
                done[case["id"]] = d
                rows.append((case, d, score(case, d, keep, pack), {}))
        ps = await loaded(settings.ollama_base_url)
    finally:
        await llm.aclose()
    n = len(rows)
    total = sum(sum(s.values()) for _, _, s, _ in rows)
    lat = sorted(d.duration_ms for _, d, _, _ in rows)
    lines = [
        f"# factory.design, respect des consignes - {args.label} - {date.today()}\n",
        f"Modèle : {rows[0][1].model} - prompt v{rows[0][1].prompt_version} - {n} conceptions - garde-fou "
        f"{'coupé' if args.no_guard else 'actif'}\n",
        f"- Respect : {total}/{5 * n} ("
        + ", ".join(f"{k} {sum(s[k] for _, _, s, _ in rows)}/{n}" for k in POINTS)
        + ")",
        f"- Latence : médiane {statistics.median(lat)} ms, max {lat[-1]} ms ; chargement du modèle "
        f"{sum(d.load_ms for _, d, _, _ in rows)} ms au total",
        f"- Tokens par conception : entrée médiane {statistics.median(d.prompt_tokens for _, d, _, _ in rows):.0f}, "
        f"sortie médiane {statistics.median(d.completion_tokens for _, d, _, _ in rows):.0f}",
        f"- Régénérations qui changent la section : {sum(changed)}/{len(changed)}",
        f"- Replis : {sum(d.fallback for _, d, _, _ in rows)} ; essais > 1 : "
        f"{sum(d.attempts > 1 for _, d, _, _ in rows)}",
        f"- Ollama /api/ps après la série : {json.dumps(ps)}\n",
        "| Jeu | " + " | ".join(POINTS) + " | Total | ms | Essais | Niveau | Ton | Aléas | unmet |",
        "|---|" + "---|" * (len(POINTS) + 7),
    ]
    for case, d, s, _ in rows:
        p = d.params
        plan = ",".join(f"s{e['week']}:{e['event_id']}" for e in p["event_plan"]) or "-"
        lines.append(
            f"| {case['id']} | "
            + " | ".join("ok" if s[k] else "NON" for k in POINTS)
            + f" | {sum(s.values())}/5 | {d.duration_ms} | {d.attempts} | {p['difficulty']} | {p['agent_tone']} |"
            f" {p['events']} ({p['weeks']} sem.) {plan} | {' / '.join(d.unmet)[:110].replace('|', '/') or '-'} |"
        )
    out = settings.gmix_ai_dir / "evals" / "results" / f"design-consignes-{date.today()}"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / f"{args.label}.json").write_text(
        json.dumps([{"id": c["id"], "points": s, **asdict(d)} for c, d, s, _ in rows], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print("\n".join(lines), f"\nRapport : {out / (args.label + '.md')}")


if __name__ == "__main__":
    asyncio.run(main())
