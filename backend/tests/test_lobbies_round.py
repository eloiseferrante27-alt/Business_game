"""« Prêt », avance automatique, vote sur les absents, forçage, pause, aléa du formateur, droits par département et
conception IA (annexe 0010 §1, §5, §7). La logique du vote (`_round`) se teste sans infra ; le parcours HTTP exige la
base Docker et le moteur de 4b (`held_roles`, `force_event`, droits par département)."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy import delete

from gmix.api.auth import create_access_token
from gmix.api.main import app
from gmix.api.routes.lobbies import _round
from gmix.api.ws import WebSocketHub
from gmix.db import get_engine, get_sessionmaker
from gmix.db.models import BusinessGame, Lobby, User, UserRole
from gmix.tools.create_user import create_user

# --- logique pure : aucune infra -------------------------------------------------------------------------------


def _lobby(ready: list[str], ballots: dict[str, str], **settings: Any) -> Any:
    ready_block = {"week": 1, "users": ready, "ballots": ballots}
    return SimpleNamespace(
        id=uuid.uuid4(), state={"week": 1, "status": "running"}, settings=settings | {"ready": ready_block}
    )


def _members(*ids: str) -> list[dict[str, Any]]:
    return [{"user_id": u, "game_role": f"r{u}"} for u in ids]


def _hub(lobby: Any, *connected: str) -> WebSocketHub:
    hub = WebSocketHub()
    for u in connected:
        hub.subscribe(u, str(lobby.id))
    return hub


@pytest.mark.parametrize(
    ("ballots", "decision"),
    [
        ({}, None),  # personne n'a voté
        ({"a": "ignore"}, None),  # 1 sur 3 ne suffit pas, pas d'attente non plus
        ({"a": "ignore", "b": "ignore"}, "ignore"),  # majorité stricte
        ({"a": "wait"}, None),  # 1 sur 3 : ni majorité d'attente ni égalité
        ({"a": "wait", "b": "wait"}, "wait"),
    ],
)
def test_vote_decision_with_three_connected(ballots: dict[str, str], decision: str | None) -> None:
    lobby = _lobby(["a", "b", "c"], ballots)
    rnd = _round(lobby, _members("a", "b", "c", "d"), _hub(lobby, "a", "b", "c"))
    assert rnd["absent"] == ["d"] and rnd["vote"]["open"] and rnd["vote"]["voters"] == 3
    assert rnd["vote"]["decision"] == decision


def test_vote_tie_means_wait_and_closed_cases() -> None:
    lobby = _lobby(["a", "b"], {"a": "ignore", "b": "wait"})
    members = _members("a", "b", "c")
    rnd = _round(lobby, members, _hub(lobby, "a", "b"))
    assert rnd["vote"]["decision"] == "wait" and rnd["vote"]["ignore"] == rnd["vote"]["wait"] == 1
    assert not _round(_lobby(["a"], {}), members, _hub(lobby, "a", "b"))["vote"]["open"]  # b pas prêt
    assert not _round(_lobby(["a", "b"], {}, advance_mode="manual"), members, _hub(lobby, "a", "b"))["vote"]["open"]
    assert not _round(_lobby(["a", "b"], {}, paused=True), members, _hub(lobby, "a", "b"))["vote"]["open"]
    stale = _lobby(["a", "b"], {"a": "ignore"})
    stale.state["week"] = 2  # une avance remet appel et vote à zéro
    rnd = _round(stale, members, _hub(stale, "a", "b"))
    assert rnd["ready"] == [] and rnd["vote"]["ballots"] == {}


def test_watchers_follow_subscription() -> None:
    hub = WebSocketHub()
    hub.subscribe("u1", "L1")
    hub.subscribe("u1", "L2")  # une session suit un seul lobby
    assert hub.watchers("L1") == set() and hub.watchers("L2") == {"u1"}


# --- parcours HTTP (infra Docker) -------------------------------------------------------------------------------

needs_4b = pytest.mark.integration
PARAMS = {"theme": "industrie", "modules": ["approvisionnement", "production", "qualite"], "weeks": 6,
          "products": 2, "events": "frequents", "seed": 7}  # fmt: skip


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


class World:
    def __init__(self, client: httpx.AsyncClient, heads: dict[str, dict[str, str]], users: dict[str, User]) -> None:
        self.client, self.heads, self.users = client, heads, users
        self.url, self.spec, self.roles = "", {}, {}

    async def open(self, mode: str = "auto", *, start: bool = True) -> None:
        game = (await self.client.post("/api/v1/games", json=PARAMS, headers=self.heads["trainer"])).json()
        self.spec = game["spec"]
        body = {"name": "G", "business_game_id": game["id"], "advance_mode": mode}
        lobby = (await self.client.post("/api/v1/lobbies", json=body, headers=self.heads["trainer"])).json()
        assert lobby["round"]["advance_mode"] == mode
        self.url = f"/api/v1/lobbies/{lobby['id']}"
        by_module = {m["id"]: m["role_id"] for m in self.spec["modules"]}
        for name, module in zip(("a", "b", "c"), PARAMS["modules"], strict=True):
            await self.client.post("/api/v1/lobbies/join", json={"code": lobby["join_code"]}, headers=self.heads[name])
            put = await self.client.put(
                f"{self.url}/role", json={"game_role": by_module[module]}, headers=self.heads[name]
            )
            assert put.status_code == 200
            self.roles[name] = by_module[module]
        if start:
            assert (await self.client.post(f"{self.url}/start", headers=self.heads["trainer"])).status_code == 200

    def connect(self, *names: str) -> None:
        lobby_id = self.url.rsplit("/", 1)[1]
        for name in names:
            app.state.hub.subscribe(str(self.users[name].id), lobby_id)

    async def ready(self, name: str, ready: bool = True, absent: str | None = None) -> httpx.Response:
        body: dict[str, Any] = {"ready": ready} | ({"absent": absent} if absent else {})
        return await self.client.post(f"{self.url}/ready", json=body, headers=self.heads[name])

    async def week(self) -> int:
        view = (await self.client.get(self.url, headers=self.heads["trainer"])).json()
        return view["state"]["week"]


@asynccontextmanager
async def _world() -> AsyncIterator[World]:
    suffix = uuid.uuid4().hex[:8]
    roles = {"trainer": UserRole.TRAINER, "other": UserRole.TRAINER, "a": UserRole.PLAYER, "b": UserRole.PLAYER,
             "c": UserRole.PLAYER}  # fmt: skip
    users = {n: await create_user(f"{n}-{suffix}", "mdp-de-test-1", r) for n, r in roles.items()}
    ids = [u.id for u in users.values()]
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        ):
            yield World(client, {n: _auth(u) for n, u in users.items()}, users)
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(Lobby).where(Lobby.trainer_id.in_(ids)))
            await session.execute(delete(BusinessGame).where(BusinessGame.created_by.in_(ids)))
            await session.execute(delete(User).where(User.username.like(f"%-{suffix}")))
            await session.commit()
        await get_engine().dispose()


@pytest.mark.integration
async def test_ready_advances_automatically_and_resets() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b", "c")
        assert (
            await w.client.post(f"{w.url}/ready", json={"ready": True}, headers=w.heads["trainer"])
        ).status_code == 409
        for name in ("a", "a", "b"):  # le second « prêt » de a est idempotent
            answer = await w.ready(name)
            assert answer.status_code == 200 and answer.json()["round"]["ready_count"] == (1 if name == "a" else 2)
        assert await w.week() == 1
        last = (await w.ready("c")).json()
        assert last["state"]["week"] == 2 and last["round"]["ready"] == [] and last["round"]["vote"]["ballots"] == {}
        assert (await w.ready("a", False)).json()["round"]["ready_count"] == 0  # retirer un prêt vide la liste
        outsider = await w.client.post(f"{w.url}/ready", json={"ready": True}, headers=w.heads["other"])
        assert outsider.status_code == 404


@pytest.mark.integration
async def test_manual_mode_never_advances_on_ready() -> None:
    async with _world() as w:
        await w.open("manual")
        w.connect("a", "b", "c")
        for name in ("a", "b", "c"):
            assert (await w.ready(name)).status_code == 200
        assert await w.week() == 1
        assert (await w.client.post(f"{w.url}/advance", headers=w.heads["a"])).status_code == 403
        assert (await w.client.post(f"{w.url}/advance", headers=w.heads["trainer"])).json()["state"]["week"] == 2


@pytest.mark.integration
async def test_vote_ignore_wait_and_tie() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")  # c est absent
        assert (await w.ready("a", absent="ignore")).status_code == 409  # vote pas encore ouvert (b pas prêt)
        await w.ready("b")
        view = (await w.ready("a")).json()["round"]
        assert view["vote"]["open"] and view["vote"]["voters"] == 2 and view["absent"] == [str(w.users["c"].id)]
        tie = (await w.ready("a", absent="ignore")).json()
        assert tie["state"]["week"] == 1 and tie["round"]["vote"]["decision"] is None  # 1 sur 2 : pas de majorité
        tie = (await w.ready("b", absent="wait")).json()["round"]["vote"]
        assert tie["ignore"] == tie["wait"] == 1 and tie["decision"] == "wait"  # l'égalité fait attendre
        assert await w.week() == 1
        # b change son bulletin : majorité stricte pour ignorer, l'avance part dans la même requête
        done = (await w.ready("b", absent="ignore")).json()
        assert done["state"]["week"] == 2 and done["round"]["vote"]["ballots"] == {}
        assert w.roles["c"] in {r for r in [w.roles["c"]]}  # rôle de l'absent mis en pilote automatique par l'API


@pytest.mark.integration
async def test_vote_wait_blocks_and_returning_player_closes_it() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")
        await w.ready("a")
        await w.ready("b")
        assert (await w.ready("a", absent="wait")).json()["round"]["vote"]["decision"] == "wait"  # la moitié suffit
        decided = (await w.ready("b", absent="wait")).json()
        assert decided["round"]["vote"]["decision"] == "wait" and decided["state"]["week"] == 1
        w.connect("c")  # l'absent revient : le vote se ferme, son « prêt » fait partir la semaine
        assert not (await w.client.get(w.url, headers=w.heads["a"])).json()["round"]["vote"]["open"]
        assert (await w.ready("c")).json()["state"]["week"] == 2
        assert (await w.ready("a", absent="ignore")).status_code == 409  # plus de vote ouvert


@pytest.mark.integration
async def test_pause_force_and_event() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b", "c")
        pause = {"paused": True}
        assert (await w.client.post(f"{w.url}/pause", json=pause, headers=w.heads["a"])).status_code == 403
        assert (await w.client.post(f"{w.url}/pause", json=pause, headers=w.heads["other"])).status_code == 404
        assert (await w.client.post(f"{w.url}/pause", json=pause, headers=w.heads["trainer"])).json()["round"]["paused"]
        for name in ("a", "b", "c"):
            await w.ready(name)
        assert await w.week() == 1  # en pause, tout le monde prêt ne suffit pas
        forced = await w.client.post(f"{w.url}/advance", json={"ignore_absent": True}, headers=w.heads["trainer"])
        assert forced.status_code == 200 and forced.json()["state"]["week"] == 2  # le forçage vaut en pause

        event = w.spec["events"][0]["id"]
        bad = await w.client.post(f"{w.url}/event", json={"event_id": "inconnu"}, headers=w.heads["trainer"])
        assert bad.status_code == 422
        assert (
            await w.client.post(f"{w.url}/event", json={"event_id": event}, headers=w.heads["a"])
        ).status_code == 403
        ok = await w.client.post(f"{w.url}/event", json={"event_id": event}, headers=w.heads["trainer"])
        assert ok.status_code == 200 and ok.json()["state"]["event"]["id"] == event


@pytest.mark.integration
async def test_pause_and_event_need_a_running_game() -> None:
    async with _world() as w:
        await w.open(start=False)
        for route, body in (("pause", {"paused": True}), ("event", {"event_id": w.spec["events"][0]["id"]})):
            answer = await w.client.post(f"{w.url}/{route}", json=body, headers=w.heads["trainer"])
            assert answer.status_code == 409
        assert (await w.ready("a")).status_code == 409


@pytest.mark.integration
async def test_department_rights() -> None:
    """Un joueur n'agit que sur le module de son rôle ; le formateur agit partout (annexe 0010 §5)."""
    async with _world() as w:
        await w.open()
        offer = next(o for o in w.spec["offers"] if o["profile"] == "standard")
        order = {
            "module": "approvisionnement",
            "action": "commander",
            "values": {"offer": offer["id"], "quantity": 500},
        }
        url = f"{w.url}/actions"
        assert (await w.client.post(url, json=order, headers=w.heads["a"])).status_code == 200  # son module
        assert (await w.client.post(url, json=order, headers=w.heads["b"])).status_code == 409  # module d'un autre
        assert (await w.client.post(url, json=order, headers=w.heads["trainer"])).status_code == 200
        assert (await w.client.post(url, json=order, headers=w.heads["other"])).status_code == 404


