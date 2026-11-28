"""Rôles de jeu dans les routes de lobby (ADR 0013, annexe §3 ter, étape 4) : plan, choix, attribution au lancement
et droits sur les actions, de 1 à 6 joueurs. Base Docker requise ; le plan est posé dans la spec du lobby."""

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, update

from gmix.api.auth import create_access_token
from gmix.api.main import app
from gmix.db import get_engine, get_sessionmaker
from gmix.db.models import BusinessGame, Lobby, User, UserRole
from gmix.tools.create_user import create_user

pytestmark = pytest.mark.integration

PARAMS = {"theme": "industrie", "modules": ["approvisionnement", "production", "maintenance", "qualite", "commercial",
          "transport", "finance"], "weeks": 4, "products": 2, "events": "aucun", "seed": 7}  # fmt: skip
ACTIONS = ["planifier", "entretenir", "controler", "fixer_prix", "choisir_mode", "decouvert", "commander"]


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def _with_plans(spec: dict[str, Any]) -> tuple[dict[str, Any], dict[int, list[str]], dict[str, str]]:
    """Spec à plans de 1 à 5 joueurs : les 7 actions réparties en k rôles `p{k}_{i}` (action j -> rôle j % k)."""
    module_of = {a["id"]: m["id"] for m in spec["modules"] for a in m["actions"]}
    roles, plans = list(spec["roles"]), {}
    for k in range(1, 6):
        plans[k] = [f"p{k}_{i}" for i in range(k)]
        for i, role_id in enumerate(plans[k]):
            owned = ACTIONS[i::k]
            roles.append(
                {"id": role_id, "title": f"Rôle {role_id}", "module_id": module_of[owned[0]], "actions": owned}
            )
    meta = spec["meta"] | {"players": spec["meta"]["players"] | {"max": 6}}
    spec = spec | {"roles": roles, "meta": meta, "role_plans": [{"players": k, "roles": r} for k, r in plans.items()]}
    return spec, plans, module_of


def _values(spec: dict[str, Any], action_id: str) -> dict[str, Any]:
    action = next(a for m in spec["modules"] for a in m["actions"] if a["id"] == action_id)
    out: dict[str, Any] = {}
    for f in action["fields"]:
        source = {"offers": spec["offers"], "lines": spec["lines"], "products": spec["products"]}.get(f.get("source"))
        out[f["id"]] = f.get("default") or (f["min"] if f["type"] == "int" else (source or f["options"])[0]["id"])
    return out


async def test_role_matrix_from_1_to_6_players() -> None:
    suffix = uuid.uuid4().hex[:8]
    names = {"trainer": UserRole.TRAINER, "other": UserRole.TRAINER, "admin": UserRole.ADMIN} | {
        f"p{i}": UserRole.PLAYER for i in range(1, 7)
    }
    users = {n: await create_user(f"{n}-{suffix}", "mdp-de-test-1", r) for n, r in names.items()}
    heads = {n: _auth(u) for n, u in users.items()}
    ids = [u.id for u in users.values()]
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
            spec, plans, module_of = _with_plans(game["spec"])
            for n in range(1, 7):
                plan = plans[min(n, 5)]
                made = await client.post(
                    "/api/v1/lobbies", json={"name": f"G{n}", "business_game_id": game["id"]}, headers=heads["trainer"]
                )
                lobby = made.json()
                url = f"/api/v1/lobbies/{lobby['id']}"
                async with get_sessionmaker()() as session:
                    await session.execute(update(Lobby).where(Lobby.id == uuid.UUID(lobby["id"])).values(spec=spec))
                    await session.commit()

                async def join(name: str, code: str = lobby["join_code"]) -> dict[str, Any]:
                    res = await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads[name])
                    assert res.status_code == 200, res.text
                    return res.json()

                def put(name: str, role: str, url: str = url) -> Any:
                    return client.put(f"{url}/role", json={"game_role": role}, headers=heads[name])

                view = await join("p1")
                assert (await put("p1", plans[1][0])).status_code == 200  # plan à 1 joueur : seul p1 est là
                for i in range(2, n + 1):
                    view = await join(f"p{i}")
                if n > 1:  # n a changé : le choix de p1 est effacé
                    assert view["members"][0]["game_role"] is None
                assert view["seats"]["players"] == n and view["seats"]["roles"] == plan

                outside = "p1_0" if n > 1 else "p2_0"
                bad = await put("p1", outside)
                assert bad.status_code == 422 and bad.json()["detail"] == f"Ce rôle n'est pas proposé à {n} joueurs"
                assert (await put("p1", plan[0])).status_code == 200
                if n > 1:
                    taken = await put("p2", plan[0])
                    assert taken.status_code == 409, taken.text  # un rôle libre d'abord
                    assert (await put("p2", plan[1])).status_code == 200
                    assert (await put("p2", plan[1])).status_code == 200  # idempotent
                lobby_view = (await client.get(url, headers=heads["p1"])).json()
                assert lobby_view["my_role"] == plan[0] and set(lobby_view["seats"]["owners"].values()) == set(plan)

                started = await client.post(f"{url}/start", headers=heads["trainer"])
                assert started.status_code == 200, started.text
                expected = {f"p{i + 1}": plan[i] if i < len(plan) else plan[0] for i in range(n)}  # 6e : double
                for i in range(1, n + 1):
                    mine = (await client.get(url, headers=heads[f"p{i}"])).json()["my_role"]
                    assert mine == expected[f"p{i}"], (n, i)

                for i in range(1, n + 1):
                    role = expected[f"p{i}"]
                    mine = ACTIONS[plan.index(role) :: len(plan)]
                    own = next(a for a in mine if a != "commander")
                    other = next((a for a in ACTIONS if a != "commander" and a not in mine), None)
                    body = {"module": module_of[own], "action": own, "values": _values(spec, own)}
                    done = await client.post(f"{url}/actions", json=body, headers=heads[f"p{i}"])
                    assert done.status_code == 200, (n, i, done.text)
                    if other:
                        body = {"module": module_of[other], "action": other, "values": _values(spec, other)}
                        refused = await client.post(f"{url}/actions", json=body, headers=heads[f"p{i}"])
                        assert refused.status_code == 409 and "revient au rôle" in refused.json()["detail"], (n, i)
                for who in ("trainer", "admin"):
                    body = {
                        "module": module_of["fixer_prix"],
                        "action": "fixer_prix",
                        "values": _values(spec, "fixer_prix"),
                    }
                    assert (await client.post(f"{url}/actions", json=body, headers=heads[who])).status_code == 200
                assert (await client.get(url, headers=heads["other"])).status_code == 404
                assert (
                    await client.put(f"{url}/role", json={"game_role": plan[0]}, headers=heads["p1"])
                ).status_code == 409
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()


