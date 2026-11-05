"""Business games simulés : génération par paramètres (instantanée, sans modèle ni texte libre), relecture,
import et export de la spec (docs/decisions/0006). Un formateur ne voit que ses business games, l'admin les voit
tous (docs/roles.md)."""

import secrets
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import delete, func, select

from gmix.api.auth import Session, Staff
from gmix.api.deps import publish
from gmix.assets_catalog import load_assets_catalog
from gmix.db.models import BusinessGame, GameStatus, GenerationJob, JobStatus, Lobby, LobbyStatus, User, UserRole
from gmix.game import generation
from gmix.game.engine import GameRuleError
from gmix.game.generation import autopilot_check, generate
from gmix.game.layout import check_placement, pack_coverage, recompile_layout
from gmix.game.spec import DesignRequest, GameParams, LayoutEdit, SimSpec, load_pack
from gmix.messaging.envelope import Actor, Envelope
from gmix.messaging.topics import AUDIT, GENERATION_COMMANDS
from gmix.settings import get_settings

router = APIRouter(prefix="/api/v1/games", tags=["business games"])
# [min, max, défaut], comme `limits` d'un pack ; ai/simulation.yaml n'en déclare pas
ATELIER_RANGES = {"weeks": [4, 12, 8], "products": [2, 4, 3]}
ATELIER_INFO = {  # ai/simulation.yaml n'a pas ces clés ; un pack de ai/packs/ les déclare lui-même
    "label": "Atelier de production",
    "description": "Simulation hebdomadaire de chaîne logistique : achats, lignes agrégées, qualité, ventes.",
    "domain": "supply-chain",
    "engine": "weekly",
}
SpecBody = Annotated[dict[str, Any], Body(description="spec complète (gmix.game.spec.SimSpec)")]


class GameSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    domain_slug: str
    status: GameStatus
    created_at: datetime


class GameDetail(GameSummary):
    brief: str
    params: dict[str, Any]
    review: dict[str, Any]
    spec_version: int
    spec: dict[str, Any] | None


async def owned_game(session: Session, game_id: uuid.UUID, user: User) -> BusinessGame:
    game = await session.get(BusinessGame, game_id)
    if game is None or (user.role != UserRole.ADMIN and game.created_by != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business game introuvable")
    return game


def _choices(pack: dict[str, Any]) -> dict[str, Any]:
    """Les choix d'un pack (secteurs, modules, agents, caractère, difficulté, aléas), tels que lus par le client."""
    return {
        "themes": [
            {"id": key, "label": t["label"], "description": t["description"],
             "products": [p["name"] for p in t["products"]]}
            for key, t in pack["themes"].items()
        ],
        "modules": [
            {"id": key, "title": m["title"], "description": m["description"]} for key, m in pack["modules"].items()
        ],
        "extra_agents": [
            {"id": key, "title": a["title"], "description": a["description"]}
            for key, a in pack["extra_agents"].items()
        ],
        "tones": [{"id": key, "label": t["label"]} for key, t in pack["agent_tones"].items()],
        "difficulties": [
            {"id": key, "label": d["label"], "detail": d["detail"]} for key, d in pack["difficulties"].items()
        ],
        "events": [{"id": key, "label": e["label"]} for key, e in pack["events_levels"].items()],
    }  # fmt: skip


def _pack_entry(pack_id: str) -> dict[str, Any]:
    pack = load_pack(pack_id)
    entry = ATELIER_INFO | {k: pack[k] for k in ATELIER_INFO if k in pack}
    cover = pack_coverage(pack_id, load_assets_catalog())
    return {"id": pack_id, **entry, "params": pack.get("params", []), **_choices(pack),
            "limits": pack.get("limits", ATELIER_RANGES),
            "coverage": cover, "available": cover["ratio"] >= 1.0}  # fmt: skip


@router.get("/options")
async def generation_options(actor: Staff) -> dict[str, Any]:
    """Choix proposés au formateur pour générer un business game : clés de premier niveau = pack « atelier »
    (ai/simulation.yaml, inchangé) ; `packs` liste tous les packs (ai/packs/*.yaml), `limits` au format `ranges`."""
    packs = ["atelier", *sorted(p.stem for p in (get_settings().gmix_ai_dir / "packs").glob("*.yaml"))]
    return _choices(load_pack("atelier")) | {"ranges": ATELIER_RANGES, "packs": [_pack_entry(p) for p in packs]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_game(
    params: GameParams, actor: Staff, session: Session, request: Request, force: bool = False
) -> GameDetail:
    """Génère le business game à partir des seuls paramètres (pack et options compris), puis le vérifie par une
    partie en pilote automatique. Pack dont les assets manquent : 422, sauf `force=true` pour l'admin (audité)."""
    missing = _uncovered(params.pack, actor, force)
    spec = _generate(params)
    game = BusinessGame(domain_slug=spec["meta"]["domain"], created_by=actor.id)
    session.add(game)
    await _store(session, request, game, spec, actor, "game.generated")
    await _audit_forced(request, actor, game, missing)
    return await get_game(game.id, actor, session)


def _generate(params: GameParams) -> dict[str, Any]:
    try:
        return generate(params)
    except GameRuleError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None


def _uncovered(pack_id: str, actor: User, force: bool) -> list[str]:
    """Assets manquants du pack ; lève 422 si le pack n'est pas couvert, sauf admin avec `force`."""
    try:
        missing = pack_coverage(pack_id, load_assets_catalog())["missing"]
    except ValueError as exc:  # pack inconnu
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    if missing and not (force and actor.role == UserRole.ADMIN):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"message": f"Le pack « {pack_id} » n'est pas couvert par les assets", "missing": missing},
        )
    return missing


