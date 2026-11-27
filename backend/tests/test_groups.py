"""Groupes de travail : N équipes, une entreprise chacune, avance indépendante, une équipe par joueur, débrief
comparé (ADR 0011 §2). Parcours HTTP : exige la base Docker (scripts\\infra.ps1 up)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import delete

from gmix.db import get_sessionmaker
from gmix.db.models import LobbyGroup
from tests.test_lobbies_round import PARAMS, World, _world


@asynccontextmanager
async def _group_world() -> AsyncIterator[tuple[World, dict]]:
    async with _world() as w:
        try:
            game = (await w.client.post("/api/v1/games", json=PARAMS, headers=w.heads["trainer"])).json()
            body = {"name": "Licence pro", "business_game_id": game["id"], "teams": 2}
            created = await w.client.post("/api/v1/groups", json=body, headers=w.heads["trainer"])
            assert created.status_code == 201, created.text
            yield w, created.json() | {"spec": game["spec"]}
        finally:  # les groupes référencent le formateur : à supprimer avant les comptes (_world)
            async with get_sessionmaker()() as session:
                await session.execute(delete(LobbyGroup).where(LobbyGroup.trainer_id == w.users["trainer"].id))
                await session.commit()


@pytest.mark.integration
async def test_group_creates_teams_and_players_pick_one() -> None:
    async with _group_world() as (w, group):
        assert [t["name"] for t in group["teams"]] == ["Équipe 1", "Équipe 2"] and group["join_code"]
        t1, t2 = (t["lobby_id"] for t in group["teams"])
        listing = await w.client.post("/api/v1/groups/join", json={"code": group["join_code"]}, headers=w.heads["a"])
        assert listing.json()["join_code"] is None and len(listing.json()["teams"]) == 2  # le code reste au formateur
        joined = await w.client.post(
            "/api/v1/groups/join", json={"code": group["join_code"], "lobby_id": t1}, headers=w.heads["a"]
        )
        assert joined.status_code == 200 and joined.json()["group_id"] == group["id"]
        again = await w.client.post(
            "/api/v1/groups/join", json={"code": group["join_code"], "lobby_id": t1}, headers=w.heads["a"]
        )
        assert again.status_code == 200  # idempotent
        other = await w.client.post(
            "/api/v1/groups/join", json={"code": group["join_code"], "lobby_id": t2}, headers=w.heads["a"]
        )
        assert other.status_code == 409  # une équipe par groupe
        team2 = (await w.client.get(f"/api/v1/lobbies/{t2}", headers=w.heads["trainer"])).json()
        by_code = await w.client.post("/api/v1/lobbies/join", json={"code": team2["join_code"]}, headers=w.heads["a"])
        assert by_code.status_code == 409  # même règle par le code de l'équipe
        view = (await w.client.get(f"/api/v1/groups/{group['id']}", headers=w.heads["a"])).json()
        assert view["my_team"] == t1 and view["join_code"] is None
        assert (await w.client.get(f"/api/v1/groups/{group['id']}", headers=w.heads["b"])).status_code == 404
        assert (await w.client.get(f"/api/v1/groups/{group['id']}", headers=w.heads["other"])).status_code == 404
        mine = (await w.client.get("/api/v1/groups", headers=w.heads["a"])).json()
        assert [g["id"] for g in mine] == [group["id"]]


@pytest.mark.integration
async def test_teams_advance_independently_and_debrief_compares() -> None:
    async with _group_world() as (w, group):
        t1, t2 = (t["lobby_id"] for t in group["teams"])
        role = next(r["id"] for r in group["spec"]["roles"])
        for name, team in (("a", t1), ("b", t2)):
            await w.client.post(
                "/api/v1/groups/join", json={"code": group["join_code"], "lobby_id": team}, headers=w.heads[name]
            )
            put = await w.client.put(f"/api/v1/lobbies/{team}/role", json={"game_role": role}, headers=w.heads[name])
            assert put.status_code == 200  # le même rôle dans deux entreprises différentes
        for team in (t1, t2):
            assert (await w.client.post(f"/api/v1/lobbies/{team}/start", headers=w.heads["trainer"])).status_code == 200
        advanced = await w.client.post(f"/api/v1/lobbies/{t1}/advance", headers=w.heads["trainer"])
        assert advanced.json()["state"]["week"] == 2
        weeks = {t["lobby_id"]: t["week"] for t in (await w.client.get(
            f"/api/v1/groups/{group['id']}", headers=w.heads["trainer"])).json()["teams"]}  # fmt: skip
        assert weeks == {t1: 2, t2: 1}
        assert (await w.client.get(f"/api/v1/groups/{group['id']}/debrief", headers=w.heads["a"])).status_code == 409
        debrief = (await w.client.get(f"/api/v1/groups/{group['id']}/debrief", headers=w.heads["trainer"])).json()
        assert [t["lobby_id"] for t in debrief["teams"]] == [t1, t2]
