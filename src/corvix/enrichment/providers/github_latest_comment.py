"""GitHub latest-comment enrichment provider."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeIs

from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentContext, JsonFetchClient

_TEST_REPORT_LINK_ONLY_RE = re.compile(r"^\[\s*Test report\s*\]\([^\s)]+\)$", re.IGNORECASE)


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


@dataclass(slots=True)
class GitHubLatestCommentProvider:
    """Enriches comment notifications with the latest comment metadata."""

    timeout_seconds: float = 10.0
    name: str = "github.latest_comment"

    def enrich(
        self,
        notification: Notification,
        client: JsonFetchClient,
        ctx: EnrichmentContext,
    ) -> dict[str, object]:
        """Return latest comment metadata under the provider namespace."""
        if notification.reason != "comment" or not notification.thread_url:
            return {}

        thread_payload = ctx.get_json(client=client, url=notification.thread_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(thread_payload):
            return {}
        latest_comment_url = _extract_latest_comment_url(thread_payload)
        if latest_comment_url is None:
            return {}

        comment_payload = ctx.get_json(client=client, url=latest_comment_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(comment_payload):
            return {}

        body_raw = comment_payload.get("body")
        body = body_raw if isinstance(body_raw, str) else ""
        user = comment_payload.get("user")
        author_login: str | None = None
        if _is_str_object_map(user):
            login = user.get("login")
            if isinstance(login, str):
                author_login = login

        return {
            "author": {"login": author_login} if author_login is not None else {},
            "body": body,
            "is_ci_only": _is_ci_only(body),
            "is_test_report_link_only": _is_test_report_link_only(body),
        }


def _extract_latest_comment_url(thread_payload: Mapping[str, object]) -> str | None:
    subject = thread_payload.get("subject")
    if not _is_str_object_map(subject):
        return None
    latest_comment_url = subject.get("latest_comment_url")
    return latest_comment_url if isinstance(latest_comment_url, str) and latest_comment_url else None


def _is_ci_only(body: str) -> bool:
    return body.strip().casefold() == "ci"


def _is_test_report_link_only(body: str) -> bool:
    return _TEST_REPORT_LINK_ONLY_RE.fullmatch(body.strip()) is not None
