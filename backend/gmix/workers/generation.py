"""Worker de conception d'usine par l'IA (ADR 0010 annexe §7, ADR 0008 annexe §5).

Lancement : scripts\\worker.ps1 generation   (ou python -m gmix.workers.generation)
Commande `generation.requested` (topic generation.commands) -> design_factory (tâche IA) -> generate(GameParams)
-> jeu `draft` + job `succeeded`, événements sur generation.events. Rejouable : un job qui n'est plus `queued`
est ignoré. Le brief n'est jamais journalisé (empreinte `brief_sha256` seulement).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import or_, select, update

from gmix.db import get_sessionmaker
from gmix.db.models import BusinessGame, GameStatus, GenerationJob, JobStatus
from gmix.game.generation import autopilot_check, generate, unsourced
from gmix.game.layout import recompile_layout
from gmix.game.spec import FACTORY_SECTIONS, GameParams, load_pack
from gmix.llm.factory_design import FactoryDesign, design_factory, design_schema
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


def _keep(game: BusinessGame, section: str | None) -> tuple[dict[str, Any], str]:
    """Clés imposées au modèle et pack. `design` : `fixed` + joueurs ; `regenerate_<s>` : les params hors section,
    plus les clés de la section que le modèle ne produit pas (ex. `company_name`)."""
    if section is None:
        p = game.params or {}
        return (p.get("fixed") or {}) | {k: p[k] for k in ("players_min", "players_max") if k in p}, p.get(
            "pack", "usine"
        )
    params = (game.spec or {}).get("params") or {}
    pack_id = params.get("pack", "usine")
    produced = set(design_schema(load_pack(pack_id))["properties"])
    redo = FACTORY_SECTIONS[section] & produced
    return {k: v for k, v in params.items() if k not in redo}, pack_id


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
            .returning(GenerationJob.request, GenerationJob.kind)
        )
        row = claimed.first()
        await session.commit()
        game = await session.get(BusinessGame, game_id)
    if row is None or game is None:
        log.info("job %s ignoré (déjà traité ou jeu absent)", job_id)
        return
    request, job_kind = row[0] or {}, row[1]
    seed = int(request.get("seed", 0))
    section = (request.get("sections") or [None])[0] if job_kind.startswith("regenerate_") else None
    try:
        await progress("concept", 10)
        old = game.spec or {}
        keep, pack_id = _keep(game, section)
        design = await design_factory(llm, game.brief, seed=seed, pack_id=pack_id, keep=keep, note=request.get("note"))
        await progress("simulation", 40)
        dropped: list[dict[str, Any]] = []
        if section and design.fallback:  # repli : la spec ne change pas
            spec = old
            review = {"fallback": True, "reasons": design.reasons, "section": section}
        else:
            spec = generate(GameParams(**design.params))
            if section and old.get("layout_edits") and spec.get("departments"):
                spec, dropped = recompile_layout(spec, load_pack(spec["meta"]["pack"]), old["layout_edits"])
                gone = {r["index"] for r in dropped}
                spec["layout_edits"] = [e for i, e in enumerate(old["layout_edits"]) if i not in gone]
            await progress("checks", 90)
            review = {"autopilot": autopilot_check(spec), "unsourced": unsourced(spec), "fallback": design.fallback,
                      "reasons": design.reasons, "unmet": design.unmet, "attempts": design.attempts}  # fmt: skip
            if section:
                review |= {"section": section, "dropped": dropped}
        async with get_sessionmaker()() as session:
            game = await session.get(BusinessGame, game_id)
            if section:  # `brief` jamais touché ; `review` fusionnée (ADR 0012 §1)
                review = (game.review or {}) | review
            if not (section and design.fallback):
                game.spec, game.title = spec, spec["meta"]["title"][:200]
                game.params = spec["params"]
                game.spec_version = (game.spec_version or 0) + 1
            game.status, game.review = GameStatus.DRAFT, review
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
            .where(
                GenerationJob.status == JobStatus.RUNNING,
                or_(GenerationJob.kind == "design", GenerationJob.kind.like("regenerate\\_%")),
            )
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
