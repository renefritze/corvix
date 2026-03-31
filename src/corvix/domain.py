"""Domain models for GitHub notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlparse

_MIN_API_REPO_SEGMENTS = 4
_MIN_RESOURCE_SEGMENTS = 2
_RELEASE_TAG_SEGMENTS = 3
_API_RESOURCE_TO_WEB_PATH = {
    "pulls": "pull",
    "issues": "issues",
    "commits": "commit",
    "compare": "compare",
    "discussions": "discussions",
}


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
    web_url: str | None = None

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
        subject = cast(dict[str, object], subject)
        repository = cast(dict[str, object], repository)

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
        web_url = _derive_web_url(payload)

        return cls(
            thread_id=thread_id,
            repository=repo_name,
            reason=reason,
            subject_title=subject_title,
            subject_type=subject_type,
            unread=unread,
            updated_at=parse_timestamp(updated),
            thread_url=thread_url_str,
            web_url=web_url,
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
            "web_url": self.notification.web_url,
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

        p: dict[str, Any] = cast(dict[str, Any], payload)
        thread_url_raw = p.get("thread_url")
        web_url_raw = p.get("web_url")
        matched_rules_raw = p.get("matched_rules", [])
        actions_taken_raw = p.get("actions_taken", [])
        notification = Notification(
            thread_id=str(p.get("thread_id", "")),
            repository=str(p.get("repository", "")),
            reason=str(p.get("reason", "")),
            subject_title=str(p.get("subject_title", "")),
            subject_type=str(p.get("subject_type", "")),
            unread=bool(p.get("unread", False)),
            updated_at=parse_timestamp(updated_at),
            thread_url=thread_url_raw if isinstance(thread_url_raw, str) else None,
            web_url=web_url_raw if isinstance(web_url_raw, str) else None,
        )
        return cls(
            notification=notification,
            score=float(p.get("score", 0.0)),
            excluded=bool(p.get("excluded", False)),
            matched_rules=[value for value in matched_rules_raw if isinstance(value, str)],
            actions_taken=[value for value in actions_taken_raw if isinstance(value, str)],
            dismissed=bool(p.get("dismissed", False)),
        )


def _derive_web_url(payload: dict[str, object]) -> str | None:
    subject = payload.get("subject")
    repository = payload.get("repository")
    if not isinstance(subject, dict) or not isinstance(repository, dict):
        return None
    subject = cast(dict[str, object], subject)
    repository = cast(dict[str, object], repository)

    repo_name = repository.get("full_name")
    if not isinstance(repo_name, str) or not repo_name:
        return None

    repo_web_url = repository.get("html_url")
    repo_base = repo_web_url if isinstance(repo_web_url, str) and repo_web_url else f"https://github.com/{repo_name}"

    subject_url = subject.get("url")
    if not isinstance(subject_url, str) or not subject_url:
        return repo_base

    return _map_subject_api_url_to_web(subject_url=subject_url, repo_name=repo_name, repo_base=repo_base) or repo_base


def _map_subject_api_url_to_web(subject_url: str, repo_name: str, repo_base: str) -> str | None:
    parsed = urlparse(subject_url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if len(path_segments) < _MIN_API_REPO_SEGMENTS or path_segments[0] != "repos":
        return None

    api_repo_name = "/".join(path_segments[1:3])
    if api_repo_name != repo_name:
        return None

    resource = path_segments[3:]
    resource_name = resource[0]
    mapped_web_path = _API_RESOURCE_TO_WEB_PATH.get(resource_name)
    if mapped_web_path is not None and len(resource) >= _MIN_RESOURCE_SEGMENTS:
        return f"{repo_base}/{mapped_web_path}/{resource[1]}"
    if resource_name == "releases" and len(resource) >= _RELEASE_TAG_SEGMENTS and resource[1] == "tags":
        return f"{repo_base}/releases/tag/{resource[2]}"
    return None