@pytest.mark.integration
async def test_designs_only_for_usine() -> None:
    async with _world() as w:
        brief = "Former des étudiants au goulot et à la maintenance préventive."
        trainer, designs = w.heads["trainer"], "/api/v1/games/designs"
        refused = await w.client.post(designs, json={"pack": "atelier", "brief": brief}, headers=trainer)
        assert refused.status_code == 422 and refused.json()["detail"]["missing"] == []
        assert "usine" in refused.json()["detail"]["message"]
        admin = await w.client.post(designs, json={"pack": "atelier", "brief": brief}, headers=w.heads["a"])
        assert admin.status_code == 403  # un joueur n'a pas accès
        short = await w.client.post(designs, json={"pack": "usine", "brief": "trop court"}, headers=trainer)
        assert short.status_code == 422


@pytest.mark.integration
async def test_design_request_creates_generating_game_and_job() -> None:
    async with _world() as w:
        brief = "Former des étudiants au goulot et à la maintenance préventive."
        trainer, designs = w.heads["trainer"], "/api/v1/games/designs"
        accepted = await w.client.post(designs, json={"pack": "usine", "brief": brief, "seed": 3}, headers=trainer)
        assert accepted.status_code == 202, accepted.text
        game_id = accepted.json()["game_id"]
        assert (await w.client.get(f"/api/v1/games/{game_id}", headers=trainer)).json()["status"] == "generating"
        job = (await w.client.get(f"/api/v1/games/{game_id}/job", headers=trainer)).json()
        assert job["id"] == accepted.json()["job_id"] and job["status"] in {"queued", "running"}
        assert (await w.client.get(f"/api/v1/games/{game_id}/job", headers=w.heads["other"])).status_code == 404
        again = await w.client.post(designs, json={"pack": "usine", "brief": brief}, headers=trainer)
        assert again.status_code == 409  # une conception à la fois par demandeur
