"""Vote sur un joueur absent avec trois vrais joueurs inscrits (ADR 0010, annexe §1) : a et b connectés, c absent."""

from __future__ import annotations

import pytest

from tests.test_lobbies_round import _world


@pytest.mark.integration
async def test_two_present_vote_ignore_advances_week() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")
        await w.ready("a")
        view = (await w.ready("b")).json()["round"]
        assert view["vote"]["open"] and view["absent"] == [str(w.users["c"].id)]
        first = (await w.ready("a", absent="ignore")).json()  # 1 voix sur 2 : pas de majorité stricte
        assert first["state"]["week"] == 1 and first["round"]["vote"]["decision"] is None
        done = (await w.ready("b", absent="ignore")).json()
        assert done["state"]["week"] == 2 and done["round"]["ready"] == []


@pytest.mark.integration
async def test_incomplete_vote_does_not_advance() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")
        await w.ready("b")
        answer = (await w.ready("a", absent="ignore")).json()  # a vote ignore, b n'a pas voté
        assert answer["state"]["week"] == 1 and answer["round"]["vote"]["ignore"] == 1
        assert await w.week() == 1


@pytest.mark.integration
async def test_absent_returns_and_gets_ready_before_vote_ends() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")
        await w.ready("a")
        await w.ready("b")
        await w.ready("a", absent="ignore")
        w.connect("c")  # c revient avant le second bulletin : le vote se ferme
        assert not (await w.client.get(w.url, headers=w.heads["b"])).json()["round"]["vote"]["open"]
        assert (await w.ready("b", absent="ignore")).status_code == 409
        assert await w.week() == 1
        assert (await w.ready("c")).json()["state"]["week"] == 2  # tout le monde est prêt : la semaine part


@pytest.mark.integration
async def test_ballot_rules_double_vote_self_and_absent() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")
        await w.ready("a")
        await w.ready("b")
        # pas de vote pour soi : le bulletin porte sur « les absents » ; l'absent (c) ne peut pas voter lui-même
        assert (await w.ready("c", absent="ignore")).status_code == 409
        # voter deux fois remplace le bulletin au lieu de le compter deux fois
        for _ in range(2):
            vote = (await w.ready("a", absent="ignore")).json()["round"]["vote"]
        assert vote["ignore"] == 1 and vote["ballots"] == {str(w.users["a"].id): "ignore"}
        assert await w.week() == 1
        # un bulletin sans être prêt est refusé
        assert (await w.ready("a", False, absent="ignore")).status_code == 422


@pytest.mark.integration
async def test_player_of_another_lobby_cannot_vote() -> None:
    async with _world() as w, _world() as other:
        await w.open()
        await other.open()
        w.connect("a", "b")
        await w.ready("a")
        await w.ready("b")
        for absent in (None, "ignore"):
            body = {"ready": True} | ({"absent": absent} if absent else {})
            answer = await w.client.post(f"{w.url}/ready", json=body, headers=other.heads["a"])
            assert answer.status_code == 404
        assert (await w.ready("a", absent="ignore")).json()["round"]["vote"]["ballots"].keys() == {str(w.users["a"].id)}
        assert await w.week() == 1


@pytest.mark.integration
async def test_trainer_forces_advance_with_ignore_absent() -> None:
    async with _world() as w:
        await w.open()
        w.connect("a", "b")
        await w.ready("a")
        await w.ready("b")
        assert await w.week() == 1  # vote ouvert mais sans majorité
        assert (
            await w.client.post(f"{w.url}/advance", json={"ignore_absent": True}, headers=w.heads["a"])
        ).status_code == 403
        forced = await w.client.post(f"{w.url}/advance", json={"ignore_absent": True}, headers=w.heads["trainer"])
        assert forced.status_code == 200 and forced.json()["state"]["week"] == 2
        assert await w.week() == 2
