"""Audit des 10 jeux conçus par l'IA (docs/audits/protocole-jeux-ia.md) avec le vrai modèle, sans passer par l'API.

Usage (depuis backend\\) : python -m gmix.tools.eval_audit_games [--only J01,J02] [--out <dossier>]
Sorties : ai/evals/results/audit-<date>/<Id>/ (fichiers du protocole §2) et resume.md. Fermer Godot avant (GPU).
Une erreur Ollama (mémoire, modèle absent) arrête l'outil avec le message exact : jamais de repli silencieux.
"""

import argparse
import asyncio
import json
import re
import statistics
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from gmix.game import engine, factory_game
from gmix.game.generation import autopilot_check, generate, unsourced
from gmix.game.spec import FACTORY_SECTIONS, GameParams, forbidden_in_text, load_pack
from gmix.llm.factory_design import FactoryDesign, design_factory, design_schema
from gmix.llm.service import LLMService
from gmix.settings import get_settings
from gmix.tools.eval_dialogue import numbers

REPO = get_settings().gmix_ai_dir.parent
PROTOCOL = REPO / "docs" / "audits" / "protocole-jeux-ia.md"
NOTE = re.compile(r"(?:^|\.)note(?:\[\d+\])*$")
NOT_FOUND = "calculé, non retrouvé"
WORDS = re.compile(
    r"\b(deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|vingt|trente|quarante|cinquante|cent|mille|"
    r"moiti[ée]|double|triple|pour cent)\b",
    re.I,
)
TU = re.compile(r"\b(tu|te|toi|ton|ta|tes)\b", re.I)


def load_entries(path: Path = PROTOCOL) -> list[dict]:
    block = re.search(r"```jsonl\n(.*?)```", path.read_text("utf-8"), re.S)
    return [json.loads(line) for line in block.group(1).splitlines() if line.strip()]  # type: ignore[union-attr]


async def design_with_retries(
    llm: LLMService, entry: dict, keep: dict, note: str | None, current: dict | None = None
) -> list[FactoryDesign]:
    """Conception, puis jusqu'à deux relances en repli avec seed + 100 (protocole §2, étape 1)."""
    tries: list[FactoryDesign] = []
    for step in range(3):
        d = await design_factory(
            llm, entry["brief"], seed=entry["seed"] + 100 * step, keep=keep, note=note, current=current
        )
        if d.fallback and any("OllamaError" in r or "ModelUnavailable" in r for r in d.reasons):
            raise RuntimeError("Ollama a échoué : " + " | ".join(d.reasons))
        tries.append(d)
        if not d.fallback:
            break
    return tries


def play(spec: dict, *, held: set[str] | None = None, autopilot: bool = False, trail: list | None = None) -> dict:
    """Partie jouée jusqu'au bout ; `trail` reçoit le rapport de chaque semaine (ce que voit le moteur)."""
    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        state = engine.advance(spec, state, autopilot_all=autopilot, held_roles=held)
        if trail is not None:
            trail.append((state.get("snap") or {}).get("report"))
    return state


def event_view(spec: dict) -> tuple[dict, bool]:
    """Première vue d'une partie en pilote automatique dont l'aléa n'est pas vide ; sinon aléa forcé (semaine 2).
    La vue porte `usure` (bilan des goulots à cette semaine) : les briefings de maintenance en citent les chiffres."""

    def view_of(state: dict) -> dict:
        return engine.public_state(spec, state) | {"usure": factory_game.bottleneck_wear(spec, state)}

    state = engine.start(spec, engine.initial_state(spec))
    while state["status"] == "running":
        view = view_of(state)
        if view["event"]:
            return view, False
        if state["week"] >= 2:
            break
        state = engine.advance(spec, state, autopilot_all=True)
    state = engine.force_event(spec, state, spec["events"][0]["id"])
    return view_of(state), True


