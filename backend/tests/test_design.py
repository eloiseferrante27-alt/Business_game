"""Variables du prompt de conception (gmix.game.design) : partie réseau."""

from gmix.game.design import concept_variables, network_variable
from gmix.game.spec import DesignRequest, load_pack


def test_one_line_per_site_with_its_allowed_classes_and_default() -> None:
    lines = network_variable(load_pack("usine")).splitlines()
    assert len(lines) == 4
    assert (
        "fournisseur_economique : Fournisseur economique, classes permises national, import (défaut national)"
        in lines[2]
    )
    assert "client : Client, classes permises proche (défaut proche)" in lines[3]


def test_a_pack_without_network_has_no_site_to_choose() -> None:
    assert network_variable({}) == "aucun site à choisir"
    request = DesignRequest(pack="atelier", brief="Former des BTS à la gestion de stock.")
    assert concept_variables(request) == {"network": "aucun site à choisir"}
