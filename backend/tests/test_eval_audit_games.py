"""Outil d'audit des jeux IA (gmix.tools.eval_audit_games) avec un modèle simulé : fichiers, contrôles, régénération."""

import json
from pathlib import Path

from gmix.llm.catalog import load_catalog
from gmix.llm.service import LLMService
from gmix.tools.eval_audit_games import NOT_FOUND, load_entries, run_game, summary, trace_numbers

from .test_factory_design import GOOD, ScriptedOllama


async def test_two_games_are_written_with_checks(tmp_path: Path) -> None:
    entries = {e["id"]: e for e in load_entries()}
    assert len(entries) == 10
    llm = LLMService(load_catalog(), ScriptedOllama([GOOD, GOOD]))  # type: ignore[arg-type]
    done = {}
    done["J02"] = await run_game(llm, entries["J02"], done, tmp_path / "J02")
    done["J08"] = await run_game(llm, entries["J08"], done, tmp_path / "J08")
    for game in ("J02", "J08"):
        names = {f.name for f in (tmp_path / game).iterdir()}
        assert {
            "entree.json",
            "design.json",
            "spec.json",
            "textes.md",
            "briefings-alea.json",
            "controles.json",
        } <= names
    ctl = json.loads((tmp_path / "J02" / "controles.json").read_text("utf-8"))
    assert {"C1", "C2", "C3", "C5", "C7", "C8", "C9", "echecs"} <= ctl.keys() and ctl["C8"]["ok"]
    assert "keep_envoye" in json.loads((tmp_path / "J08" / "entree.json").read_text("utf-8"))
    assert "J08" in summary(list(done.values()))


def test_trace_numbers_skips_notes_and_finds_week_report() -> None:
    sources = {
        "spec": {"placement_rules": [{"note": 4}], "limits": {"weeks": [4, 12]}},
        "rapport": [None, {"packed": {"cases": 124}}],
    }
    lines = ["Durée : 4 semaines.", "Semaine passée : 124 cartons.", "Coût 137 900 €, TRS 13,7 %.", "Écart de 4,25 %."]
    found, missing = trace_numbers(lines, sources, {"text": "Cible 137 900 €."})
    by = {r["nombre"]: r for r in found}
    assert by["4"]["chemin"] == "spec.limits.weeks[0]" and by["4"]["candidats"] == ["spec.limits.weeks[0]"]
    assert by["124"]["chemin"] == "rapport[1].packed.cases"
    assert by["137900"]["texte_libre"] and {r["nombre"] for r in missing} == {"13.7", "4.25"}
    assert all(r["chemin"] == NOT_FOUND for r in missing)
