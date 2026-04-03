"""Domain models for GitHub notifications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlparse

_MIN_API_REPO_SEGMENTS = 4
_MIN_RESOURCE_SEGMENTS = 2
_RELEASE_TAG_SEGMENTS = 3
_ACTIONS_RUNS_SEGMENTS = 3
_API_RESOURCE_TO_WEB_PATH = {
    "pulls": "pull",
    "issues": "issues",
    "commits": "commit",
    "compare": "compare",
    "discussions": "discussions",
}


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
    msg = f"Invalid stored record: field '{key}' must be a string or null."
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
        msg = f"Invalid stored record: field '{key}' must be a list of strings."
        raise ValueError(msg)
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = f"Invalid stored record: field '{key}' must be a list of strings."
            raise ValueError(msg)
        output.append(item)
    return output


def _optional_context(payload: Mapping[str, object], key: str) -> dict[str, object]:
    value = payload.get(key, {})
    context = _as_object_map(value)
    if context is None:
        msg = f"Invalid stored record: field '{key}' must be an object."
        raise ValueError(msg)
    return context


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

    @classmethod
    def from_api_payload(cls, payload: Mapping[str, object]) -> Notification:
        """Build a notification from a GitHub API response payload."""
        subject = _as_object_map(payload.get("subject"))
        repository = _as_object_map(payload.get("repository"))
        if subject is None:
            msg = "Invalid notification payload: missing subject map."
            raise ValueError(msg)
        if repository is None:
            msg = "Invalid notification payload: missing repository map."
            raise ValueError(msg)

        thread_id = payload.get("id")
        if not isinstance(thread_id, str) or not thread_id:
            msg = "Invalid notification payload: missing thread id."
            raise ValueError(msg)

        updated = payload.get("updated_at")
        if not isinstance(updated, str) or not updated:
            msg = "Invalid notification payload: missing updated_at timestamp."
            raise ValueError(msg)

        repo_name = repository.get("full_name")
        if not isinstance(repo_name, str) or not repo_name:
            msg = "Invalid notification payload: missing repository.full_name."
            raise ValueError(msg)

        reason = payload.get("reason")
        if not isinstance(reason, str) or not reason:
            msg = "Invalid notification payload: missing reason."
            raise ValueError(msg)

        subject_title = subject.get("title")
        if not isinstance(subject_title, str) or not subject_title:
            msg = "Invalid notification payload: missing subject.title."
            raise ValueError(msg)

        subject_type = subject.get("type")
        if not isinstance(subject_type, str) or not subject_type:
            msg = "Invalid notification payload: missing subject.type."
            raise ValueError(msg)

        unread = _optional_bool(payload, "unread", False, "notification payload")

        thread_url = payload.get("url")
        thread_url_str = thread_url if isinstance(thread_url, str) else None
        subject_url_raw = subject.get("url")
        subject_url_str = subject_url_raw if isinstance(subject_url_raw, str) else None
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
            subject_url=subject_url_str,
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
    context: dict[str, object] = field(default_factory=dict)

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
        updated_at = _require_non_empty_str(payload, "updated_at", "stored record")
        notification = Notification(
            thread_id=_require_non_empty_str(payload, "thread_id", "stored record"),
            repository=_require_non_empty_str(payload, "repository", "stored record"),
            reason=_require_non_empty_str(payload, "reason", "stored record"),
            subject_title=_require_non_empty_str(payload, "subject_title", "stored record"),
            subject_type=_require_non_empty_str(payload, "subject_type", "stored record"),
            unread=_optional_bool(payload, "unread", False, "stored record"),
            updated_at=parse_timestamp(updated_at),
            thread_url=_optional_str(payload, "thread_url"),
            subject_url=_optional_str(payload, "subject_url"),
            web_url=_optional_str(payload, "web_url"),
        )
        return cls(
            notification=notification,
            score=_optional_float(payload, "score", 0.0, "stored record"),
            excluded=_optional_bool(payload, "excluded", False, "stored record"),
            matched_rules=_optional_str_list(payload, "matched_rules"),
            actions_taken=_optional_str_list(payload, "actions_taken"),
            dismissed=_optional_bool(payload, "dismissed", False, "stored record"),
            context=_optional_context(payload, "context"),
        )


def _derive_web_url(payload: Mapping[str, object]) -> str | None:
    subject = _as_object_map(payload.get("subject"))
    repository = _as_object_map(payload.get("repository"))
    if subject is None or repository is None:
        return None

    repo_name = repository.get("full_name")
    if not isinstance(repo_name, str) or not repo_name:
        return None

    repo_web_url = repository.get("html_url")
    repo_base = repo_web_url if isinstance(repo_web_url, str) and repo_web_url else f"https://github.com/{repo_name}"

    subject_url = subject.get("url")
    if not isinstance(subject_url, str) or not subject_url:
        return None

    return _map_subject_api_url_to_web(subject_url=subject_url, repo_name=repo_name, repo_base=repo_base)


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
    if resource_name == "actions" and len(resource) >= _ACTIONS_RUNS_SEGMENTS and resource[1] == "runs":
        return f"{repo_base}/actions/runs/{resource[2]}"
    return None