def texts(spec: dict, unmet: list[str]) -> list[str]:
    """Textes dans l'ordre de l'écran, une ligne chacun ; les citations commencent par « Source : »."""
    out = [spec["meta"]["title"], spec["meta"]["pitch"]]
    for r in spec["game_rules"]:
        out += [r["text"], f"Source : {r['citation']}"] if r["citation"] else [r["text"]]
    out += [f"{c['label']} {c['op']} {c['target']} (partiel {c.get('partial')})" for c in spec["criteria"]]
    for mod in spec["modules"]:
        out += [mod["title"], mod["description"], f"Pilote automatique : {mod['autopilot']}"]
    for a in spec["agents"]:
        p = a["personality"]
        out += [f"{a['name']}, {a['job']}",
                f"{p['label']} : {p['traits']} ; {p['style']} ; préfixe « {p['prefix']} »", *a["tasks"]]  # fmt: skip
    for n in spec["notions"]:
        out += [n["title"], n["text"], f"Source : {n['citation']}"]
    out += [x for e in spec["events"] for x in (e["title"], e["description"])]
    out += [x for t in spec["tutorial"] for x in (t["title"], t["text"])]
    out += [o["label"] for o in spec["offers"]] + [ln["label"] for ln in spec["lines"]]
    out += [f"Non couvert : {u}" for u in unmet]
    return [t for t in out if t]


