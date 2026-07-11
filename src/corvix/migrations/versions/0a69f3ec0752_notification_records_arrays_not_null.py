"""notification_records_arrays_not_null

Revision ID: 0a69f3ec0752
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0a69f3ec0752"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill NULLs and enforce NOT NULL on the array columns.

    `db.py`'s ORM model has always declared `matched_rules`/`actions_taken`
    as non-optional, but the initial migration never added the matching
    NOT NULL constraint -- these two were out of sync since day one.
    """
    op.execute("UPDATE notification_records SET matched_rules = '{}' WHERE matched_rules IS NULL")
    op.execute("UPDATE notification_records SET actions_taken = '{}' WHERE actions_taken IS NULL")
    op.alter_column(
        "notification_records",
        "matched_rules",
        existing_type=postgresql.ARRAY(sa.String()),
        nullable=False,
        existing_server_default="{}",
    )
    op.alter_column(
        "notification_records",
        "actions_taken",
        existing_type=postgresql.ARRAY(sa.String()),
        nullable=False,
        existing_server_default="{}",
    )


def downgrade() -> None:
    """Relax the array columns back to nullable."""
    op.alter_column(
        "notification_records",
        "matched_rules",
        existing_type=postgresql.ARRAY(sa.String()),
        nullable=True,
        existing_server_default="{}",
    )
    op.alter_column(
        "notification_records",
        "actions_taken",
        existing_type=postgresql.ARRAY(sa.String()),
        nullable=True,
        existing_server_default="{}",
    )
