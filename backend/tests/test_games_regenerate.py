"""POST /games/{id}/design/regenerate et fusion de `review` par `_store` (ADR 0012 §1). Base Docker requise ; la
publication Kafka est remplacée par un enregistreur (le worker a ses propres tests)."""

import uuid
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from gmix.db import get_sessionmaker
from gmix.db.models import BusinessGame, GameStatus, GenerationJob, JobStatus, Lobby, LobbyStatus
from tests.test_lobbies_round import PARAMS, World, _world

pytestmark = pytest.mark.integration
BRIEF = "Former des étudiants au goulot et à la maintenance préventive."


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []

    async def fake(_request: Any, topic: Any, event: Any, *, required: bool = False) -> bool:
        events.append((topic.name, event))
        return True

    monkeypatch.setattr("gmix.api.routes.games.publish", fake)
    return events


async def _designed(w: World, *, status: GameStatus = GameStatus.READY) -> str:
    """Jeu du formateur rangé comme le worker le fait : `attempts` dans la revue, brief du formateur."""
    game = (await w.client.post("/api/v1/games", json=PARAMS, headers=w.heads["trainer"])).json()
    async with get_sessionmaker()() as session:
        row = await session.get(BusinessGame, uuid.UUID(game["id"]))
        assert row is not None
        row.brief, row.status, row.review = BRIEF, status, {**row.review, "attempts": 1, "section": "x"}
        await session.commit()
    return game["id"]


def _url(game_id: str) -> str:
    return f"/api/v1/games/{game_id}/design/regenerate"


async def test_regenerate_accepted_and_draft(sent: list[tuple[str, Any]]) -> None:
    async with _world() as w:
        gid = await _designed(w)
        r = await w.client.post(_url(gid), json={"section": "personnages", "note": "Plus direct", "seed": 5},
                                headers=w.heads["trainer"])  # fmt: skip
        assert r.status_code == 202, r.text
        topics = {t: e for t, e in sent}
        event = topics["gmix.generation.commands"]
        assert event.type == "generation.requested"
        assert event.payload == {"job_id": r.json()["job_id"], "game_id": gid, "sections": ["personnages"],
                                 "seed": 5, "note": "Plus direct"}  # fmt: skip
        assert topics["gmix.audit"].payload["section"] == "personnages"
        game = (await w.client.get(f"/api/v1/games/{gid}", headers=w.heads["trainer"])).json()
        assert game["status"] == "generating"
        job = (await w.client.get(f"/api/v1/games/{gid}/job", headers=w.heads["trainer"])).json()
        assert job["kind"] == "regenerate_personnages" and job["status"] == "queued"
        # le worker repasse en draft ; la publication refait ensuite `ready` sans toucher brief ni review
        async with get_sessionmaker()() as session:
            row = await session.get(BusinessGame, uuid.UUID(gid))
            assert row is not None
            row.status = GameStatus.DRAFT
            await session.execute(GenerationJob.__table__.update().values(status=JobStatus.SUCCEEDED))
            await session.commit()
        pub = await w.client.post(f"/api/v1/games/{gid}/publish", headers=w.heads["trainer"])
        assert pub.json()["status"] == "ready"


async def test_regenerate_roles(sent: list[tuple[str, Any]]) -> None:
    async with _world() as w:
        gid = await _designed(w)
        body = {"section": "objectifs"}
        assert (await w.client.post(_url(gid), json=body, headers=w.heads["a"])).status_code == 403
        assert (await w.client.post(_url(gid), json=body, headers=w.heads["other"])).status_code == 404
        assert all(t != "gmix.generation.commands" for t, _ in sent)


async def test_regenerate_conflicts(sent: list[tuple[str, Any]]) -> None:
    async with _world() as w:
        trainer, body = w.heads["trainer"], {"section": "entreprise"}
        plain = (await w.client.post("/api/v1/games", json=PARAMS, headers=trainer)).json()["id"]
        refused = await w.client.post(_url(plain), json=body, headers=trainer)  # non conçu par l'IA
        assert refused.status_code == 409 and "pas été conçu par l'IA" in refused.json()["detail"]

        gid = await _designed(w)
        async with get_sessionmaker()() as session:  # lobby en cours
            lobby = Lobby(name="L", business_game_id=uuid.UUID(gid), trainer_id=w.users["trainer"].id,
                          status=LobbyStatus.RUNNING, join_code="ZZZZZZ")  # fmt: skip
            session.add(lobby)
            await session.commit()
        assert (await w.client.post(_url(gid), json=body, headers=trainer)).status_code == 409
        async with get_sessionmaker()() as session:
            await session.delete(await session.get(Lobby, lobby.id))
            await session.commit()

        assert (await w.client.post(_url(gid), json=body, headers=trainer)).status_code == 202
        again = await w.client.post(_url(gid), json=body, headers=trainer)  # job actif (et jeu generating)
        assert again.status_code == 409
        async with get_sessionmaker()() as session:  # job actif seul : le jeu n'est plus generating
            row = await session.get(BusinessGame, uuid.UUID(gid))
            assert row is not None
            row.status = GameStatus.DRAFT
            await session.commit()
            assert await session.scalar(select(GenerationJob.id).where(GenerationJob.status == JobStatus.QUEUED))
        assert (await w.client.post(_url(gid), json=body, headers=trainer)).status_code == 409


async def test_regenerate_503_restores_game(monkeypatch: pytest.MonkeyPatch) -> None:
    async def down(*_a: Any, **_k: Any) -> bool:
        raise HTTPException(503, "Kafka indisponible")

    async with _world() as w:
        gid = await _designed(w, status=GameStatus.DRAFT)
        monkeypatch.setattr("gmix.api.routes.games.publish", down)
        r = await w.client.post(_url(gid), json={"section": "entreprise"}, headers=w.heads["trainer"])
        assert r.status_code == 503
        game = (await w.client.get(f"/api/v1/games/{gid}", headers=w.heads["trainer"])).json()
        assert game["status"] == "draft"
        assert (await w.client.get(f"/api/v1/games/{gid}/job", headers=w.heads["trainer"])).status_code == 404


async def test_store_keeps_brief_and_review(sent: list[tuple[str, Any]]) -> None:
    async with _world() as w:
        gid = await _designed(w)
        trainer = w.heads["trainer"]
        pub = (await w.client.post(f"/api/v1/games/{gid}/publish", headers=trainer)).json()
        assert pub["brief"] == BRIEF and pub["review"]["attempts"] == 1 and "autopilot" in pub["review"]
        put = (await w.client.put(f"/api/v1/games/{gid}/params", json=PARAMS, headers=trainer)).json()
        assert put["status"] == "draft" and put["brief"] == BRIEF
        assert put["review"]["attempts"] == 1 and put["review"]["section"] == "x" and "dropped" in put["review"]