def leaves(obj: Any, path: str = "", strings: bool = False):
    """Feuilles numériques (et, si `strings`, nombres des textes) ; les feuilles « note » sont écartées."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{path}.{k}" if path else str(k), strings)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}[{i}]", strings)
    elif isinstance(obj, int | float) and not isinstance(obj, bool) and not NOTE.search(path):
        yield path, float(obj)
    elif strings and isinstance(obj, str) and not NOTE.search(path):
        for n in numbers(obj):
            yield path, float(n)


def trace_numbers(
    lines: list[str], sources: dict[str, Any], prose: dict | None = None
) -> tuple[list[dict], list[dict]]:
    """C1 : chaque nombre affiché (écriture française reconnue), à sa précision ou en pourcentage, avec tous ses
    chemins candidats parmi les feuilles numériques des sources (spec, pack, rapport et état du moteur) ; le premier
    est retenu. Sinon, nombre cité dans un texte du pack (`texte_libre`, circulaire : affiché, non vérifié) ; sinon
    « calculé, non retrouvé » (somme ou arrondi du moteur)."""

    def pool(src: dict[str, Any], strings: bool) -> list[tuple[str, float]]:
        return [
            (f"{n}{p}" if p.startswith("[") else f"{n}.{p}", v)
            for n, o in src.items()
            for p, v in leaves(o, "", strings)
        ]

    strict, weak = pool(sources | {"pack": prose or {}}, False), pool({"pack": prose or {}}, True)
    found, missing = [], []
    for line in lines:
        for token in sorted(numbers(line)):
            n, k = float(token), len(token.split(".")[1]) if "." in token else 0
            hit = [p for p, v in strict if round(v, k) == n or round(v * 100, k) == n]
            free = not hit and [p for p, v in weak if round(v, k) == n or round(v * 100, k) == n]
            paths = hit or free
            row = {"nombre": token, "chemin": paths[0] if paths else NOT_FOUND, "candidats": paths[:5],
                   "texte_libre": bool(free), "texte": line[:100]}  # fmt: skip
            (found if paths else missing).append(row)
    return found, missing


def checks(entry: dict, design: FactoryDesign, spec: dict, art: dict, keep: dict, origin: dict | None) -> dict:
    p, lines = design.params, art["lines"]
    plan = p.get("event_plan") or []
    modules = {m["id"] for m in spec["modules"]}
    events = {e["id"]: e for e in spec["events"]}
    declared = {
        f: re.search(r"^> Source : (.+)$", (REPO / "knowledge/supply-chain" / f).read_text("utf-8"), re.M)
        for f in re.findall(r"^\| (\S+\.md) ", (REPO / "knowledge/supply-chain/SOURCES.md").read_text("utf-8"), re.M)
        if (REPO / "knowledge/supply-chain" / f).exists()
    }
    sources = {m.group(1) for m in declared.values() if m}
    cited = [("notion", n["id"], n["citation"]) for n in spec["notions"]]
    cited += [("règle", r["id"], r["citation"]) for r in spec["game_rules"] if r["citation"]]
    bad_src = [
        f"{k} {i}"
        for k, i, c in cited
        if not c or (c not in sources and not ((m := re.match(r"Fiche (\S+)", c)) and f"{m.group(1)}.md" in declared))
    ]
    found, missing = trace_numbers(
        [x for x in lines if not x.startswith("Source :") and not x.startswith("Non couvert")] + art["facts"],
        {"spec": spec, "etat": art["state"], "vue": art["view"],
         "vue_alea": art["alea"], "debrief": art["debrief"], "rapport": art["reports"]},
        load_pack(p["pack"]),
    )  # fmt: skip
    said = " ".join(lines + art["facts"])
    bad_unmet = [u for u in design.unmet if forbidden_in_text(u) or WORDS.search(u)]
    ev_week = art["alea"]["briefings"]
    informed = [a for a, b in ev_week.items() if b["facts"] and b["facts"][0].startswith("Cette semaine, ")]
    late = [e for e in plan if e["week"] > p["weeks"]]
    dead = [e["event_id"] for e in plan if not modules & set(events[e["event_id"]]["modules"])]
    dead += [e["id"] for e in spec["events"] if not modules & set(e["modules"])]
    auto, passive = art["autopilot"], art["passive"]
    verdicts = {c["id"]: c["verdict"] for c in auto["criteria"]}
    changed = {k for k in p if origin and p[k] != origin.get(k)}
    section = (entry.get("regen") or {}).get("section")
    c7 = not (late or dead) and bool(informed) and (p["events"] != "aucun" or (not plan and not art["pilot_events"]))
    res = {
        "C1": {"ok": not missing, "trouves": len(found), "non_trouves": missing, "chemins": found},
        "C2": {"ok": not bad_src, "citations_fausses": bad_src},
        "C3": {"ok": not bad_unmet, "unmet_fautifs": bad_unmet},
        "C5": {"ok": not TU.search(said), "tutoiement": sorted({m.group(0) for m in TU.finditer(said)})},
        "C7": {"ok": c7, "aleas_sans_module_joue": dead, "plan_apres_fin": late, "agents_informes": informed},
        "C8": {"ok": not [k for k, v in keep.items() if p.get(k) != v]
               and (not origin or changed <= FACTORY_SECTIONS[section]),
               "cles_non_respectees": [k for k, v in keep.items() if p.get(k) != v], "cles_changees": sorted(changed)},
        "C9": {"ok": auto["playable"] and (p["difficulty"] != "decouverte" or set(verdicts.values()) == {"atteint"})
               and any(c["verdict"] != "atteint" for c in passive), "playable": auto["playable"],
               "pilote": verdicts, "passif": {c["id"]: c["verdict"] for c in passive}},
    }  # fmt: skip
    res["echecs"] = [k for k, v in res.items() if not v["ok"]]
    return res


def md(spec: dict, art: dict, unmet: list[str], uns: list[dict]) -> str:
    extra = ["", "## Non sourcé (vue formateur)", *[f"- {u['key']} ({u['status']}) : {u['note']}" for u in uns]]
    return (
        "\n\n".join(art["lines"][:2]) + "\n\n" + "\n".join(f"- {t}" for t in art["lines"][2:]) + "\n" + "\n".join(extra)
    )


def write_all(out: Path, files: dict[str, Any], textes: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), "utf-8")
    (out / "textes.md").write_text(textes, "utf-8")


async def run_game(llm: LLMService, entry: dict, done: dict[str, dict], out: Path) -> dict:
    regen = entry.get("regen")
    origin = done[regen["from"]]["params"] if regen else None
    if regen:
        produced = set(design_schema(load_pack("usine"))["properties"])
        redo = FACTORY_SECTIONS[regen["section"]] & produced
        keep, note = {k: v for k, v in origin.items() if k not in redo}, regen["note"]
        current = {k: origin[k] for k in redo}  # comme le worker (D14)
    else:
        keep, note, current = dict(entry.get("fixed") or {}), None, None
    tries = await design_with_retries(llm, entry, keep, note, current)
    design = tries[-1]
    spec = generate(GameParams(**design.params))
    review = {"autopilot": autopilot_check(spec), "unsourced": unsourced(spec)}
    start = engine.start(spec, engine.initial_state(spec))
    s1 = engine.public_state(spec, start)
    alea, forced = event_view(spec)
    reports: list = []
    pilot = play(spec, autopilot=True, trail=reports)
    pilot_debrief = engine.debrief(spec, pilot)
    passive = engine.debrief(spec, play(spec, held={r["id"] for r in spec["roles"]}))["criteria"]
    facts = [f for v in (s1, alea) for b in v["briefings"].values() for f in (*b["facts"], b["line"] or "")]
    facts += [a["text"] for v in (s1, alea) for a in v["alerts"]] + pilot_debrief["lessons"]
    art = {"lines": texts(spec, design.unmet), "facts": [f for f in facts if f], "state": pilot, "view": s1,
           "reports": reports, "debrief": pilot_debrief, "alea": alea, "autopilot": review["autopilot"],
           "passive": passive,
           "pilot_events": [h for h in pilot["history"] if h["event"]]}  # fmt: skip
    ctl = checks(entry, design, spec, art, keep, origin)
    files = {
        "entree.json": entry | ({"keep_envoye": keep, "note": note} if regen else {}),
        "design.json": asdict(design) | {"essais": [asdict(t) for t in tries]},
        "spec.json": spec,
        "briefings-s1.json": {k: s1[k] for k in ("week", "event", "briefings", "alerts")},
        "briefings-alea.json": {k: alea[k] for k in ("week", "event", "briefings", "alerts")} | {"forced": forced},
        "debrief-pilote.json": pilot_debrief,
        "criteres-passif.json": passive,
        "controles.json": ctl,
    }
    title = f"# {entry['id']} : {spec['meta']['title']}\n\n"
    write_all(out, files, title + md(spec, art, design.unmet, review["unsourced"]) + "\n")
    return {"id": entry["id"], "entry": entry, "params": design.params, "design": design, "tries": tries, "ctl": ctl,
            "spec": spec, "review": review}  # fmt: skip


def previous_failures(path: Path | None) -> dict[str, str]:
    """Échecs automatiques par jeu d'un resume.md antérieur (colonne « Échecs auto »)."""
    if not path or not path.exists():
        return {}
    rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in path.read_text("utf-8").splitlines()]
    return {r[0]: r[8] for r in rows if len(r) >= 12 and re.fullmatch(r"J\d+", r[0])}


