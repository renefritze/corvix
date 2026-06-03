"""SQLAlchemy ORM models and engine helpers for PostgreSQL persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from corvix.env import get_env_value


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class NotificationRecordRow(Base):
    """Persisted notification record."""

    __tablename__ = "notification_records"
    __table_args__ = (UniqueConstraint("user_id", "account_id", "thread_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)
    account_id: Mapped[str] = mapped_column(Text, nullable=False)
    account_label: Mapped[str] = mapped_column(Text, nullable=False)
    thread_id: Mapped[str] = mapped_column(Text, nullable=False)
    repository: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    subject_title: Mapped[str] = mapped_column(Text, nullable=False)
    subject_type: Mapped[str] = mapped_column(Text, nullable=False)
    unread: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    thread_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    web_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    matched_rules: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    actions_taken: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    context: Mapped[dict[str, object]] = mapped_column(postgresql.JSONB, nullable=False, default=dict)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class PollerStatusRow(Base):
    """Latest poller status (single-row table, keyed by the fixed single-user UUID)."""

    __tablename__ = "poller_status"

    user_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    last_poll_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_errors: Mapped[list[dict[str, object]] | None] = mapped_column(postgresql.JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def get_database_url(url_env: str = "DATABASE_URL") -> str | None:
    """Return DB URL from env, supporting `${URL_ENV}_FILE` Docker secret files."""
    return get_env_value(url_env)