async def _audit_forced(request: Request, actor: User, game: BusinessGame, missing: list[str]) -> None:
    if missing:
        payload = {"game_id": str(game.id), "forced": True, "missing": missing}
        actor_info = Actor(user_id=actor.id, role=actor.role.value)
        await publish(request, AUDIT, Envelope(type="game.forced", source="api", actor=actor_info, payload=payload))


@router.get("")
async def list_games(actor: Staff, session: Session) -> list[GameSummary]:
    query = select(BusinessGame).where(BusinessGame.status != GameStatus.ARCHIVED)
    if actor.role != UserRole.ADMIN:
        query = query.where(BusinessGame.created_by == actor.id)
    return [
        GameSummary.model_validate(g) for g in await session.scalars(query.order_by(BusinessGame.created_at.desc()))
    ]


DESIGN_SECTIONS = ["concept", "cast", "journey"]


@router.post("/designs", status_code=status.HTTP_202_ACCEPTED)
async def create_design(
    body: DesignRequest, actor: Staff, session: Session, request: Request, force: bool = False
) -> dict[str, str]:
    """Demande de conception par l'IA (annexe 0010 §7), usine seulement. Le jeu passe en `generating` ; le worker
    de conception (étapes 6 et 7) le fait passer en `draft` (succès ou repli déterministe) ou `failed`.
    Les réparations bornées et le repli sont ceux du worker, pas de cette route."""
    if body.pack != "usine":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"message": "La conception par l'IA ne concerne que l'usine", "missing": []},
        )
    missing = _uncovered(body.pack, actor, force)
    active = await session.scalar(
        select(GenerationJob.id)
        .where(GenerationJob.requested_by == actor.id, GenerationJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        .limit(1)
    )
    if active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Une conception est déjà en cours")
    seed = body.seed if body.seed is not None else secrets.randbelow(2**31)
    game = BusinessGame(
        domain_slug=load_pack(body.pack).get("domain", ATELIER_INFO["domain"]), created_by=actor.id,
        title=f"Conception en cours : {body.brief[:60]}", brief=body.brief, status=GameStatus.GENERATING,
        params=body.model_dump(mode="json"),
    )  # fmt: skip
    session.add(game)
    await session.flush()
    plan = {"sections": DESIGN_SECTIONS, "seed": seed, "note": None}
    job = GenerationJob(business_game_id=game.id, kind="design", requested_by=actor.id, request=plan)
    session.add(job)
    await session.commit()
    envelope = Envelope(
        type="generation.requested", source="api", correlation_id=game.id, client_id=str(actor.id),
        actor=Actor(user_id=actor.id, role=actor.role.value),
        payload={"job_id": str(job.id), "game_id": str(game.id), **plan},
    )  # fmt: skip
    try:
        await publish(request, GENERATION_COMMANDS, envelope, required=True)
    except HTTPException:  # rien n'est gardé si la demande ne part pas
        await session.execute(delete(GenerationJob).where(GenerationJob.id == job.id))
        await session.execute(delete(BusinessGame).where(BusinessGame.id == game.id))
        await session.commit()
        raise
    audit = {"game_id": str(game.id), "job_id": str(job.id), "seed": seed}
    await publish(
        request, AUDIT, Envelope(type="game.design_requested", source="api", actor=envelope.actor, payload=audit)
    )
    await _audit_forced(request, actor, game, missing)
    return {"game_id": str(game.id), "job_id": str(job.id)}


@router.get("/{game_id}/job")
async def get_job(game_id: uuid.UUID, actor: Staff, session: Session) -> dict[str, Any]:
    """Dernier job du jeu, avec sa place dans la file (jobs `queued` plus anciens)."""
    await owned_game(session, game_id, actor)
    job = await session.scalar(
        select(GenerationJob)
        .where(GenerationJob.business_game_id == game_id)
        .order_by(GenerationJob.created_at.desc())
        .limit(1)
    )
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune conception pour ce business game")
    ahead = await session.scalar(
        select(func.count()).where(GenerationJob.status == JobStatus.QUEUED, GenerationJob.created_at < job.created_at)
    )
    return {
        "id": str(job.id), "kind": job.kind, "status": job.status, "stage": job.stage, "progress": job.progress,
        "error": job.error, "usage": job.usage, "queue_position": ahead or 0,
        "created_at": job.created_at, "updated_at": job.updated_at,
    }  # fmt: skip


@router.get("/{game_id}")
async def get_game(game_id: uuid.UUID, actor: Staff, session: Session) -> GameDetail:
    return GameDetail.model_validate(await owned_game(session, game_id, actor))


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_game(actor: Staff, session: Session, request: Request, spec: SpecBody) -> GameDetail:
    """Crée un business game depuis une spec JSON (export d'un collègue, spec retouchée hors ligne)."""
    valid = _validated(spec)
    game = BusinessGame(domain_slug=valid["meta"]["domain"], created_by=actor.id)
    session.add(game)
    await _store(session, request, game, valid, actor, "game.imported", GameStatus.DRAFT)
    return await get_game(game.id, actor, session)


@router.put("/{game_id}/spec")
async def update_spec(
    game_id: uuid.UUID, actor: Staff, session: Session, request: Request, spec: SpecBody
) -> GameDetail:
    """Spec retouchée par le formateur (les lobbies déjà créés gardent leur copie)."""
    game = await owned_game(session, game_id, actor)
    await _store(session, request, game, _validated(spec), actor, "game.spec_saved", GameStatus.DRAFT)
    return await get_game(game_id, actor, session)


def _validated(spec: dict[str, Any]) -> dict[str, Any]:
    try:
        return SimSpec.model_validate(spec).model_dump(mode="json")
    except ValidationError as exc:
        errors = [f"{'/'.join(map(str, e['loc']))} : {e['msg']}" for e in exc.errors()[:20]]
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"message": "Spec invalide", "errors": errors}
        ) from None


