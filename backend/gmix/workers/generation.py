"""Worker de conception d'usine par l'IA (ADR 0010 annexe §7, ADR 0008 annexe §5).

Lancement : scripts\\worker.ps1 generation   (ou python -m gmix.workers.generation)
Commande `generation.requested` (topic generation.commands) -> design_factory (tâche IA) -> generate(GameParams)
-> jeu `draft` + job `succeeded`, événements sur generation.events. Rejouable : un job qui n'est plus `queued`
est ignoré. Le brief n'est jamais journalisé (empreinte `brief_sha256` seulement).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select, update

from gmix.db import get_sessionmaker
from gmix.db.models import BusinessGame, GameStatus, GenerationJob, JobStatus
from gmix.game.generation import autopilot_check, generate, unsourced
from gmix.game.spec import GameParams
from gmix.llm.factory_design import FactoryDesign, design_factory
from gmix.llm.service import LLMService
from gmix.messaging.envelope import Envelope
from gmix.messaging.kafka import EventProducer, consume
from gmix.messaging.topics import GENERATION_COMMANDS, GENERATION_EVENTS
from gmix.workers.runtime import run_worker

log = logging.getLogger("gmix.worker.generation")
SOURCE = "worker-generation"
INTERRUPTED = "Conception interrompue : relancez la conception."


async def _set_job(job_id: uuid.UUID, **values: Any) -> None:
    async with get_sessionmaker()() as session:
        await session.execute(update(GenerationJob).where(GenerationJob.id == job_id).values(**values))
        await session.commit()


async def _fail(job_id: uuid.UUID, game_id: uuid.UUID, stage: str, error: str, emit) -> None:  # noqa: ANN001
    """Job en `failed` ; le jeu repasse en `draft` s'il a une spec, sinon `failed`."""
    await _set_job(job_id, status=JobStatus.FAILED, stage=stage, error=error)
    async with get_sessionmaker()() as session:
        game = await session.get(BusinessGame, game_id)
        if game is not None:
            game.status = GameStatus.DRAFT if game.spec else GameStatus.FAILED
            await session.commit()
    await emit("generation.failed", {"job_id": str(job_id), "game_id": str(game_id), "stage": stage, "error": error})


def _usage(d: FactoryDesign) -> dict[str, Any]:
    return {"design": {
        "model": d.model, "prompt_tokens": d.prompt_tokens, "completion_tokens": d.completion_tokens,
        "ms": d.duration_ms, "attempts": d.attempts, "fallback": d.fallback, "reasons": d.reasons,
        "unmet": d.unmet, "prompt_version": d.prompt_version, "brief_sha256": d.brief_sha256,
    }}  # fmt: skip


async def process(event: Envelope, llm: LLMService, producer: Any) -> None:
    """Traite une commande ; ne lève que pour un message illisible (-> DLQ)."""
    try:
        job_id, game_id = uuid.UUID(event.payload["job_id"]), uuid.UUID(event.payload["game_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("commande de conception illisible") from exc

    async def emit(kind: str, payload: dict[str, Any]) -> None:
        await producer.publish(GENERATION_EVENTS, event.reply(kind, SOURCE, payload))

    async def progress(stage: str, pct: int) -> None:
        await _set_job(job_id, stage=stage, progress=pct)
        await emit("generation.progress", {"job_id": str(job_id), "game_id": str(game_id), "stage": stage,
                                           "progress": pct, "attempt": 1})  # fmt: skip

    async with get_sessionmaker()() as session:  # prise du job : seul un job `queued` est traité
        claimed = await session.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == JobStatus.QUEUED)
            .values(status=JobStatus.RUNNING, stage="brief", progress=5)
            .returning(GenerationJob.request)
        )
        row = claimed.first()
        await session.commit()
        game = await session.get(BusinessGame, game_id)
    if row is None or game is None:
        log.info("job %s ignoré (déjà traité ou jeu absent)", job_id)
        return
    seed = int((row[0] or {}).get("seed", 0))
    try:
        await progress("concept", 10)
        design = await design_factory(llm, game.brief, seed=seed)
        await progress("simulation", 40)
        spec = generate(GameParams(**design.params))
        await progress("checks", 90)
        review = {"autopilot": autopilot_check(spec), "unsourced": unsourced(spec), "fallback": design.fallback,
                  "reasons": design.reasons, "unmet": design.unmet, "attempts": design.attempts}  # fmt: skip
        async with get_sessionmaker()() as session:
            game = await session.get(BusinessGame, game_id)
            game.spec, game.title, game.status = spec, spec["meta"]["title"][:200], GameStatus.DRAFT
            game.params, game.review = spec["params"], review
            game.spec_version = (game.spec_version or 0) + 1
            await session.commit()
        await _set_job(job_id, status=JobStatus.SUCCEEDED, stage="done", progress=100, usage=_usage(design))
    except Exception as exc:
        log.exception("conception %s en échec", job_id)
        await _fail(job_id, game_id, "design", f"La conception a échoué ({type(exc).__name__}). Réessayez.", emit)
        return
    await emit("generation.completed", {
        "job_id": str(job_id), "game_id": str(game_id), "title": spec["meta"]["title"],
        "fallback": design.fallback, "unmet": design.unmet, "attempts": design.attempts,
        "duration_ms": design.duration_ms, "tokens": design.prompt_tokens + design.completion_tokens,
    })  # fmt: skip
    log.info("conception %s terminée (repli=%s, brief=%s)", job_id, design.fallback, design.brief_sha256[:12])


async def recover(producer: Any) -> None:
    """Au démarrage : les jobs restés `running` (worker arrêté) passent en `failed`."""
    async with get_sessionmaker()() as session:
        stuck = (await session.execute(
            select(GenerationJob.id, GenerationJob.business_game_id, GenerationJob.requested_by)
            .where(GenerationJob.status == JobStatus.RUNNING, GenerationJob.kind == "design")
        )).all()  # fmt: skip
    for job_id, game_id, user_id in stuck:
        event = Envelope(type="generation.requested", source=SOURCE, correlation_id=game_id, client_id=str(user_id),
                         payload={})  # fmt: skip

        async def emit(kind: str, payload: dict[str, Any], event: Envelope = event) -> None:
            await producer.publish(GENERATION_EVENTS, event.reply(kind, SOURCE, payload))

        await _fail(job_id, game_id, "interrupted", INTERRUPTED, emit)


async def main() -> None:
    llm = LLMService.from_settings()
    producer = EventProducer()
    await producer.start()
    try:
        await recover(producer)
        await consume(
            [GENERATION_COMMANDS], lambda e: process(e, llm, producer), group_id="worker-generation", dlq=producer,
            max_poll_interval_ms=15 * 60_000,
        )  # fmt: skip
    finally:
        await producer.stop()
        await llm.aclose()


if __name__ == "__main__":
    run_worker(main)
