"""Domain models for GitHub notifications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypedDict


class PollerStatus(TypedDict, total=False):
    """Status written to the cache by the poller/watch loop."""

    status: str
    last_poll_time: str | None
    last_error: str | None
    last_error_time: str | None


STORED_RECORD_LABEL = "stored record"


def _as_object_map(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    output: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def _require_non_empty_str(payload: Mapping[str, object], key: str, label: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    msg = f"Invalid {label}: missing {key}."
    raise ValueError(msg)


def _optional_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    msg = f"Invalid {STORED_RECORD_LABEL}: field '{key}' must be a string or null."
    raise ValueError(msg)


def _optional_bool(payload: Mapping[str, object], key: str, default: bool, label: str) -> bool:
    if key not in payload:
        return default
    value = payload[key]
    if isinstance(value, bool):
        return value
    msg = f"Invalid {label}: field '{key}' must be a boolean."
    raise ValueError(msg)


def _optional_float(payload: Mapping[str, object], key: str, default: float, label: str) -> float:
    if key not in payload:
        return default
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"Invalid {label}: field '{key}' must be a number."
        raise ValueError(msg)
    return float(value)


def _optional_str_list(payload: Mapping[str, object], key: str) -> list[str]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        msg = f"Invalid {STORED_RECORD_LABEL}: field '{key}' must be a list of strings."
        raise ValueError(msg)
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = f"Invalid {STORED_RECORD_LABEL}: field '{key}' must be a list of strings."
            raise ValueError(msg)
        output.append(item)
    return output


def _optional_context(payload: Mapping[str, object], key: str) -> dict[str, object]:
    value = payload.get(key, {})
    context = _as_object_map(value)
    if context is None:
        msg = f"Invalid {STORED_RECORD_LABEL}: field '{key}' must be an object."
        raise ValueError(msg)
    return context


def _require_object_map(value: object, message: str) -> dict[str, object]:
    object_map = _as_object_map(value)
    if object_map is not None:
        return object_map
    raise ValueError(message)


def _require_non_empty_str_value(value: object, message: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(message)


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO8601 timestamp into a timezone-aware datetime."""
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def format_timestamp(value: datetime) -> str:
    """Format a timezone-aware datetime as an ISO8601 string."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class Notification:
    """Normalized notification from GitHub's notifications API."""

    thread_id: str
    repository: str
    reason: str
    subject_title: str
    subject_type: str
    unread: bool
    updated_at: datetime
    thread_url: str | None = None
    subject_url: str | None = None
    web_url: str | None = None
    account_id: str = "primary"
    account_label: str = "Primary"

    @classmethod
    def from_api_payload(
        cls,
        payload: Mapping[str, object],
        *,
        account_id: str = "primary",
        account_label: str = "Primary",
    ) -> Notification:
        """Build a notification from a GitHub API response payload."""
        subject = _require_object_map(
            payload.get("subject"),
            "Invalid notification payload: missing subject map.",
        )
        repository = _require_object_map(
            payload.get("repository"),
            "Invalid notification payload: missing repository map.",
        )

        thread_id = _require_non_empty_str_value(
            payload.get("id"),
            "Invalid notification payload: missing thread id.",
        )

        updated = _require_non_empty_str_value(
            payload.get("updated_at"),
            "Invalid notification payload: missing updated_at timestamp.",
        )

        repo_name = _require_non_empty_str_value(
            repository.get("full_name"),
            "Invalid notification payload: missing repository.full_name.",
        )

        reason = _require_non_empty_str_value(
            payload.get("reason"),
            "Invalid notification payload: missing reason.",
        )

        subject_title = _require_non_empty_str_value(
            subject.get("title"),
            "Invalid notification payload: missing subject.title.",
        )

        subject_type = _require_non_empty_str_value(
            subject.get("type"),
            "Invalid notification payload: missing subject.type.",
        )

        unread = _optional_bool(payload, "unread", False, "notification payload")

        thread_url = payload.get("url")
        thread_url_str = thread_url if isinstance(thread_url, str) else None
        subject_url_raw = subject.get("url")
        subject_url_str = subject_url_raw if isinstance(subject_url_raw, str) else None
        return cls(
            account_id=account_id,
            account_label=account_label,
            thread_id=thread_id,
            repository=repo_name,
            reason=reason,
            subject_title=subject_title,
            subject_type=subject_type,
            unread=unread,
            updated_at=parse_timestamp(updated),
            thread_url=thread_url_str,
            subject_url=subject_url_str,
            web_url=None,
        )


@dataclass(slots=True)
class NotificationRecord:
    """Scored and rule-evaluated notification persisted for dashboards."""

    notification: Notification
    score: float
    excluded: bool
    matched_rules: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    dismissed: bool = False
    context: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "account_id": self.notification.account_id,
            "account_label": self.notification.account_label,
            "thread_id": self.notification.thread_id,
            "repository": self.notification.repository,
            "reason": self.notification.reason,
            "subject_title": self.notification.subject_title,
            "subject_type": self.notification.subject_type,
            "unread": self.notification.unread,
            "updated_at": format_timestamp(self.notification.updated_at),
            "thread_url": self.notification.thread_url,
            "subject_url": self.notification.subject_url,
            "web_url": self.notification.web_url,
            "score": self.score,
            "excluded": self.excluded,
            "matched_rules": self.matched_rules,
            "actions_taken": self.actions_taken,
            "dismissed": self.dismissed,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> NotificationRecord:
        """Parse a stored record."""
        updated_at = _require_non_empty_str(payload, "updated_at", STORED_RECORD_LABEL)
        notification = Notification(
            account_id=_get_non_empty_str_or_default(payload, "account_id", "primary"),
            account_label=_get_non_empty_str_or_default(payload, "account_label", "Primary"),
            thread_id=_require_non_empty_str(payload, "thread_id", STORED_RECORD_LABEL),
            repository=_require_non_empty_str(payload, "repository", STORED_RECORD_LABEL),
            reason=_require_non_empty_str(payload, "reason", STORED_RECORD_LABEL),
            subject_title=_require_non_empty_str(payload, "subject_title", STORED_RECORD_LABEL),
            subject_type=_require_non_empty_str(payload, "subject_type", STORED_RECORD_LABEL),
            unread=_optional_bool(payload, "unread", False, STORED_RECORD_LABEL),
            updated_at=parse_timestamp(updated_at),
            thread_url=_optional_str(payload, "thread_url"),
            subject_url=_optional_str(payload, "subject_url"),
            web_url=_optional_str(payload, "web_url"),
        )
        return cls(
            notification=notification,
            score=_optional_float(payload, "score", 0.0, STORED_RECORD_LABEL),
            excluded=_optional_bool(payload, "excluded", False, STORED_RECORD_LABEL),
            matched_rules=_optional_str_list(payload, "matched_rules"),
            actions_taken=_optional_str_list(payload, "actions_taken"),
            dismissed=_optional_bool(payload, "dismissed", False, STORED_RECORD_LABEL),
            context=_optional_context(payload, "context"),
        )


def notification_key(notification: Notification) -> str:
    """Return a stable account-scoped key for a notification."""
    return f"{notification.account_id}:{notification.thread_id}"


def _get_non_empty_str_or_default(payload: Mapping[str, object], key: str, default: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return default