async def _store(
    session: Session,
    request: Request,
    game: BusinessGame,
    spec: dict[str, Any],
    actor: User,
    event_type: str,
    status: GameStatus = GameStatus.READY,
    review_extra: dict[str, Any] | None = None,
) -> None:
    meta = spec["meta"]
    modules = ", ".join(m["title"].lower() for m in spec["modules"])
    game.spec, game.title, game.status = spec, meta["title"][:200], status
    game.brief = f"{meta['theme_label']} · {meta['difficulty_label']} · {meta['weeks']} semaines · {modules}"
    game.params = spec["params"]
    game.spec_version = (game.spec_version or 0) + 1  # None sur un objet pas encore inséré
    # `unsourced` vient de moteur-jeu (étape 4b) : absent, la revue ne le porte pas encore
    unsourced = getattr(generation, "unsourced", lambda _spec: [])
    game.review = {"autopilot": autopilot_check(spec), "unsourced": unsourced(spec),
                   "edited_by": str(actor.id)} | (review_extra or {})  # fmt: skip
    await session.commit()
    payload = {"game_id": str(game.id), "spec_version": game.spec_version, "seed": spec["seed"]}
    actor_info = Actor(user_id=actor.id, role=actor.role.value)
    await publish(request, AUDIT, Envelope(type=event_type, source="api", actor=actor_info, payload=payload))


# --- éditeur de grille et paramètres (ADR 0009, point 8) ; `ready` = publié ------------------------------------


