"""Tests for domain model construction, parsing, and serialization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from corvix.domain import (
    Notification,
    NotificationRecord,
    format_timestamp,
    parse_timestamp,
)

# --- parse_timestamp ---


def test_parse_timestamp_z_suffix() -> None:
    ts = parse_timestamp("2024-01-15T12:30:00Z")
    assert ts.year == 2024
    assert ts.month == 1
    assert ts.day == 15
    assert ts.tzinfo is not None
    offset = ts.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0


def test_parse_timestamp_plus_offset() -> None:
    ts = parse_timestamp("2024-01-15T12:30:00+00:00")
    assert ts.tzinfo is not None


def test_parse_timestamp_naive_gets_utc() -> None:
    ts = parse_timestamp("2024-01-15T12:30:00")
    assert ts.tzinfo == UTC


# --- format_timestamp ---


def test_format_timestamp_produces_z_suffix() -> None:
    dt = datetime(2024, 1, 15, 12, 30, 0, tzinfo=UTC)
    result = format_timestamp(dt)
    assert result.endswith("Z")
    assert "2024-01-15" in result


def test_format_parse_round_trip() -> None:
    original = datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)
    assert parse_timestamp(format_timestamp(original)) == original


# --- Notification.from_api_payload ---


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "123",
        "updated_at": "2024-01-15T12:30:00Z",
        "reason": "mention",
        "unread": True,
        "url": "https://api.github.com/notifications/threads/123",
        "subject": {
            "title": "Fix the bug",
            "type": "PullRequest",
            "url": "https://api.github.com/repos/org/repo/pulls/42",
        },
        "repository": {
            "full_name": "org/repo",
            "html_url": "https://github.com/org/repo",
        },
    }
    payload.update(overrides)
    return payload


def test_from_api_payload_valid() -> None:
    n = Notification.from_api_payload(_valid_payload())
    assert n.thread_id == "123"
    assert n.repository == "org/repo"
    assert n.reason == "mention"
    assert n.subject_title == "Fix the bug"
    assert n.subject_type == "PullRequest"
    assert n.unread is True
    assert n.thread_url == "https://api.github.com/notifications/threads/123"


def test_from_api_payload_preserves_subject_url() -> None:
    n = Notification.from_api_payload(_valid_payload())
    assert n.subject_url == "https://api.github.com/repos/org/repo/pulls/42"


def test_from_api_payload_defaults_web_url_to_none() -> None:
    n = Notification.from_api_payload(_valid_payload())
    assert n.web_url is None


def test_from_api_payload_preserves_repository_url() -> None:
    n = Notification.from_api_payload(_valid_payload())
    assert n.repository_url == "https://github.com/org/repo"


def test_from_api_payload_missing_repository_url_defaults_none() -> None:
    payload = _valid_payload(repository={"full_name": "org/repo"})
    n = Notification.from_api_payload(payload)
    assert n.repository_url is None


def test_from_api_payload_missing_subject_raises() -> None:
    payload = _valid_payload()
    del payload["subject"]
    with pytest.raises(ValueError, match="missing subject"):
        Notification.from_api_payload(payload)


def test_from_api_payload_subject_not_dict_raises() -> None:
    payload = _valid_payload(subject="not a dict")
    with pytest.raises(ValueError, match="missing subject"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_repository_raises() -> None:
    payload = _valid_payload()
    del payload["repository"]
    with pytest.raises(ValueError, match="missing repository"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_id_raises() -> None:
    payload = _valid_payload()
    del payload["id"]
    with pytest.raises(ValueError, match="missing thread id"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_updated_at_raises() -> None:
    payload = _valid_payload()
    del payload["updated_at"]
    with pytest.raises(ValueError, match="missing updated_at"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_repo_full_name_raises() -> None:
    payload = _valid_payload(repository={"id": 1})
    with pytest.raises(ValueError, match=r"missing repository\.full_name"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_reason_raises() -> None:
    payload = _valid_payload()
    del payload["reason"]
    with pytest.raises(ValueError, match="missing reason"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_subject_title_raises() -> None:
    payload = _valid_payload(subject={"type": "PullRequest"})
    with pytest.raises(ValueError, match=r"missing subject\.title"):
        Notification.from_api_payload(payload)


def test_from_api_payload_missing_subject_type_raises() -> None:
    payload = _valid_payload(subject={"title": "Fix it"})
    with pytest.raises(ValueError, match=r"missing subject\.type"):
        Notification.from_api_payload(payload)


def test_from_api_payload_no_thread_url() -> None:
    payload = _valid_payload()
    del payload["url"]
    n = Notification.from_api_payload(payload)
    assert n.thread_url is None


def test_from_api_payload_invalid_unread_type_raises() -> None:
    payload = _valid_payload(unread=1)
    with pytest.raises(ValueError, match="field 'unread' must be a boolean"):
        Notification.from_api_payload(payload)


# --- NotificationRecord to_dict / from_dict ---


def _make_record(thread_id: str = "1", dismissed: bool = False) -> NotificationRecord:
    n = Notification(
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="Test",
        subject_type="PullRequest",
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        web_url="https://github.com/org/repo/pull/1",
    )
    return NotificationRecord(
        notification=n,
        score=5.0,
        excluded=False,
        dismissed=dismissed,
        context={"github": {"latest_comment": {"is_ci_only": True}}},
    )


def test_to_dict_from_dict_round_trip() -> None:
    record = _make_record()
    restored = NotificationRecord.from_dict(record.to_dict())
    assert restored.notification.thread_id == record.notification.thread_id
    assert restored.notification.web_url == record.notification.web_url
    assert restored.score == record.score
    assert restored.excluded == record.excluded
    assert restored.dismissed == record.dismissed
    assert restored.context == record.context


def test_dismissed_true_round_trips() -> None:
    assert NotificationRecord.from_dict(_make_record(dismissed=True).to_dict()).dismissed is True


def test_dismissed_false_round_trips() -> None:
    assert NotificationRecord.from_dict(_make_record(dismissed=False).to_dict()).dismissed is False


def test_from_dict_without_dismissed_defaults_false() -> None:
    as_dict = _make_record().to_dict()
    del as_dict["dismissed"]
    assert NotificationRecord.from_dict(as_dict).dismissed is False


def test_from_dict_without_web_url_is_none() -> None:
    as_dict = _make_record().to_dict()
    del as_dict["web_url"]
    assert NotificationRecord.from_dict(as_dict).notification.web_url is None


def test_subject_url_round_trips() -> None:
    n = Notification(
        thread_id="1",
        repository="org/repo",
        reason="mention",
        subject_title="Test",
        subject_type="CheckSuite",
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        subject_url="https://api.github.com/repos/org/repo/check-suites/555",
    )
    record = NotificationRecord(notification=n, score=1.0, excluded=False)
    restored = NotificationRecord.from_dict(record.to_dict())
    assert restored.notification.subject_url == "https://api.github.com/repos/org/repo/check-suites/555"


def test_repository_url_round_trips() -> None:
    n = Notification(
        thread_id="1",
        repository="org/repo",
        repository_url="https://github.example.com/org/repo",
        reason="mention",
        subject_title="Test",
        subject_type="Issue",
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    record = NotificationRecord(notification=n, score=1.0, excluded=False)
    restored = NotificationRecord.from_dict(record.to_dict())
    assert restored.notification.repository_url == "https://github.example.com/org/repo"


def test_from_dict_without_subject_url_is_none() -> None:
    as_dict = _make_record().to_dict()
    del as_dict["subject_url"]
    assert NotificationRecord.from_dict(as_dict).notification.subject_url is None


def test_from_dict_without_context_defaults_empty_dict() -> None:
    as_dict = _make_record().to_dict()
    del as_dict["context"]
    assert NotificationRecord.from_dict(as_dict).context == {}


def test_from_dict_missing_updated_at_raises() -> None:
    payload = _make_record().to_dict()
    del payload["updated_at"]

    with pytest.raises(ValueError, match="missing updated_at"):
        NotificationRecord.from_dict(payload)
