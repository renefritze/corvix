"""add_account_errors_to_poller_status

Revision ID: f7e3a2b9c1d5
Revises: d4e7c1a9f2b3
Create Date: 2026-05-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7e3a2b9c1d5"
down_revision: str | None = "d4e7c1a9f2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add account_errors JSONB column to poller_status.

    Stores per-account fetch failures so the web UI can surface broken
    tokens without failing the entire poll cycle.  NULL means no errors.
    """
    op.add_column(
        "poller_status",
        sa.Column("account_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("poller_status", "account_errors")
