"""SQLAlchemy ORM models and engine helpers for PostgreSQL persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from corvix.env import get_env_value


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class User(Base):
    """Registered user with an encrypted GitHub token."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_login: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    github_token: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet-encrypted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    preferences: Mapped[UserPreferences | None] = relationship("UserPreferences", back_populates="user", uselist=False)
    push_subscriptions: Mapped[list[PushSubscription]] = relationship("PushSubscription", back_populates="user")
    notification_records: Mapped[list[NotificationRecordRow]] = relationship(
        "NotificationRecordRow", back_populates="user"
    )


class NotificationRecordRow(Base):
    """Persisted notification record scoped to a user."""

    __tablename__ = "notification_records"
    __table_args__ = (UniqueConstraint("user_id", "thread_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(Text, nullable=False)
    repository: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    subject_title: Mapped[str] = mapped_column(Text, nullable=False)
    subject_type: Mapped[str] = mapped_column(Text, nullable=False)
    unread: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    thread_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    matched_rules: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    actions_taken: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="notification_records")


class UserPreferences(Base):
    """Per-user preferences (theme, browser notifications)."""

    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    theme: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    browser_notify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship("User", back_populates="preferences")


class PushSubscription(Base):
    """Browser push subscription for a user."""

    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "endpoint"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="push_subscriptions")


def get_database_url(url_env: str = "DATABASE_URL") -> str | None:
    """Return DB URL from env, supporting `${URL_ENV}_FILE` Docker secret files."""
    return get_env_value(url_env)
