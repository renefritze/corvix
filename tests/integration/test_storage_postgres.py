"""PostgreSQL integration tests for PostgresStorage."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from corvix.config import AppConfig
from corvix.domain import Notification, NotificationRecord, PollerStatus
from corvix.storage import PostgresStorage, StorageConfigError, create_storage

SCORE_HIGH = 50.0
SCORE_LOW = 10.0
SCORE_UPDATED = 99.0


@pytest.fixture(scope="session")
def postgres_urls() -> Generator[tuple[str, str]]:
    testcontainers = pytest.importorskip("testcontainers.postgres")
    try:
        container = testcontainers.PostgresContainer("postgres:16-alpine")
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
            cur.execute("TRUNCATE TABLE notification_records RESTART IDENTITY CASCADE")
            cur.execute("DELETE FROM poller_status")
        conn.commit()
    with PostgresStorage(connection_string=migrated_postgres_url) as pg_storage:
        yield pg_storage


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
        matched_rules=("rule-a",),
        actions_taken=(),
        context={"github": {"latest_comment": {"is_ci_only": False}}},
    )


@pytest.mark.integration
def test_save_and_load_records(storage: PostgresStorage) -> None:
    now = datetime.now(tz=UTC)
    input_records = [_record("t1", SCORE_HIGH), _record("t2", SCORE_LOW)]

    storage.save_records(records=input_records, generated_at=now)
    generated_at, loaded = storage.load_records()

    assert generated_at == now
    assert {r.notification.thread_id for r in loaded} == {"t1", "t2"}
    by_id = {r.notification.thread_id: r for r in loaded}
    assert by_id["t1"].score == SCORE_HIGH
    assert by_id["t2"].score == SCORE_LOW
    assert by_id["t1"].context == {"github": {"latest_comment": {"is_ci_only": False}}}


@pytest.mark.integration
def test_save_records_upsert_preserves_dismissed(storage: PostgresStorage) -> None:
    first_snapshot = datetime.now(tz=UTC) - timedelta(minutes=1)
    second_snapshot = datetime.now(tz=UTC)

    storage.save_records(records=[_record("t1", 1.0)], generated_at=first_snapshot)
    storage.dismiss_record(thread_id="t1")
    storage.save_records(records=[_record("t1", SCORE_UPDATED)], generated_at=second_snapshot)

    _, loaded = storage.load_records()
    assert len(loaded) == 1
    assert loaded[0].notification.thread_id == "t1"
    assert loaded[0].score == SCORE_UPDATED
    assert loaded[0].dismissed is True


@pytest.mark.integration
def test_load_records_empty_returns_none_and_empty(storage: PostgresStorage) -> None:
    generated_at, loaded = storage.load_records()

    assert generated_at is None
    assert loaded == []


@pytest.mark.integration
def test_dismiss_record_updates_flag(storage: PostgresStorage) -> None:
    storage.save_records(
        records=[_record("t1", 2.0), _record("t2", 3.0)],
        generated_at=datetime.now(tz=UTC),
    )

    storage.dismiss_record(thread_id="t2")
    _, loaded = storage.load_records()
    by_id = {record.notification.thread_id: record for record in loaded}

    assert by_id["t1"].dismissed is False
    assert by_id["t2"].dismissed is True


@pytest.mark.integration
def test_get_dismissed_thread_ids(storage: PostgresStorage) -> None:
    storage.save_records(
        records=[_record("t1", 2.0), _record("t2", 3.0), _record("t3", 4.0)],
        generated_at=datetime.now(tz=UTC),
    )
    storage.dismiss_record(thread_id="t1")
    storage.dismiss_record(thread_id="t3")

    dismissed_ids = storage.get_dismissed_thread_ids()

    assert set(dismissed_ids) == {"t1", "t3"}


@pytest.mark.integration
def test_mark_record_read_updates_unread_flag(storage: PostgresStorage) -> None:
    storage.save_records(
        records=[_record("t1", 2.0), _record("t2", 3.0)],
        generated_at=datetime.now(tz=UTC),
    )

    storage.mark_record_read(thread_id="t2")
    _, loaded = storage.load_records()
    by_id = {record.notification.thread_id: record for record in loaded}

    assert by_id["t1"].notification.unread is True
    assert by_id["t2"].notification.unread is False


@pytest.mark.integration
def test_ordering_by_snapshot_then_score(storage: PostgresStorage) -> None:
    old_snapshot = datetime.now(tz=UTC) - timedelta(hours=2)
    new_snapshot = datetime.now(tz=UTC) - timedelta(hours=1)

    storage.save_records(records=[_record("old-high", 999.0)], generated_at=old_snapshot)
    storage.save_records(
        records=[_record("new-low", 1.0), _record("new-high", 100.0)],
        generated_at=new_snapshot,
    )

    _, loaded = storage.load_records()

    assert [record.notification.thread_id for record in loaded] == ["new-high", "new-low", "old-high"]


@pytest.mark.integration
def test_load_status_defaults_to_unknown(storage: PostgresStorage) -> None:
    status = storage.load_status()

    assert status.status == "unknown"
    assert status.last_poll_time is None


@pytest.mark.integration
def test_save_and_load_status_roundtrip(storage: PostgresStorage) -> None:
    storage.save_status(
        PollerStatus(status="ok", last_poll_time="2024-01-01T00:00:00Z", last_error=None, last_error_time=None),
    )
    storage.save_status(
        PollerStatus(
            status="error",
            last_poll_time="2024-01-01T00:00:00Z",
            last_error="boom",
            last_error_time="2024-01-02T00:00:00Z",
        ),
    )

    status = storage.load_status()
    assert status.status == "error"
    assert status.last_poll_time == "2024-01-01T00:00:00Z"
    assert status.last_error == "boom"
    assert status.last_error_time == "2024-01-02T00:00:00Z"


@pytest.mark.integration
def test_save_and_load_records_roundtrip(storage: PostgresStorage) -> None:
    storage.save_status(
        PollerStatus(status="ok", last_poll_time="2024-01-01T00:00:00Z", last_error=None, last_error_time=None),
    )
    storage.save_records(records=[_record("t1", SCORE_HIGH)], generated_at=datetime.now(tz=UTC))

    _, loaded = storage.load_records()
    assert [record.notification.thread_id for record in loaded] == ["t1"]
    assert storage.load_status().status == "ok"


@pytest.mark.integration
def test_create_storage_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_FILE", raising=False)

    with pytest.raises(StorageConfigError):
        create_storage(config)
