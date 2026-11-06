"""Évaluation de `factory.design` avec le vrai modèle (Ollama, aucune doublure) sur ai/evals/factory.design.jsonl.

Usage (depuis backend\\) : python -m gmix.tools.eval_factory_design [--runs 1]
Rapport : ai/evals/results/factory.design-<date>.md (valides du premier coup, après réparation, replis, attentes,
latence et tokens par cas). Fermer Godot avant : il occupe le GPU.
"""

import argparse
import asyncio
import json
import statistics
from datetime import date

from gmix.game.spec import FACTORY_SECTIONS, default_params
from gmix.llm.factory_design import FactoryDesign, design_factory
from gmix.llm.service import LLMService
from gmix.settings import get_settings


def regen_args(case: dict) -> dict:
    """Cas de régénération : keep = paramètres par défaut du pack hors clés de la section (ADR 0012 §1)."""
    regen = case.get("regen")
    if not regen:
        return {}
    base = default_params("usine") | {"difficulty": "expert", "theme": "automobile"}
    return {
        "keep": {k: v for k, v in base.items() if k not in FACTORY_SECTIONS[regen["section"]]},
        "note": regen["note"],
    }


def met(expect: dict, d: FactoryDesign, keep: dict | None = None) -> bool:
    p = d.params
    checks = [
        set(expect.get("modules_include", [])) <= set(p["modules"]),
        p["difficulty"] in expect.get("difficulty_in", [p["difficulty"]]),
        p["theme"] in expect.get("theme_in", [p["theme"]]),
        p["events"] in expect.get("events_in", [p["events"]]),
        p["weeks"] <= expect.get("weeks_max", p["weeks"]),
        bool(d.unmet) or not expect.get("unmet_nonempty"),
        d.fallback == expect["fallback"] if "fallback" in expect else True,
        d.attempts == 0 if expect.get("no_model_call") else True,
        all(p[k] == v for k, v in (keep or {}).items()) if expect.get("keep_intact") else True,
    ]
    return all(checks)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    path = get_settings().gmix_ai_dir / "evals" / "factory.design.jsonl"
    cases = [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]
    llm = LLMService.from_settings(with_cache=False)  # sans cache : on mesure le modèle
    rows = []
    try:
        await design_factory(
            llm, cases[0]["brief"], seed=0
        )  # chauffe : le chargement du modèle n'entre pas dans les latences
        for case in cases:
            for run in range(args.runs):
                extra = regen_args(case)
                d = await design_factory(llm, case["brief"], seed=run, **extra)
                rows.append((case, d, met(case["expect"], d, extra.get("keep"))))
    finally:
        await llm.aclose()
    n = len(rows)
    first = sum(1 for _, d, _ in rows if d.attempts == 1 and not d.fallback)
    repaired = sum(1 for _, d, _ in rows if d.attempts > 1 and not d.fallback)
    fb = sum(d.fallback for _, d, _ in rows)
    called = [d for _, d, _ in rows if d.attempts]
    lat = sorted(d.duration_ms for d in called)
    tin = statistics.median(d.prompt_tokens for d in called)
    tout = statistics.median(d.completion_tokens for d in called)
    keys = ("theme", "modules", "difficulty", "weeks", "events", "tunings", "event_plan")
    lines = [
        f"# factory.design - {date.today()}\n",
        f"Modèle : {called[0].model} - prompt v{called[0].prompt_version} - {n} appels ({len(cases)} cas)\n",
        f"- Valides du premier coup : {first}/{n} ; après réparation : {repaired} ; replis : {fb}/{n}",
        f"- Attentes satisfaites : {sum(ok for *_, ok in rows)}/{n}",
        f"- Latence (appels au modèle) : médiane {statistics.median(lat)} ms, max {lat[-1]} ms",
        f"- Tokens par appel : entrée médiane {tin:.0f}, sortie médiane {tout:.0f}\n",
        "| Cas | Attente | Repli | Essais | ms | Raisons |\n|---|---|---|---|---|---|",
    ]
    for case, d, ok in rows:
        reasons = " / ".join(d.reasons)[:160].replace("|", "/")
        shown = json.dumps({k: d.params[k] for k in keys}, ensure_ascii=False)[:300].replace("|", "/")
        lines.append(
            f"| {case['id']} | {'oui' if ok else 'NON'} | {'oui' if d.fallback else 'non'} | {d.attempts} |"
            f" {d.duration_ms} | {reasons} |"
        )
        lines.append(f"|  | params | | | | {shown} |")
    out = path.parent / "results" / f"factory.design-{date.today()}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:7]), f"\nRapport : {out}")


if __name__ == "__main__":
    asyncio.run(main())
