"""groupes d'équipes

Table lobby_groups et colonne lobbies.group_id (ADR 0011 §2) : un groupe rassemble des lobbies, une équipe chacun.
Les lobbies existants gardent group_id NULL : aucun ne change de sens, pas de migration de données.

Revision ID: b4e1f6a2c903
Revises: 7c2e9a4b1d58
Create Date: 2026-11-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4e1f6a2c903"
down_revision: str | None = "7c2e9a4b1d58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lobby_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("join_code", sa.String(length=8), nullable=False),
        sa.Column("trainer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trainer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["business_game_id"], ["business_games.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("join_code"),
    )
    op.create_index(op.f("ix_lobby_groups_trainer_id"), "lobby_groups", ["trainer_id"], unique=False)
    op.add_column("lobbies", sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_lobbies_group_id"), "lobbies", ["group_id"], unique=False)
    op.create_foreign_key(
        "fk_lobbies_group_id_lobby_groups", "lobbies", "lobby_groups", ["group_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("fk_lobbies_group_id_lobby_groups", "lobbies", type_="foreignkey")
    op.drop_index(op.f("ix_lobbies_group_id"), table_name="lobbies")
    op.drop_column("lobbies", "group_id")
    op.drop_index(op.f("ix_lobby_groups_trainer_id"), table_name="lobby_groups")
    op.drop_table("lobby_groups")
