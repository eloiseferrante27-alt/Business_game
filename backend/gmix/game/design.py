"""Conception d'un jeu à partir d'une demande (ADR 0008, annexe §3). Module pur, sans modèle ni entrée-sortie.

Fait pour l'instant : les variables du prompt `game.design.concept` liées au réseau. Le reste du contrat (schémas,
compilation, contrôles) viendra avec l'étape 5 de l'annexe, après le générateur d'usine."""

from __future__ import annotations

from typing import Any

from gmix.game.layout import site_label
from gmix.game.spec import DesignRequest, load_pack


def network_variable(pack: dict[str, Any]) -> str:
    """Une ligne par site : « id : libellé, classes permises (défaut X) » ; le modèle y choisit une classe."""
    sites = (pack.get("network") or {}).get("sites") or {}
    if not sites:
        return "aucun site à choisir"
    return "\n".join(
        f"- {name} : {site_label(name, s)}, classes permises {', '.join(s['distances'])} (défaut {s['default']})"
        for name, s in sites.items()
    )


def concept_variables(request: DesignRequest) -> dict[str, str]:
    # shortcut: seule la variable `network` est produite ici, les 16 autres du prompt arrivent avec l'étape 5
    return {"network": network_variable(load_pack(request.pack))}
