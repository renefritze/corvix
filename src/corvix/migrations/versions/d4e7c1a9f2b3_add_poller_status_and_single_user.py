"""add_poller_status_and_single_user

Revision ID: d4e7c1a9f2b3
Revises: c3a1f2e9b8d0
Create Date: 2026-05-25

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e7c1a9f2b3"
down_revision: str | None = "c3a1f2e9b8d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USERS_ID_FK = "users.id"
SINGLE_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Add the poller_status table and seed the single-user identity row.

    The poller status (last poll time / errors) moves from the JSON cache file
    into PostgreSQL so the poller and web service share it without a volume.
    The seeded user row gives single-user deployments a fixed user_id that
    satisfies the notification_records / poller_status foreign keys.
    """
    op.create_table(
        "poller_status",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(USERS_ID_FK), primary_key=True),
        sa.Column("status", sa.Text, nullable=False, server_default="unknown"),
        sa.Column("last_poll_time", sa.Text, nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("last_error_time", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO users (id, github_login, github_token, created_at, updated_at)
            VALUES (:user_id, '__corvix_single_user__', '', now(), now())
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(user_id=SINGLE_USER_ID)
    )


def downgrade() -> None:
    """Drop the poller_status table.

    The seeded single-user row is intentionally left in place; deleting it could
    violate foreign keys from existing notification_records.
    """
    op.drop_table("poller_status")
