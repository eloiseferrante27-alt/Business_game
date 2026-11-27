"""Notation des consignes de l'outil eval_design_consignes (sans modèle) et cohérence de son jeu de cas."""

import json

from gmix.game.spec import load_pack
from gmix.llm.factory_design import FactoryDesign
from gmix.settings import get_settings
from gmix.tools.eval_design_consignes import POINTS, score

CASES = [
    json.loads(line)
    for line in (get_settings().gmix_ai_dir / "evals" / "design.consignes.jsonl").read_text("utf-8").splitlines()
    if line
]
PARAMS = {
    "difficulty": "decouverte", "agent_tone": "mixte", "events": "aucun", "event_plan": [], "weeks": 4,
    "modules": ["pilotage", "production"], "theme": "industrie", "options": {"lines": 2},
}  # fmt: skip


def test_cases_cover_the_ten_briefs() -> None:
    assert [c["id"] for c in CASES] == [f"J{i:02d}" for i in range(1, 11)]
    assert all(
        set(c["expect"]) <= {"niveau", "ton", "events_in", "plan", "weeks_min", "theme", "lines", "unmet"}
        for c in CASES
    )


def test_score_counts_each_point() -> None:
    pack = load_pack("usine")
    j01 = CASES[0]
    good = FactoryDesign(params=PARAMS, fallback=False)
    assert score(j01, good, j01["fixed"], pack) == dict.fromkeys(POINTS, True)
    bad = FactoryDesign(
        params=PARAMS | {"difficulty": "expert", "agent_tone": "exigeant"},
        fallback=False,
        unmet=["usine ough ough ough"],
    )
    s = score(j01, bad, j01["fixed"], pack)
    assert [k for k in POINTS if not s[k]] == ["niveau", "ton", "unmet"]
    late = {"week": 2, "event_id": next(iter(pack["events"]))}
    j08 = next(c for c in CASES if c["id"] == "J08")
    assert not score(
        j08,
        FactoryDesign(params=PARAMS | {"events": "rares", "weeks": 12, "event_plan": [late]}, fallback=False),
        {},
        pack,
    )["aleas"]  # aléa en semaine 2 : pas « en fin de partie »
