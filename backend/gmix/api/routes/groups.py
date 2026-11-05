"""Groupes de travail : un groupe rassemble des équipes, chacune jouée comme un lobby (une entreprise), ADR 0011 §2.
La partie de chaque équipe passe par /api/v1/lobbies/{id} ; ce routeur crée, liste, fait rejoindre et compare."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from gmix.api.auth import CurrentUser, Session, Staff
from gmix.api.routes.lobbies import _members, _view, audit_created, join, new_code, new_lobby, ready_game
from gmix.db.models import Lobby, LobbyGroup, LobbyMember, User, UserRole
from gmix.game import engine

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    business_game_id: uuid.UUID
    teams: int = Field(default=2, ge=1, le=12)
    advance_mode: Literal["auto", "manual"] = "auto"


class GroupJoin(BaseModel):
    code: str = Field(min_length=4, max_length=12)
    lobby_id: uuid.UUID | None = None  # absent : on liste les équipes pour que le joueur choisisse


def _manages(user: User, group: LobbyGroup) -> bool:
    return user.role == UserRole.ADMIN or group.trainer_id == user.id


async def _teams(session: Session, group: LobbyGroup) -> list[Lobby]:
    return list(await session.scalars(select(Lobby).where(Lobby.group_id == group.id).order_by(Lobby.created_at)))


async def _view_group(session: Session, group: LobbyGroup, user: User) -> dict[str, Any]:
    teams, mine = await _teams(session, group), None
    cards = []
    for lobby in teams:
        members = await _members(session, lobby.id)
        if any(m["user_id"] == str(user.id) for m in members):
            mine = str(lobby.id)
        cards.append({
            "lobby_id": str(lobby.id), "name": lobby.name, "status": lobby.status,
            "players": [{"display_name": m["display_name"], "game_role": m["game_role"]} for m in members],
            "max_players": lobby.spec["meta"]["players"]["max"],
            "week": lobby.state.get("week"), "game_status": lobby.state.get("status"),
        })  # fmt: skip
    return {
        "id": str(group.id), "name": group.name, "is_manager": _manages(user, group),
        "join_code": group.join_code if _manages(user, group) else None,
        "game_title": (teams[0].spec or {}).get("meta", {}).get("title") if teams else None,
        "my_team": mine, "teams": cards,
    }  # fmt: skip


async def _access(session: Session, group_id: uuid.UUID, user: User) -> LobbyGroup:
    """Groupe visible par son formateur, l'admin et les joueurs d'une de ses équipes ; 404 pour les autres."""
    group = await session.get(LobbyGroup, group_id)
    if group is not None and not _manages(user, group):
        member = await session.scalar(
            select(LobbyMember.lobby_id)
            .join(Lobby, Lobby.id == LobbyMember.lobby_id)
            .where(Lobby.group_id == group.id, LobbyMember.user_id == user.id)
        )
        group = group if member else None
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Groupe introuvable")
    return group


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(body: GroupCreate, actor: Staff, session: Session, request: Request) -> dict[str, Any]:
    game = await ready_game(session, body.business_game_id, actor)
    group = LobbyGroup(
        name=body.name, join_code=await new_code(session, LobbyGroup.join_code), trainer_id=actor.id,
        business_game_id=game.id,
    )  # fmt: skip
    session.add(group)
    await session.flush()
    teams = [
        await new_lobby(session, game, actor, f"Équipe {n}", body.advance_mode, group.id)
        for n in range(1, body.teams + 1)
    ]
    await session.commit()
    for lobby in teams:
        await audit_created(request, actor, lobby, game)
    return await _view_group(session, group, actor)


@router.get("")
async def list_groups(user: CurrentUser, session: Session) -> list[dict[str, Any]]:
    """Formateur : ses groupes ; joueur : ceux où il tient une équipe ; admin : tous."""
    query = select(LobbyGroup).order_by(LobbyGroup.created_at.desc()).limit(100)
    if user.role == UserRole.TRAINER:
        query = query.where(LobbyGroup.trainer_id == user.id)
    elif user.role == UserRole.PLAYER:
        teams = select(Lobby.group_id).join(LobbyMember, LobbyMember.lobby_id == Lobby.id)
        query = query.where(LobbyGroup.id.in_(teams.where(LobbyMember.user_id == user.id)))
    return [
        {"id": str(g.id), "name": g.name, "join_code": g.join_code if _manages(user, g) else None}
        for g in await session.scalars(query)
    ]


@router.post("/join")
async def join_group(body: GroupJoin, user: CurrentUser, session: Session, request: Request) -> dict[str, Any]:
    """Sans `lobby_id` : les équipes du groupe, pour choisir. Avec : entrée dans cette équipe (vue du lobby)."""
    group = await session.scalar(select(LobbyGroup).where(LobbyGroup.join_code == body.code.strip().upper()))
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Code inconnu")
    if body.lobby_id is None:
        return await _view_group(session, group, user) | {"join_code": None}
    query = select(Lobby).where(Lobby.id == body.lobby_id, Lobby.group_id == group.id).with_for_update()
    lobby = await session.scalar(query)
    if lobby is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Équipe introuvable dans ce groupe")
    member = await join(session, lobby, user, request)
    return await _view(session, lobby, user, member, request)


@router.get("/{group_id}")
async def get_group(group_id: uuid.UUID, user: CurrentUser, session: Session) -> dict[str, Any]:
    return await _view_group(session, await _access(session, group_id, user), user)


@router.get("/{group_id}/debrief")
async def get_group_debrief(group_id: uuid.UUID, user: CurrentUser, session: Session) -> dict[str, Any]:
    """Débrief de chaque équipe, côte à côte (EX-32). Un joueur l'ouvre quand toutes les équipes ont fini."""
    group = await _access(session, group_id, user)
    teams = await _teams(session, group)
    if not _manages(user, group) and any(t.state.get("status") != "finished" for t in teams):
        raise HTTPException(status.HTTP_409_CONFLICT, "Le débrief du groupe s'ouvre quand toutes les équipes ont fini")
    return {
        "id": str(group.id), "name": group.name,
        "teams": [{"lobby_id": str(t.id), "name": t.name, "debrief": engine.debrief(t.spec, t.state)} for t in teams],
    }  # fmt: skip