class LayoutBody(BaseModel):
    layout_edits: list[LayoutEdit] = Field(max_length=200)


async def _editable(session: Session, game_id: uuid.UUID, actor: User) -> BusinessGame:
    """Business game du formateur, modifiable : ni en génération, ni joué par un lobby en cours (409)."""
    game = await owned_game(session, game_id, actor)
    if game.status == GameStatus.GENERATING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Le business game est en cours de génération")
    running = await session.scalar(
        select(Lobby.id).where(Lobby.business_game_id == game.id, Lobby.status == LobbyStatus.RUNNING).limit(1)
    )
    if running:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un lobby de ce business game est en cours de partie")
    return game


def _with_edits(spec: dict[str, Any], edits: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Spec dont le plan est recalculé puis retouché ; retourne aussi les retouches refusées par `apply_edits`."""
    return recompile_layout(spec, load_pack(spec["meta"]["pack"]), edits)


def _plan_error(errors: list[str], message: str, code: int) -> HTTPException:
    return HTTPException(code, {"message": message, "errors": errors})


@router.put("/{game_id}/layout")
async def update_layout(
    game_id: uuid.UUID, body: LayoutBody, actor: Staff, session: Session, request: Request
) -> GameDetail:
    """Enregistre la liste entière des retouches (idempotent). 422 avec les raisons si une retouche est refusée ou
    si le plan viole une règle du pack ; la partie repasse en `draft`."""
    game = await _editable(session, game_id, actor)
    if not game.spec or not game.spec.get("departments"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Ce business game n'a pas de plan modifiable")
    edits = [e.model_dump(mode="json") for e in body.layout_edits]
    spec, rejected = _with_edits(game.spec, edits)
    if rejected:
        reasons = [f"retouche {r['index'] + 1} : {r['message']}" for r in rejected]
        raise _plan_error(reasons, "Retouches refusées", status.HTTP_422_UNPROCESSABLE_CONTENT)
    spec = _validated(spec)
    if errors := check_placement(spec, load_pack(spec["meta"]["pack"])):
        raise _plan_error(errors, "Plan non conforme aux règles du pack", status.HTTP_422_UNPROCESSABLE_CONTENT)
    await _store(session, request, game, spec, actor, "game.layout_saved", GameStatus.DRAFT)
    return await get_game(game_id, actor, session)


@router.put("/{game_id}/params")
async def update_params(
    game_id: uuid.UUID, params: GameParams, actor: Staff, session: Session, request: Request, force: bool = False
) -> GameDetail:
    """Refait la génération avec la même graine et rejoue les retouches de plan (celles qui ne tiennent plus sont
    retirées et listées dans `review.dropped`) ; la partie repasse en `draft`."""
    game = await _editable(session, game_id, actor)
    missing = _uncovered(params.pack, actor, force)
    old = game.spec or {}
    spec = _generate(params.model_copy(update={"seed": old.get("seed", params.seed)}))
    dropped: list[dict[str, Any]] = []
    if old.get("layout_edits") and spec.get("departments"):
        spec, dropped = _with_edits(spec, old["layout_edits"])
        gone = {r["index"] for r in dropped}
        spec["layout_edits"] = [e for i, e in enumerate(old["layout_edits"]) if i not in gone]
    await _store(session, request, game, spec, actor, "game.params_saved", GameStatus.DRAFT, {"dropped": dropped})
    await _audit_forced(request, actor, game, missing)
    return await get_game(game_id, actor, session)


@router.post("/{game_id}/publish")
async def publish_game(game_id: uuid.UUID, actor: Staff, session: Session, request: Request) -> GameDetail:
    """Refait les contrôles (spec, règles de placement) puis publie (`ready`) ; 409 si un contrôle échoue."""
    game = await _editable(session, game_id, actor)
    if game.spec is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Business game sans spec")
    try:
        spec = _validated(game.spec)
    except HTTPException as exc:
        raise _plan_error(exc.detail["errors"], "Spec invalide", status.HTTP_409_CONFLICT) from None
    if spec.get("departments") and (errors := check_placement(spec, load_pack(spec["meta"]["pack"]))):
        raise _plan_error(errors, "Plan non conforme aux règles du pack", status.HTTP_409_CONFLICT)
    await _store(session, request, game, spec, actor, "game.published")
    return await get_game(game_id, actor, session)
