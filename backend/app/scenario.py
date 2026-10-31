"""Chargement des scénarios : chaque fichier scenarios/<id>.json règle les valeurs du monde."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SCENARIO_DIR = Path(__file__).parent / "scenarios"


@lru_cache(maxsize=8)
def load_scenario(scenario_id: str = "default") -> dict[str, Any]:
    path = (SCENARIO_DIR / f"{scenario_id}.json").resolve()
    if path.parent != SCENARIO_DIR.resolve() or not path.exists():
        raise ValueError(f"Scénario inconnu : {scenario_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_scenarios() -> list[dict[str, str]]:
    result = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        result.append({"id": path.stem, "name": data.get("name", path.stem), "description": data.get("description", "")})
    return result
