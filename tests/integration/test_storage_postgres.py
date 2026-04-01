"""PostgreSQL integration tests for PostgresStorage."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from corvix.domain import Notification, NotificationRecord
from corvix.storage import PostgresStorage

SCORE_HIGH = 50.0
SCORE_LOW = 10.0
SCORE_UPDATED = 99.0


@pytest.fixture(scope="session")
def postgres_urls() -> Generator[tuple[str, str]]:
    testcontainers = pytest.importorskip("testcontainers.postgres")
    container = testcontainers.PostgresContainer("postgres:16-alpine")
    try:
        container.start()
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"Could not start Postgres test container: {error}")
    try:
        raw_url = container.get_connection_url()
        sqlalchemy_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        psycopg_url = raw_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        yield sqlalchemy_url, psycopg_url
    finally:
        container.stop()


@pytest.fixture(scope="session")
def migrated_postgres_url(postgres_urls: tuple[str, str]) -> Generator[str]:
    root = Path(__file__).resolve().parents[2]
    alembic_ini = root / "alembic.ini"
    sqlalchemy_url, psycopg_url = postgres_urls
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    try:
        command.upgrade(Config(str(alembic_ini)), "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url
    yield psycopg_url


@pytest.fixture()
def storage(migrated_postgres_url: str) -> Generator[PostgresStorage]:
    with psycopg.connect(migrated_postgres_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE notification_records, push_subscriptions, user_preferences, users RESTART IDENTITY CASCADE"
            )
        conn.commit()
    yield PostgresStorage(connection_string=migrated_postgres_url)


def _create_user(database_url: str, user_id: UUID) -> None:
    now = datetime.now(tz=UTC)
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, github_login, github_token, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, f"user-{str(user_id)[:8]}", "encrypted-token", now, now),
            )
        conn.commit()


def _record(thread_id: str, score: float) -> NotificationRecord:
    now = datetime.now(tz=UTC)
    return NotificationRecord(
        notification=Notification(
            thread_id=thread_id,
            repository="org/repo",
            reason="mention",
            subject_title=f"Subject {thread_id}",
            subject_type="PullRequest",
            unread=True,
            updated_at=now - timedelta(minutes=5),
            thread_url=f"https://api.github.com/notifications/threads/{thread_id}",
            web_url=f"https://github.com/org/repo/pull/{thread_id}",
        ),
        score=score,
        excluded=False,
        matched_rules=["rule-a"],
        actions_taken=[],
    )


@pytest.mark.integration
def test_save_and_load_records(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    user_id = uuid4()
    _create_user(migrated_postgres_url, user_id)
    now = datetime.now(tz=UTC)
    input_records = [_record("t1", SCORE_HIGH), _record("t2", SCORE_LOW)]

    storage.save_records(user_id=user_id, records=input_records, generated_at=now)
    generated_at, loaded = storage.load_records(user_id=user_id)

    assert generated_at == now
    assert {r.notification.thread_id for r in loaded} == {"t1", "t2"}
    by_id = {r.notification.thread_id: r for r in loaded}
    assert by_id["t1"].score == SCORE_HIGH
    assert by_id["t2"].score == SCORE_LOW


@pytest.mark.integration
def test_save_records_upsert_preserves_dismissed(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    user_id = uuid4()
    _create_user(migrated_postgres_url, user_id)
    first_snapshot = datetime.now(tz=UTC) - timedelta(minutes=1)
    second_snapshot = datetime.now(tz=UTC)

    storage.save_records(user_id=user_id, records=[_record("t1", 1.0)], generated_at=first_snapshot)
    storage.dismiss_record(user_id=user_id, thread_id="t1")
    storage.save_records(user_id=user_id, records=[_record("t1", SCORE_UPDATED)], generated_at=second_snapshot)

    _, loaded = storage.load_records(user_id=user_id)
    assert len(loaded) == 1
    assert loaded[0].notification.thread_id == "t1"
    assert loaded[0].score == SCORE_UPDATED
    assert loaded[0].dismissed is True


@pytest.mark.integration
def test_load_records_empty_returns_none_and_empty(storage: PostgresStorage) -> None:
    generated_at, loaded = storage.load_records(user_id=uuid4())

    assert generated_at is None
    assert loaded == []


@pytest.mark.integration
def test_dismiss_record_updates_flag(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    user_id = uuid4()
    _create_user(migrated_postgres_url, user_id)
    storage.save_records(
        user_id=user_id,
        records=[_record("t1", 2.0), _record("t2", 3.0)],
        generated_at=datetime.now(tz=UTC),
    )

    storage.dismiss_record(user_id=user_id, thread_id="t2")
    _, loaded = storage.load_records(user_id=user_id)
    by_id = {record.notification.thread_id: record for record in loaded}

    assert by_id["t1"].dismissed is False
    assert by_id["t2"].dismissed is True


@pytest.mark.integration
def test_get_dismissed_thread_ids(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    user_id = uuid4()
    _create_user(migrated_postgres_url, user_id)
    storage.save_records(
        user_id=user_id,
        records=[_record("t1", 2.0), _record("t2", 3.0), _record("t3", 4.0)],
        generated_at=datetime.now(tz=UTC),
    )
    storage.dismiss_record(user_id=user_id, thread_id="t1")
    storage.dismiss_record(user_id=user_id, thread_id="t3")

    dismissed_ids = storage.get_dismissed_thread_ids(user_id=user_id)

    assert set(dismissed_ids) == {"t1", "t3"}


@pytest.mark.integration
def test_mark_record_read_updates_unread_flag(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    user_id = uuid4()
    _create_user(migrated_postgres_url, user_id)
    storage.save_records(
        user_id=user_id,
        records=[_record("t1", 2.0), _record("t2", 3.0)],
        generated_at=datetime.now(tz=UTC),
    )

    storage.mark_record_read(user_id=user_id, thread_id="t2")
    _, loaded = storage.load_records(user_id=user_id)
    by_id = {record.notification.thread_id: record for record in loaded}

    assert by_id["t1"].notification.unread is True
    assert by_id["t2"].notification.unread is False


@pytest.mark.integration
def test_records_scoped_to_user(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    first_user = uuid4()
    second_user = uuid4()
    _create_user(migrated_postgres_url, first_user)
    _create_user(migrated_postgres_url, second_user)
    now = datetime.now(tz=UTC)

    storage.save_records(user_id=first_user, records=[_record("a1", 1.0)], generated_at=now)
    storage.save_records(user_id=second_user, records=[_record("b1", 2.0)], generated_at=now)

    _, first_user_records = storage.load_records(user_id=first_user)
    _, second_user_records = storage.load_records(user_id=second_user)

    assert [record.notification.thread_id for record in first_user_records] == ["a1"]
    assert [record.notification.thread_id for record in second_user_records] == ["b1"]


@pytest.mark.integration
def test_ordering_by_snapshot_then_score(migrated_postgres_url: str, storage: PostgresStorage) -> None:
    user_id = uuid4()
    _create_user(migrated_postgres_url, user_id)
    old_snapshot = datetime.now(tz=UTC) - timedelta(hours=2)
    new_snapshot = datetime.now(tz=UTC) - timedelta(hours=1)

    storage.save_records(user_id=user_id, records=[_record("old-high", 999.0)], generated_at=old_snapshot)
    storage.save_records(
        user_id=user_id,
        records=[_record("new-low", 1.0), _record("new-high", 100.0)],
        generated_at=new_snapshot,
    )

    _, loaded = storage.load_records(user_id=user_id)

    assert [record.notification.thread_id for record in loaded] == ["new-high", "new-low", "old-high"]