async def test_default_workshop_keeps_role_choices_when_a_player_joins() -> None:
    """Partie atelier par défaut (spec sans `role_plans`) : le plan est stable, un nouvel entrant n'efface rien."""
    suffix = uuid.uuid4().hex[:8]
    names = {"trainer": UserRole.TRAINER, "p1": UserRole.PLAYER, "p2": UserRole.PLAYER}
    users = {n: await create_user(f"{n}-{suffix}", "mdp-de-test-1", r) for n, r in names.items()}
    heads = {n: _auth(u) for n, u in users.items()}
    ids = [u.id for u in users.values()]
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
            assert not game["spec"].get("role_plans")
            made = await client.post(
                "/api/v1/lobbies", json={"name": "Atelier", "business_game_id": game["id"]}, headers=heads["trainer"]
            )
            code = made.json()["join_code"]
            await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads["p1"])
            role = game["spec"]["roles"][0]["id"]
            url = f"/api/v1/lobbies/{made.json()['id']}"
            assert (await client.put(f"{url}/role", json={"game_role": role}, headers=heads["p1"])).status_code == 200
            await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads["p2"])
            assert (await client.get(url, headers=heads["p1"])).json()["my_role"] == role
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()


async def test_join_that_changes_the_role_plan_clears_choices() -> None:
    """Spec à `role_plans` : passer de 2 à 3 joueurs change le plan, les choix déjà faits sont effacés."""
    suffix = uuid.uuid4().hex[:8]
    names = {"trainer": UserRole.TRAINER, "p1": UserRole.PLAYER, "p2": UserRole.PLAYER, "p3": UserRole.PLAYER}
    users = {n: await create_user(f"{n}-{suffix}", "mdp-de-test-1", r) for n, r in names.items()}
    heads = {n: _auth(u) for n, u in users.items()}
    ids = [u.id for u in users.values()]
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
            spec, plans, _ = _with_plans(game["spec"])
            made = await client.post(
                "/api/v1/lobbies", json={"name": "Plans", "business_game_id": game["id"]}, headers=heads["trainer"]
            )
            code, url = made.json()["join_code"], f"/api/v1/lobbies/{made.json()['id']}"
            async with get_sessionmaker()() as session:
                await session.execute(update(Lobby).where(Lobby.id == uuid.UUID(made.json()["id"])).values(spec=spec))
                await session.commit()
            for name in ("p1", "p2"):
                await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads[name])
            put = await client.put(f"{url}/role", json={"game_role": plans[2][0]}, headers=heads["p1"])
            assert put.status_code == 200, put.text
            await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads["p3"])
            assert (await client.get(url, headers=heads["p1"])).json()["my_role"] is None
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()


