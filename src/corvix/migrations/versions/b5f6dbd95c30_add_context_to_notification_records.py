"""add_context_to_notification_records

Revision ID: b5f6dbd95c30
Revises: 0f8b8f5c4c7d
Create Date: 2026-04-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b5f6dbd95c30"
down_revision: str | None = "0f8b8f5c4c7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist enrichment context on notification records."""
    op.add_column(
        "notification_records",
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Remove enrichment context from notification records."""
    op.drop_column("notification_records", "context")
