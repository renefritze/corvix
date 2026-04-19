"""add_account_fields_to_notification_records

Revision ID: 6d0e5f9d2a1b
Revises: b5f6dbd95c30
Create Date: 2026-04-17

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6d0e5f9d2a1b"
down_revision: str | None = "b5f6dbd95c30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add account identity columns and update uniqueness scope."""
    op.add_column(
        "notification_records",
        sa.Column("account_id", sa.Text(), nullable=False, server_default="primary"),
    )
    op.add_column(
        "notification_records",
        sa.Column("account_label", sa.Text(), nullable=False, server_default="Primary"),
    )
    op.drop_constraint("notification_records_user_id_thread_id_key", "notification_records", type_="unique")
    op.create_unique_constraint(
        "notification_records_user_id_account_id_thread_id_key",
        "notification_records",
        ["user_id", "account_id", "thread_id"],
    )


def downgrade() -> None:
    """Restore pre-account uniqueness and remove account columns."""
    op.drop_constraint("notification_records_user_id_account_id_thread_id_key", "notification_records", type_="unique")
    op.create_unique_constraint(
        "notification_records_user_id_thread_id_key",
        "notification_records",
        ["user_id", "thread_id"],
    )
    op.drop_column("notification_records", "account_label")
    op.drop_column("notification_records", "account_id")
