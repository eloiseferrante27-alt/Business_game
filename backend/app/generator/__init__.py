"""Générateur de mondes : pack de domaine (données) + constructeur (code) -> scénario jouable.

Le noyau ne connaît aucun domaine. Chaque domaine est un paquet `domains/<domaine>/` qui fournit
`pack.json` et deux fonctions : `build(pack, rng, params) -> monde` et `validate(monde) -> [problèmes]`.
Le monde produit a le format de `scenarios/*.json`, que le moteur charge déjà (voir docs/generateur.md).
"""

import json
import random
import re
from importlib import import_module
from pathlib import Path
from typing import Any

from .. import scenario as scenario_store

DOMAINS_DIR = Path(__file__).parent / "domains"
ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,40}$")  # même motif que NewGameRequest.scenario_id


class WorldError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("Monde invalide :\n- " + "\n- ".join(issues))
        self.issues = issues


def list_domains() -> list[str]:
    return sorted(p.name for p in DOMAINS_DIR.iterdir() if (p / "pack.json").exists())


def _domain(domain: str):
    if domain not in list_domains():
        raise ValueError(f"Domaine inconnu : {domain} (disponibles : {', '.join(list_domains())})")
    module = import_module(f".domains.{domain}", __package__)
    pack = json.loads((DOMAINS_DIR / domain / "pack.json").read_text(encoding="utf-8"))
    return module, pack


def generate(domain: str = "supply_chain", seed: int = 0, scenario_id: str | None = None, **params: Any) -> dict:
    """Même domaine + même graine + mêmes paramètres => même monde, octet pour octet."""
    module, pack = _domain(domain)
    world = module.build(pack, random.Random(seed), params)
    world["id"] = scenario_id or f"{domain.replace('_', '-')}-{seed}"
    if not ID_PATTERN.match(world["id"]):
        raise ValueError(f"Identifiant de scénario invalide : {world['id']}")
    world["name"] = f"{world.get('name', domain)} (graine {seed})"
    world["generation"] = {"domain": domain, "seed": seed, "params": params, "pack_version": pack.get("version", 1)}
    issues = module.validate(world)
    if issues:
        raise WorldError(issues)
    return world


def validate(world: dict) -> list[str]:
    """Valide un monde existant (écrit à la main ou généré) avec les règles de son domaine."""
    module, _ = _domain(world.get("generation", {}).get("domain", "supply_chain"))
    return module.validate(world)


def save(world: dict) -> Path:
    path = scenario_store.SCENARIO_DIR / f"{world['id']}.json"
    path.write_text(json.dumps(world, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    scenario_store.load_scenario.cache_clear()
    return path


def place_zones(zones: list[dict], rows: list[list[str]], aisle: float) -> dict[str, dict]:
    """Disposition générique : les zones de chaque rangée côte à côte, rangées empilées, allées entre elles.

    Renvoie {id: {x, z, w, d, ...}} centré sur l'origine (x = gauche-droite, z = haut-bas), comme layout.js.
    """
    by_id = {zone["id"]: zone for zone in zones}
    placed, depths = {}, [max(by_id[i]["d"] for i in row) for row in rows]
    z = -(sum(depths) + aisle * (len(rows) - 1)) / 2
    for row, depth in zip(rows, depths):
        x = -(sum(by_id[i]["w"] for i in row) + aisle * (len(row) - 1)) / 2
        for zone_id in row:
            zone = by_id[zone_id]
            placed[zone_id] = {**zone, "x": round(x + zone["w"] / 2, 2), "z": round(z + depth / 2, 2)}
            del placed[zone_id]["id"]
            x += zone["w"] + aisle
        z += depth + aisle
    return placed
