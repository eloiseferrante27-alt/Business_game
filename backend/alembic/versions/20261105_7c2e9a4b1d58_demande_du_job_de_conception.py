"""demande du job de conception

Colonne generation_jobs.request (annexe 0008 §6) : sections, graine et consigne du job. Les lignes existantes
reçoivent `{}` : aucune ne change de sens, pas de migration de données.

Revision ID: 7c2e9a4b1d58
Revises: 3a99c3159451
Create Date: 2026-11-05 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7c2e9a4b1d58"
down_revision: str | None = "3a99c3159451"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column(
            "request", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "request")
