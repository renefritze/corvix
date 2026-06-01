"""remove_multi_user_tables

Revision ID: a1b2c3d4e5f6
Revises: f7e3a2b9c1d5
Create Date: 2026-06-01

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f7e3a2b9c1d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop multi-user tables and their FK constraints.

    Corvix is single-user only. The users, user_preferences, and push_subscriptions
    tables existed as scaffolding for a multi-user mode that was never implemented.
    FK constraints on notification_records and poller_status are dropped; user_id
    columns are retained as plain UUIDs pointing to the seeded single-user value.
    """
    op.drop_constraint("notification_records_user_id_fkey", "notification_records", type_="foreignkey")
    op.drop_constraint("poller_status_user_id_fkey", "poller_status", type_="foreignkey")
    op.drop_table("push_subscriptions")
    op.drop_table("user_preferences")
    op.drop_table("users")


def downgrade() -> None:
    """No-op: dropped tables cannot be automatically restored."""
