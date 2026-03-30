"""initial_schema

Revision ID: 838399841a57
Revises:
Create Date: 2026-03-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "838399841a57"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables for the initial schema."""
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("github_login", sa.Text, unique=True, nullable=False),
        sa.Column("github_token", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "notification_records",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("thread_id", sa.Text, nullable=False),
        sa.Column("repository", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("subject_title", sa.Text, nullable=False),
        sa.Column("subject_type", sa.Text, nullable=False),
        sa.Column("unread", sa.Boolean, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("thread_url", sa.Text, nullable=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("excluded", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("matched_rules", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("actions_taken", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("dismissed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "thread_id"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("theme", sa.Text, nullable=False, server_default="default"),
        sa.Column("browser_notify", sa.Boolean, nullable=False, server_default="false"),
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("p256dh_key", sa.Text, nullable=False),
        sa.Column("auth_key", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "endpoint"),
    )


def downgrade() -> None:
    """Drop all tables in reverse creation order."""
    op.drop_table("push_subscriptions")
    op.drop_table("user_preferences")
    op.drop_table("notification_records")
    op.drop_table("users")
