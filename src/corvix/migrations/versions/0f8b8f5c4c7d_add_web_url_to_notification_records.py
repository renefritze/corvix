"""add_web_url_to_notification_records

Revision ID: 0f8b8f5c4c7d
Revises: 838399841a57
Create Date: 2026-03-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0f8b8f5c4c7d"
down_revision: str | None = "838399841a57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the browser-facing GitHub URL to persisted notification records."""
    op.add_column("notification_records", sa.Column("web_url", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the browser-facing GitHub URL column."""
    op.drop_column("notification_records", "web_url")
