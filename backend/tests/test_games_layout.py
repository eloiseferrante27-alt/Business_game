"""Garde-fous d'édition d'un business game (ADR 0009) : pack non couvert, 422 du pack usine, retouches de plan,
paramètres, publication. Nécessite la base Docker ; les règles du moteur de plan sont testées dans test_layout."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, update

from gmix.api.auth import create_access_token
from gmix.api.main import app
from gmix.api.routes import games
from gmix.db import get_engine, get_sessionmaker
from gmix.db.models import BusinessGame, GameStatus, Lobby, LobbyStatus, User, UserRole
from gmix.tools.create_user import create_user

pytestmark = pytest.mark.integration
PARAMS = {"theme": "industrie", "modules": ["production"], "products": 2, "weeks": 4, "events": "aucun", "seed": 3}
EDIT = {"layout_edits": [{"op": "remove", "object_id": "x.1"}]}


@asynccontextmanager
async def _users() -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, dict[str, str]], list[uuid.UUID]]]:
    """Clients HTTP et en-têtes de trois comptes jetables (formateur, autre formateur, admin), supprimés à la sortie
    avec leurs jeux et lobbies."""
    suffix = uuid.uuid4().hex[:8]
    roles = {"trainer": UserRole.TRAINER, "other": UserRole.TRAINER, "admin": UserRole.ADMIN}
    heads, ids = {}, []
    for name, role in roles.items():
        user = await create_user(f"{name}-{suffix}", "mdp-de-test-1", role)
        heads[name] = {"Authorization": f"Bearer {create_access_token(user)}"}
        ids.append(user.id)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            yield client, heads, ids
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()


async def _set_game(game_id: str, **values: Any) -> None:
    async with get_sessionmaker()() as session:
        await session.execute(update(BusinessGame).where(BusinessGame.id == uuid.UUID(game_id)).values(**values))
        await session.commit()


async def test_options_expose_coverage_and_usine_is_422() -> None:
    async with _users() as (client, heads, _):
        options = (await client.get("/api/v1/games/options", headers=heads["trainer"])).json()
        for pack in options["packs"]:
            assert 0 <= pack["coverage"]["ratio"] <= 1 and pack["available"] == (not pack["coverage"]["missing"])
        # tant que le générateur d'usine manque : 422 lisible (et non 500)
        usine = PARAMS | {"pack": "usine", "modules": ["pilotage"], "products": 1}
        answer = await client.post("/api/v1/games", json=usine, headers=heads["trainer"])
        assert answer.status_code in (201, 422), answer.text[:200]


async def test_uncovered_pack_trainer_422_admin_forces(monkeypatch: pytest.MonkeyPatch) -> None:
    cover = {"ratio": 0.5, "required": ["a"], "missing": ["a"]}
    monkeypatch.setattr(games, "pack_coverage", lambda pack_id, catalog=None: cover)
    sent: list[str] = []

    async def fake_publish(request: Any, topic: str, envelope: Any) -> None:
        sent.append(envelope.type)

    monkeypatch.setattr(games, "publish", fake_publish)
    async with _users() as (client, heads, _):
        options = (await client.get("/api/v1/games/options", headers=heads["trainer"])).json()
        assert not any(p["available"] for p in options["packs"])
        for who, query in (("trainer", ""), ("trainer", "?force=true"), ("admin", "")):
            answer = await client.post(f"/api/v1/games{query}", json=PARAMS, headers=heads[who])
            assert answer.status_code == 422 and answer.json()["detail"]["missing"] == ["a"]
        forced = await client.post("/api/v1/games?force=true", json=PARAMS, headers=heads["admin"])
        assert forced.status_code == 201 and "game.forced" in sent


async def test_layout_params_publish_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = (("put", "/layout", EDIT), ("put", "/params", PARAMS), ("post", "/publish", None))
    async with _users() as (client, heads, ids):
        game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
        url = f"/api/v1/games/{game['id']}"
        for verb, path, body in calls:  # un jeu d'autrui répond 404
            answer = await getattr(client, verb)(url + path, headers=heads["other"], **({"json": body} if body else {}))
            assert answer.status_code == 404
        assert (await client.put(f"{url}/layout", json=EDIT, headers=heads["trainer"])).status_code == 422  # sans plan
        too_many = {"layout_edits": EDIT["layout_edits"] * 201}
        assert (await client.put(f"{url}/layout", json=too_many, headers=heads["trainer"])).status_code == 422

        # params : nouvelle génération, même graine, retour en draft ; l'admin gère le jeu d'autrui
        saved = await client.put(f"{url}/params", json=PARAMS | {"weeks": 5}, headers=heads["trainer"])
        assert saved.status_code == 200 and saved.json()["status"] == "draft"
        assert saved.json()["spec"]["meta"]["weeks"] == 5 and saved.json()["spec"]["seed"] == 3
        published = await client.post(f"{url}/publish", headers=heads["admin"])
        assert published.status_code == 200 and published.json()["status"] == "ready"

        async with get_sessionmaker()() as session:  # 409 : un lobby du jeu est en cours
            session.add(Lobby(name="t", join_code=uuid.uuid4().hex[:8], business_game_id=uuid.UUID(game["id"]),
                              trainer_id=ids[0], status=LobbyStatus.RUNNING))  # fmt: skip
            await session.commit()
        for verb, path, body in calls:
            answer = await getattr(client, verb)(
                url + path, headers=heads["trainer"], **({"json": body} if body else {})
            )
            assert answer.status_code == 409
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.commit()

        await _set_game(game["id"], status=GameStatus.GENERATING)  # 409 : génération en cours
        assert (await client.put(f"{url}/params", json=PARAMS, headers=heads["trainer"])).status_code == 409

        await _set_game(game["id"], status=GameStatus.DRAFT)  # publication refusée si un contrôle échoue
        monkeypatch.setattr(games, "check_placement", lambda spec, pack: ["règle r1 violée"])
        monkeypatch.setattr(games, "_validated", lambda spec: spec | {"departments": [{"id": "d"}]})
        refused = await client.post(f"{url}/publish", headers=heads["trainer"])
        assert refused.status_code == 409 and refused.json()["detail"]["errors"] == ["règle r1 violée"]


async def test_layout_saved_as_draft_and_rejections_422(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le moteur de plan est simulé : on teste la couche HTTP (refus -> 422 avec rang, succès -> draft)."""
    async with _users() as (client, heads, _):
        game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
        url = f"/api/v1/games/{game['id']}/layout"
        await _set_game(game["id"], spec=game["spec"] | {"departments": [{"id": "d"}]})  # passe la garde « plan »
        rejected = [{"index": 0, "reason": "allee", "message": "La retouche empiète sur une allée."}]
        monkeypatch.setattr(games, "_with_edits", lambda spec, edits: (spec, rejected))
        answer = await client.put(url, json=EDIT, headers=heads["trainer"])
        assert answer.status_code == 422
        assert answer.json()["detail"]["errors"] == ["retouche 1 : La retouche empiète sur une allée."]
        monkeypatch.setattr(games, "_with_edits", lambda spec, edits: (spec | {"layout_edits": edits}, []))
        monkeypatch.setattr(games, "_validated", lambda spec: spec)
        monkeypatch.setattr(games, "check_placement", lambda spec, pack: ["règle r2 violée"])
        answer = await client.put(url, json=EDIT, headers=heads["trainer"])
        assert answer.status_code == 422 and answer.json()["detail"]["errors"] == ["règle r2 violée"]
        monkeypatch.setattr(games, "check_placement", lambda spec, pack: [])
        answer = await client.put(url, json=EDIT, headers=heads["trainer"])
        assert answer.status_code == 200 and answer.json()["status"] == "draft"