def summary(results: list[dict], before: dict[str, str] | None = None) -> str:
    before = before or {}
    rows = [
        "| Id | Secteur | Niveau | Sem. | Modules | Repli | Essais | unmet | Échecs auto | OTIF pilote | ms | Tokens"
        " | Échecs avant (19/11) | Niveau / ton demandés | Niveau / ton obtenus |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    ms, tok = [], []
    for r in results:
        d, p = r["design"], r["params"]
        ms.append(sum(t.duration_ms for t in r["tries"]))
        tok.append(sum(t.prompt_tokens + t.completion_tokens for t in r["tries"]))
        rows.append(
            f"| {r['id']} | {p['theme']} | {p['difficulty']} | {p['weeks']} | {','.join(p['modules'])} |"
            f" {'oui' if d.fallback else 'non'} | {len(r['tries'])} | {' / '.join(d.unmet) or '-'} |"
            f" {', '.join(r['ctl']['echecs']) or '-'} | {r['review']['autopilot']['otif_mean']} |"
            f" {ms[-1]} | {tok[-1]} | {before.get(r['id'], '?')} |"
            f" {(r.get('entry', {}).get('fixed') or {}).get('difficulty', 'libre')} /"
            f" {(r.get('entry', {}).get('fixed') or {}).get('agent_tone', 'libre')} |"
            f" {p['difficulty']} / {p.get('agent_tone', '?')} |"
        )
    stats = (
        f"Latence (ms) : médiane {statistics.median(ms):.0f}, max {max(ms)} ;"
        f" tokens : médiane {statistics.median(tok):.0f}, max {max(tok)}"
    )
    return (
        f"# Audit des jeux IA - {date.today()}\n\nModèle : {results[0]['design'].model}\n\n"
        + "\n".join(rows)
        + f"\n\n{stats}\n"
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--compare", type=Path, default=None, help="resume.md d'un tour précédent")
    parser.add_argument(
        "--out", type=Path, default=get_settings().gmix_ai_dir / "evals" / "results" / f"audit-{date.today()}"
    )
    args = parser.parse_args()
    entries = [e for e in load_entries() if not args.only or e["id"] in args.only.split(",")]
    llm = LLMService.from_settings(with_cache=False)
    done: dict[str, dict] = {}
    try:
        await design_with_retries(llm, entries[0], {}, None)  # chauffe : le chargement n'entre pas dans les latences
        for e in entries:
            done[e["id"]] = await run_game(llm, e, done, args.out / e["id"])
            print(e["id"], "échecs :", done[e["id"]]["ctl"]["echecs"], "repli :", done[e["id"]]["design"].fallback)
    finally:
        await llm.aclose()
    (args.out / "resume.md").write_text(summary(list(done.values()), previous_failures(args.compare)), "utf-8")
    print("Résumé :", args.out / "resume.md")


if __name__ == "__main__":
    asyncio.run(main())
