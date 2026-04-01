"""Tests for NotificationCache and StorageBackend protocol conformance."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import get_protocol_members

import pytest
from pytest import MonkeyPatch

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
    return NotificationRecord(
        notification=notification,
        score=10.0,
        excluded=False,
        dismissed=dismissed,
        context={"github": {"latest_comment": {"is_ci_only": True}}},
    )


def _cache(path: Path) -> NotificationCache:
    return NotificationCache(path=path / "notifications.json")


# --- StorageBackend protocol ---


def test_notification_cache_implements_storage_backend(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    assert callable(cache.save_records)
    assert callable(cache.load_records)
    assert callable(cache.dismiss_record)
    assert callable(cache.mark_record_read)
    assert callable(cache.get_dismissed_thread_ids)


def test_storage_backend_is_protocol() -> None:
    members = get_protocol_members(StorageBackend)
    assert "save_records" in members
    assert "load_records" in members
    assert "dismiss_record" in members
    assert "mark_record_read" in members
    assert "get_dismissed_thread_ids" in members


# --- NotificationCache save/load ---


def test_save_and_load_records_via_protocol(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    records = [_make_record("1"), _make_record("2")]
    now = datetime.now(tz=UTC)
    cache.save_records(user_id="ignored", records=records, generated_at=now)
    generated_at, loaded = cache.load_records(user_id="ignored")
    assert generated_at is not None
    assert len(loaded) == 2
    assert {r.notification.thread_id for r in loaded} == {"1", "2"}
    assert loaded[0].context


def test_load_returns_empty_when_no_file(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    generated_at, records = cache.load()
    assert generated_at is None
    assert records == []


def test_save_creates_parent_directories(tmp_path: Path) -> None:
    deep_path = tmp_path / "a" / "b" / "c" / "notifications.json"
    cache = NotificationCache(path=deep_path)
    cache.save([_make_record("1")], generated_at=datetime.now(tz=UTC))
    assert deep_path.exists()


def test_save_is_valid_json_after_repeated_writes(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    for index in range(10):
        cache.save([_make_record(str(index))], generated_at=datetime.now(tz=UTC))
        parsed = json.loads(cache.path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)
        assert isinstance(parsed.get("notifications"), list)


def test_save_uses_atomic_replace(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    cache = _cache(tmp_path)
    cache.save([_make_record("initial")], generated_at=datetime.now(tz=UTC))

    replace_calls: list[tuple[Path, Path]] = []
    original_replace = Path.replace

    def _spy_replace(source: Path, target: Path) -> Path:
        replace_calls.append((source, target))
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", _spy_replace)

    cache.save([_make_record("next")], generated_at=datetime.now(tz=UTC))

    assert len(replace_calls) == 1
    source, target = replace_calls[0]
    assert target == cache.path
    assert source != cache.path
    assert source.parent == cache.path.parent


def test_save_keeps_target_valid_until_replace(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    cache = _cache(tmp_path)
    cache.save([_make_record("old")], generated_at=datetime.now(tz=UTC))
    previous_payload = json.loads(cache.path.read_text(encoding="utf-8"))

    original_replace = Path.replace

    def _assert_old_file_still_valid(source: Path, target: Path) -> Path:
        current_target_payload = json.loads(target.read_text(encoding="utf-8"))
        assert current_target_payload == previous_payload
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", _assert_old_file_still_valid)

    cache.save([_make_record("new")], generated_at=datetime.now(tz=UTC))
    _, loaded = cache.load()
    assert len(loaded) == 1
    assert loaded[0].notification.thread_id == "new"


# --- dismiss_record ---


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
    cache.save_records(
        user_id="u",
        records=[_make_record("1", dismissed=True), _make_record("2")],
        generated_at=datetime.now(tz=UTC),
    )
    assert cache.get_dismissed_thread_ids(user_id="u") == ["1"]


def test_dismiss_nonexistent_thread_is_noop(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.save_records(user_id="u", records=[_make_record("1")], generated_at=datetime.now(tz=UTC))
    cache.dismiss_record(user_id="u", thread_id="does-not-exist")
    _, loaded = cache.load_records(user_id="u")
    assert not loaded[0].dismissed


def test_dismissed_field_defaults_false() -> None:
    assert _make_record("x").dismissed is False


def test_mark_record_read_sets_unread_false(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    records = [_make_record("1"), _make_record("2")]
    cache.save_records(user_id="u", records=records, generated_at=datetime.now(tz=UTC))

    cache.mark_record_read(user_id="u", thread_id="1")

    _, loaded = cache.load_records(user_id="u")
    by_id = {r.notification.thread_id: r for r in loaded}
    assert by_id["1"].notification.unread is False
    assert by_id["2"].notification.unread is True


def test_mark_record_read_nonexistent_thread_is_noop(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.save_records(user_id="u", records=[_make_record("1")], generated_at=datetime.now(tz=UTC))

    cache.mark_record_read(user_id="u", thread_id="does-not-exist")

    _, loaded = cache.load_records(user_id="u")
    assert loaded[0].notification.unread is True


def test_load_invalid_format_not_dict(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.path.write_text('"hello"', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid cache file format"):
        cache.load()


def test_load_invalid_notifications_not_list(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.path.write_text('{"generated_at":"2024-01-01T00:00:00Z","notifications":"bad"}', encoding="utf-8")

    with pytest.raises(ValueError, match="'notifications' must be a list"):
        cache.load()


def test_load_generated_at_non_string_is_none(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.path.write_text('{"generated_at":123,"notifications":[]}', encoding="utf-8")

    generated_at, records = cache.load()

    assert generated_at is None
    assert records == []
