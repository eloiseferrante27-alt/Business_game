"""Worker de conception : unitaire (faux LLM, base réelle) et intégration Kafka + base."""

import asyncio
import uuid

import pytest
from sqlalchemy import delete

from gmix.db import get_engine, get_sessionmaker
from gmix.db.models import BusinessGame, GameStatus, GenerationJob, JobStatus, User, UserRole
from gmix.game.spec import default_params
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
    async def fake_design(llm, brief, *, seed=0, pack_id="usine"):  # noqa: ANN001
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


def test_unreadable_command_goes_to_dlq() -> None:
    with pytest.raises(ValueError):
        asyncio.run(generation.process(Envelope(type="x", source="t", payload={}), None, Bus()))  # type: ignore[arg-type]
