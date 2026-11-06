"""Worker de conception : unitaire (faux LLM, base réelle) et intégration Kafka + base."""

import asyncio
import uuid

import pytest
from sqlalchemy import delete

from gmix.db import get_engine, get_sessionmaker
from gmix.db.models import BusinessGame, GameStatus, GenerationJob, JobStatus, User, UserRole
from gmix.game.generation import generate
from gmix.game.spec import GameParams, default_params, load_pack
from gmix.llm.factory_design import FactoryDesign
from gmix.messaging.envelope import Envelope
from gmix.workers import generation

BRIEF = "Une usine de vélos, cadence modérée, avec des pannes machine."


class Bus:
    def __init__(self) -> None:
        self.sent: list[Envelope] = []

    async def publish(self, topic, event, key=None) -> None:  # noqa: ANN001
        self.sent.append(event)


async def _seed(session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:  # noqa: ANN001
    user = User(username=f"wk_{uuid.uuid4().hex[:8]}", display_name="t", role=UserRole.TRAINER)
    session.add(user)
    await session.flush()
    game = BusinessGame(
        domain_slug="supply-chain", created_by=user.id, title="t", brief=BRIEF, status=GameStatus.GENERATING
    )
    session.add(game)
    await session.flush()
    job = GenerationJob(business_game_id=game.id, kind="design", requested_by=user.id, request={"seed": 3})
    session.add(job)
    await session.commit()
    return user.id, game.id, job.id


def _command(user_id, game_id, job_id) -> Envelope:  # noqa: ANN001
    return Envelope(type="generation.requested", source="api", correlation_id=game_id, client_id=str(user_id),
                    payload={"job_id": str(job_id), "game_id": str(game_id)})  # fmt: skip


async def _run_case(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_design(llm, brief, *, seed=0, pack_id="usine", keep=None, note=None):  # noqa: ANN001
        assert brief == BRIEF
        return FactoryDesign(params=default_params(pack_id), fallback=False,
                             attempts=1, model="fake", prompt_tokens=3, completion_tokens=4)  # fmt: skip

    monkeypatch.setattr(generation, "design_factory", fake_design)
    async with get_sessionmaker()() as session:
        user_id, game_id, job_id = await _seed(session)
    bus = Bus()
    try:
        cmd = _command(user_id, game_id, job_id)
        await generation.process(cmd, None, bus)  # type: ignore[arg-type]
        await generation.process(cmd, None, bus)  # rejeu : ignoré
        types = [e.type for e in bus.sent]
        assert types[-1] == "generation.completed" and types.count("generation.completed") == 1
        assert all(e.client_id == str(user_id) and e.correlation_id == game_id for e in bus.sent)
        async with get_sessionmaker()() as session:
            game, job = await session.get(BusinessGame, game_id), await session.get(GenerationJob, job_id)
            assert (game.status, game.spec_version, job.status) == (GameStatus.DRAFT, 1, JobStatus.SUCCEEDED)
            assert job.usage["design"]["model"] == "fake" and game.review["fallback"] is False
        with pytest.raises(ValueError):
            await generation.process(Envelope(type="x", source="t", payload={"job_id": "?"}), None, bus)  # type: ignore[arg-type]
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(BusinessGame).where(BusinessGame.id == game_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
        await get_engine().dispose()


@pytest.mark.integration
def test_process_with_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Base réelle requise (PostgreSQL), pas Kafka ni Ollama."""
    asyncio.run(_run_case(monkeypatch))


async def _seed_regen(kind: str, section: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, dict]:
    spec = generate(GameParams(**(default_params("usine") | {"company_name": "Acme Vélos", "seed": 5})))
    async with get_sessionmaker()() as session:
        user = User(username=f"wk_{uuid.uuid4().hex[:8]}", display_name="t", role=UserRole.TRAINER)
        session.add(user)
        await session.flush()
        game = BusinessGame(domain_slug="supply-chain", created_by=user.id, title="t", brief=BRIEF,
                            status=GameStatus.GENERATING, spec=spec, params=spec["params"], spec_version=1,
                            review={"attempts": 1, "keepme": 1})  # fmt: skip
        session.add(game)
        await session.flush()
        job = GenerationJob(business_game_id=game.id, kind=kind, requested_by=user.id,
                            request={"sections": [section], "seed": 9, "note": None})  # fmt: skip
        session.add(job)
        await session.commit()
        return user.id, game.id, job.id, spec


async def _regen_case(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    seen: dict = {}
    other = next(t for t in load_pack("usine")["agent_tones"] if t != default_params("usine")["agent_tone"])

    async def fake_design(llm, brief, *, seed=0, pack_id="usine", keep=None, note=None):  # noqa: ANN001
        seen.update(keep=keep, seed=seed)
        if mode == "error":
            raise RuntimeError("boom")
        params = default_params(pack_id) | {"agent_tone": other} | keep
        return FactoryDesign(params=params, fallback=mode == "fallback", reasons=["r"], attempts=1, model="fake")

    monkeypatch.setattr(generation, "design_factory", fake_design)
    user_id, game_id, job_id, spec = await _seed_regen("regenerate_personnages", "personnages")
    try:
        await generation.process(_command(user_id, game_id, job_id), None, Bus())  # type: ignore[arg-type]
        async with get_sessionmaker()() as session:
            game, job = await session.get(BusinessGame, game_id), await session.get(GenerationJob, job_id)
            assert game.status == GameStatus.DRAFT and game.brief == BRIEF and game.review["keepme"] == 1
            assert (
                seen["seed"] == 9 and "agent_tone" not in seen["keep"] and seen["keep"]["company_name"] == "Acme Vélos"
            )
            if mode == "ok":
                assert (
                    game.spec["params"]["agent_tone"] == other and game.spec["params"]["company_name"] == "Acme Vélos"
                )
                assert game.spec["params"]["seed"] == 5 and game.spec_version == 2 and game.review["dropped"] == []
                assert job.status == JobStatus.SUCCEEDED
            elif mode == "fallback":
                assert game.spec == spec and game.review["fallback"] is True and job.status == JobStatus.SUCCEEDED
            else:
                assert game.spec == spec and job.status == JobStatus.FAILED
    finally:
        async with get_sessionmaker()() as session:
            await session.execute(delete(BusinessGame).where(BusinessGame.id == game_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
        await get_engine().dispose()


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["ok", "fallback", "error"])
def test_regenerate_section(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    asyncio.run(_regen_case(monkeypatch, mode))


@pytest.mark.integration
def test_regenerate_drops_stale_layout_edits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une retouche qui ne passe plus après régénération est retirée de la spec et listée dans `review.dropped`."""
    stale = {"op": "remove", "object_id": "inconnu.0"}

    async def fake_design(llm, brief, *, seed=0, pack_id="usine", keep=None, note=None):  # noqa: ANN001
        return FactoryDesign(params=default_params(pack_id) | keep, fallback=False, attempts=1, model="fake")

    async def run() -> None:
        monkeypatch.setattr(generation, "design_factory", fake_design)
        user_id, game_id, job_id, spec = await _seed_regen("regenerate_personnages", "personnages")
        async with get_sessionmaker()() as session:
            game = await session.get(BusinessGame, game_id)
            game.spec = spec | {"layout_edits": [stale]}
            await session.commit()
        try:
            await generation.process(_command(user_id, game_id, job_id), None, Bus())  # type: ignore[arg-type]
            async with get_sessionmaker()() as session:
                game = await session.get(BusinessGame, game_id)
                assert game.status == GameStatus.DRAFT and game.spec["layout_edits"] == []
                assert [r["index"] for r in game.review["dropped"]] == [0]
        finally:
            async with get_sessionmaker()() as session:
                await session.execute(delete(BusinessGame).where(BusinessGame.id == game_id))
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()
            await get_engine().dispose()

    asyncio.run(run())


@pytest.mark.integration
def test_design_applies_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}

    async def fake_design(llm, brief, *, seed=0, pack_id="usine", keep=None, note=None):  # noqa: ANN001
        seen["keep"] = keep
        return FactoryDesign(params=default_params(pack_id) | keep, fallback=False, attempts=1, model="fake")

    async def run() -> None:
        monkeypatch.setattr(generation, "design_factory", fake_design)
        async with get_sessionmaker()() as session:
            user_id, game_id, job_id = await _seed(session)
            game = await session.get(BusinessGame, game_id)
            game.params = {"pack": "usine", "fixed": {"weeks": 8}, "players_min": 3, "players_max": 4}
            await session.commit()
        try:
            await generation.process(_command(user_id, game_id, job_id), None, Bus())  # type: ignore[arg-type]
            assert seen["keep"] == {"weeks": 8, "players_min": 3, "players_max": 4}
            async with get_sessionmaker()() as session:
                assert (await session.get(BusinessGame, game_id)).spec["params"]["weeks"] == 8
        finally:
            async with get_sessionmaker()() as session:
                await session.execute(delete(BusinessGame).where(BusinessGame.id == game_id))
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()
            await get_engine().dispose()

    asyncio.run(run())


def test_unreadable_command_goes_to_dlq() -> None:
    with pytest.raises(ValueError):
        asyncio.run(generation.process(Envelope(type="x", source="t", payload={}), None, Bus()))  # type: ignore[arg-type]