class _FakeProducer:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def publish(self, topic: Any, event: Any, key: str | None = None) -> None:
        self.events.append(event)


async def test_leave_lobby_before_start() -> None:
    """POST /leave : retire l'appelant, refus 409 (pas membre, partie lancée), 404 pour un autre formateur ;
    plan stable (atelier par défaut) : les rôles des autres sont gardés ; le formateur membre part sans effet."""
    suffix = uuid.uuid4().hex[:8]
    names = {"trainer": UserRole.TRAINER, "other": UserRole.TRAINER, "p1": UserRole.PLAYER, "p2": UserRole.PLAYER}
    users = {n: await create_user(f"{n}-{suffix}", "mdp-de-test-1", r) for n, r in names.items()}
    heads = {n: _auth(u) for n, u in users.items()}
    ids = [u.id for u in users.values()]
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
            made = await client.post(
                "/api/v1/lobbies", json={"name": "Départ", "business_game_id": game["id"]}, headers=heads["trainer"]
            )
            code, url = made.json()["join_code"], f"/api/v1/lobbies/{made.json()['id']}"
            for name in ("trainer", "p1", "p2"):
                await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads[name])
            role = game["spec"]["roles"][0]["id"]
            await client.put(f"{url}/role", json={"game_role": role}, headers=heads["p1"])
            assert (await client.get(url, headers=heads["p1"])).json()["seats"]["players"] == 2

            assert (await client.post(f"{url}/leave", headers=heads["other"])).status_code == 404
            left = await client.post(f"{url}/leave", headers=heads["p2"])
            assert left.status_code == 204 and left.content == b""
            view = (await client.get(url, headers=heads["p1"])).json()
            assert view["seats"]["players"] == 1 and view["my_role"] == role
            again = await client.post(f"{url}/leave", headers=heads["p2"])
            assert again.status_code == 404  # ni membre ni gestionnaire
            assert (await client.post(f"{url}/leave", headers=heads["trainer"])).status_code == 204
            again = await client.post(f"{url}/leave", headers=heads["trainer"])
            assert (again.status_code, again.json()["detail"]) == (409, "Vous n'êtes pas dans ce lobby")
            assert (await client.get(url, headers=heads["p1"])).json()["my_role"] == role

            assert (await client.post(f"{url}/start", headers=heads["trainer"])).status_code == 200
            late = await client.post(f"{url}/leave", headers=heads["p1"])
            assert (late.status_code, late.json()["detail"]) == (
                409,
                "La partie est lancée : vous ne pouvez plus quitter le lobby",
            )
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()


async def test_leave_that_changes_the_role_plan_clears_choices_and_publishes() -> None:
    """Spec à `role_plans` : 3 -> 2 joueurs change le plan, les rôles sont effacés ; `lobby.members` est publié
    avec seats = 2 et le partant n'est plus abonné au hub."""
    suffix = uuid.uuid4().hex[:8]
    names = {"trainer": UserRole.TRAINER, "p1": UserRole.PLAYER, "p2": UserRole.PLAYER, "p3": UserRole.PLAYER}
    users = {n: await create_user(f"{n}-{suffix}", "mdp-de-test-1", r) for n, r in names.items()}
    heads = {n: _auth(u) for n, u in users.items()}
    ids = [u.id for u in users.values()]
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            game = (await client.post("/api/v1/games", json=PARAMS, headers=heads["trainer"])).json()
            spec, plans, _ = _with_plans(game["spec"])
            made = await client.post(
                "/api/v1/lobbies", json={"name": "Plans", "business_game_id": game["id"]}, headers=heads["trainer"]
            )
            lobby_id, code = made.json()["id"], made.json()["join_code"]
            url = f"/api/v1/lobbies/{lobby_id}"
            async with get_sessionmaker()() as session:
                await session.execute(update(Lobby).where(Lobby.id == uuid.UUID(lobby_id)).values(spec=spec))
                await session.commit()
            for name in ("p1", "p2", "p3"):
                await client.post("/api/v1/lobbies/join", json={"code": code}, headers=heads[name])
            put = await client.put(f"{url}/role", json={"game_role": plans[3][0]}, headers=heads["p1"])
            assert put.status_code == 200, put.text
            producer, hub = _FakeProducer(), app.state.hub
            app.state.producer = producer
            hub.subscribe(str(users["p3"].id), lobby_id)
            assert (await client.post(f"{url}/leave", headers=heads["p3"])).status_code == 204
            assert (await client.get(url, headers=heads["p1"])).json()["my_role"] is None
            assert str(users["p3"].id) not in hub.watchers(lobby_id)
            event = next(e for e in producer.events if e.type == "lobby.members")
            assert event.payload["seats"]["players"] == 2 and len(event.payload["members"]) == 2
            app.state.producer = None
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()
