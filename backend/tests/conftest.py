import copy
from typing import Any

import pytest

from gmix.db import get_engine
from gmix.game.generation import generate
from gmix.game.spec import GameParams
from gmix.settings import get_settings

AI_DIR = get_settings().gmix_ai_dir
ALL_MODULES = ["approvisionnement", "production", "maintenance", "qualite", "commercial", "transport", "finance"]


@pytest.fixture(scope="session")
def _reference_spec() -> dict[str, Any]:
    params = GameParams(
        theme="industrie", modules=ALL_MODULES, extra_agents=["client", "fournisseur", "direction"],
        products=4, weeks=6, seed=42, events="aucun",
    )  # fmt: skip
    return generate(params)


@pytest.fixture(autouse=True)
async def _release_db_pool():
    """Chaque test a sa boucle d'événements : le pool du moteur mis en cache ne doit pas survivre à la sienne."""
    yield
    if get_engine.cache_info().currsize:
        await get_engine().dispose()


@pytest.fixture
def sim_spec(_reference_spec: dict[str, Any]) -> dict[str, Any]:
    """Business game complet (tous les modules et agents, 4 produits, sans aléa) ; copie modifiable par test."""
    return copy.deepcopy(_reference_spec)