async def test_usine_layout_recomputes_routes_and_rejects_bad_edit() -> None:
    """Pack usine réel : une retouche acceptée recalcule plan et trajets, une retouche inconnue donne un 422."""
    usine = PARAMS | {"pack": "usine", "modules": ["pilotage"], "products": 1}
    async with _users() as (client, heads, _):
        created = await client.post("/api/v1/games", json=usine, headers=heads["trainer"])
        assert created.status_code == 201, created.text[:300]
        game = created.json()
        url = f"/api/v1/games/{game['id']}"
        bad = {"layout_edits": [{"op": "remove", "object_id": "inconnu.99"}]}
        answer = await client.put(f"{url}/layout", json=bad, headers=heads["trainer"])
        assert answer.status_code == 422 and len(answer.json()["detail"]["errors"]) == 1
        before = game["spec"]
        dept = before["departments"][0]
        cells = [(x, y) for y in range(8, 17, 4) for x in range(0, 30, 6)]
        for cell in cells:  # première case libre où le pack accepte une plante
            add = {"op": "add", "department_id": dept["id"], "asset": "furn_plant", "cell": cell}
            answer = await client.put(f"{url}/layout", json={"layout_edits": [add]}, headers=heads["trainer"])
            if answer.status_code == 200:
                break
        assert answer.status_code == 200, answer.text[:300]
        body = answer.json()
        assert body["status"] == "draft" and len(body["spec"]["layout_edits"]) == 1
        assert any(o["id"].endswith(".ajout.0") for o in body["spec"]["world"]["objects"])
        assert all(a["route"] for a in body["spec"]["agents"])
        # le plan retouché = le plan d'origine + l'objet ajouté (rien d'autre ne bouge)
        old_ids = {o["id"] for o in before["world"]["objects"]}
        new_ids = {o["id"] for o in body["spec"]["world"]["objects"]}
        assert new_ids - old_ids == {o for o in new_ids if o.endswith(".ajout.0")} and old_ids <= new_ids
        assert [a["id"] for a in body["spec"]["agents"]] == [a["id"] for a in before["agents"]]
        # le rejeu des mêmes retouches donne le même plan (idempotence de PUT /layout)
        replay = {"layout_edits": body["spec"]["layout_edits"]}
        again = await client.put(f"{url}/layout", json=replay, headers=heads["trainer"])
        assert again.status_code == 200 and again.json()["spec"]["world"] == body["spec"]["world"]
        assert again.json()["spec"]["agents"] == body["spec"]["agents"]
