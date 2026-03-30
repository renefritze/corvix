"""Domain models for GitHub notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


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

    @classmethod
    def from_api_payload(cls, payload: dict[str, object]) -> Notification:
        """Build a notification from a GitHub API response payload."""
        subject = payload.get("subject")
        repository = payload.get("repository")
        if not isinstance(subject, dict):
            msg = "Invalid notification payload: missing subject map."
            raise ValueError(msg)
        if not isinstance(repository, dict):
            msg = "Invalid notification payload: missing repository map."
            raise ValueError(msg)

        thread_id = str(payload.get("id", ""))
        if not thread_id:
            msg = "Invalid notification payload: missing thread id."
            raise ValueError(msg)

        updated = payload.get("updated_at")
        if not isinstance(updated, str):
            msg = "Invalid notification payload: missing updated_at timestamp."
            raise ValueError(msg)

        repo_name = repository.get("full_name")
        if not isinstance(repo_name, str):
            msg = "Invalid notification payload: missing repository.full_name."
            raise ValueError(msg)

        reason = payload.get("reason")
        if not isinstance(reason, str):
            msg = "Invalid notification payload: missing reason."
            raise ValueError(msg)

        subject_title = subject.get("title")
        if not isinstance(subject_title, str):
            msg = "Invalid notification payload: missing subject.title."
            raise ValueError(msg)

        subject_type = subject.get("type")
        if not isinstance(subject_type, str):
            msg = "Invalid notification payload: missing subject.type."
            raise ValueError(msg)

        unread = payload.get("unread", False)
        if not isinstance(unread, bool):
            unread = bool(unread)

        thread_url = payload.get("url")
        thread_url_str = thread_url if isinstance(thread_url, str) else None

        return cls(
            thread_id=thread_id,
            repository=repo_name,
            reason=reason,
            subject_title=subject_title,
            subject_type=subject_type,
            unread=unread,
            updated_at=parse_timestamp(updated),
            thread_url=thread_url_str,
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

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "thread_id": self.notification.thread_id,
            "repository": self.notification.repository,
            "reason": self.notification.reason,
            "subject_title": self.notification.subject_title,
            "subject_type": self.notification.subject_type,
            "unread": self.notification.unread,
            "updated_at": format_timestamp(self.notification.updated_at),
            "thread_url": self.notification.thread_url,
            "score": self.score,
            "excluded": self.excluded,
            "matched_rules": self.matched_rules,
            "actions_taken": self.actions_taken,
            "dismissed": self.dismissed,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> NotificationRecord:
        """Parse a stored record."""
        updated_at = payload.get("updated_at")
        if not isinstance(updated_at, str):
            msg = "Invalid stored record: missing updated_at."
            raise ValueError(msg)

        notification = Notification(
            thread_id=str(payload.get("thread_id", "")),
            repository=str(payload.get("repository", "")),
            reason=str(payload.get("reason", "")),
            subject_title=str(payload.get("subject_title", "")),
            subject_type=str(payload.get("subject_type", "")),
            unread=bool(payload.get("unread", False)),
            updated_at=parse_timestamp(updated_at),
            thread_url=payload.get("thread_url") if isinstance(payload.get("thread_url"), str) else None,
        )
        return cls(
            notification=notification,
            score=float(payload.get("score", 0.0)),
            excluded=bool(payload.get("excluded", False)),
            matched_rules=[value for value in payload.get("matched_rules", []) if isinstance(value, str)],
            actions_taken=[value for value in payload.get("actions_taken", []) if isinstance(value, str)],
            dismissed=bool(payload.get("dismissed", False)),
        )
