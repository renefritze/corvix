"""Tests for storage backends and StorageBackend protocol conformance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import get_protocol_members

from corvix.config import load_config
from corvix.domain import Notification, NotificationRecord
from corvix.storage import NotificationCache, StorageBackend


def _make_record(thread_id: str, dismissed: bool = False) -> NotificationRecord:
    now = datetime.now(tz=UTC)
    notification = Notification(
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="Test PR",
        subject_type="PullRequest",
        unread=True,
        updated_at=now - timedelta(hours=1),
    )
    return NotificationRecord(notification=notification, score=10.0, excluded=False, dismissed=dismissed)


def _cache(path: Path) -> NotificationCache:
    return NotificationCache(path=path / "notifications.json")


# --- StorageBackend protocol ---


def test_notification_cache_implements_storage_backend(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    # Runtime check: all protocol methods exist and are callable
    assert callable(cache.save_records)
    assert callable(cache.load_records)
    assert callable(cache.dismiss_record)
    assert callable(cache.get_dismissed_thread_ids)


def test_storage_backend_is_protocol() -> None:
    members = get_protocol_members(StorageBackend)
    assert "save_records" in members
    assert "load_records" in members
    assert "dismiss_record" in members
    assert "get_dismissed_thread_ids" in members


# --- NotificationCache StorageBackend methods ---


def test_save_and_load_records_via_protocol(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    records = [_make_record("1"), _make_record("2")]
    now = datetime.now(tz=UTC)
    cache.save_records(user_id="ignored", records=records, generated_at=now)
    generated_at, loaded = cache.load_records(user_id="ignored")
    assert generated_at is not None
    assert len(loaded) == 2  # noqa: PLR2004
    assert {r.notification.thread_id for r in loaded} == {"1", "2"}


def test_dismiss_record_sets_flag(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    records = [_make_record("1"), _make_record("2")]
    now = datetime.now(tz=UTC)
    cache.save_records(user_id="u", records=records, generated_at=now)

    cache.dismiss_record(user_id="u", thread_id="1")

    _, loaded = cache.load_records(user_id="u")
    by_id = {r.notification.thread_id: r for r in loaded}
    assert by_id["1"].dismissed is True
    assert by_id["2"].dismissed is False


def test_get_dismissed_thread_ids(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    records = [_make_record("1", dismissed=True), _make_record("2")]
    cache.save_records(user_id="u", records=records, generated_at=datetime.now(tz=UTC))

    dismissed = cache.get_dismissed_thread_ids(user_id="u")
    assert dismissed == ["1"]


def test_dismiss_nonexistent_thread_is_noop(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    records = [_make_record("1")]
    cache.save_records(user_id="u", records=records, generated_at=datetime.now(tz=UTC))
    # Should not raise
    cache.dismiss_record(user_id="u", thread_id="does-not-exist")
    _, loaded = cache.load_records(user_id="u")
    assert not loaded[0].dismissed


# --- dismissed field on NotificationRecord ---


def test_dismissed_field_defaults_false() -> None:
    record = _make_record("x")
    assert record.dismissed is False


def test_dismissed_round_trips_through_dict() -> None:
    record = _make_record("x", dismissed=True)
    as_dict = record.to_dict()
    assert as_dict["dismissed"] is True
    restored = NotificationRecord.from_dict(as_dict)
    assert restored.dismissed is True


def test_dismissed_false_round_trips_through_dict() -> None:
    record = _make_record("x", dismissed=False)
    as_dict = record.to_dict()
    assert as_dict["dismissed"] is False
    restored = NotificationRecord.from_dict(as_dict)
    assert restored.dismissed is False


def test_from_dict_without_dismissed_defaults_false() -> None:
    """Old cache files without 'dismissed' key should load as dismissed=False."""
    record = _make_record("x")
    as_dict = record.to_dict()
    del as_dict["dismissed"]
    restored = NotificationRecord.from_dict(as_dict)
    assert restored.dismissed is False


# --- config new sections ---


def test_config_parses_auth_and_database_sections(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
github:
  token_env: GITHUB_TOKEN
auth:
  mode: multi_user
  session_secret: supersecret
database:
  url_env: DATABASE_URL
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.auth.mode == "multi_user"
    assert config.auth.session_secret == "supersecret"
    assert config.database.url_env == "DATABASE_URL"


def test_config_auth_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("github:\n  token_env: GITHUB_TOKEN\n", encoding="utf-8")
    config = load_config(config_file)
    assert config.auth.mode == "single_user"
    assert config.auth.session_secret == ""
    assert config.database.url_env == "DATABASE_URL"
