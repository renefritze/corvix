"""GitHub latest-comment enrichment provider."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentContext
from corvix.ingestion import GitHubNotificationsClient

_TEST_REPORT_LINK_ONLY_RE = re.compile(r"^\[\s*Test report\s*\]\([^\s)]+\)$", re.IGNORECASE)


@dataclass(slots=True)
class GitHubLatestCommentProvider:
    """Enriches comment notifications with the latest comment metadata."""

    timeout_seconds: float = 10.0
    name: str = "github.latest_comment"

    def enrich(
        self,
        notification: Notification,
        client: GitHubNotificationsClient,
        ctx: EnrichmentContext,
    ) -> dict[str, object]:
        """Return latest comment metadata under the provider namespace."""
        if notification.reason != "comment" or not notification.thread_url:
            return {}

        thread_payload = ctx.get_json(client=client, url=notification.thread_url, timeout_seconds=self.timeout_seconds)
        if not isinstance(thread_payload, dict):
            return {}
        latest_comment_url = _extract_latest_comment_url(cast(dict[str, Any], thread_payload))
        if latest_comment_url is None:
            return {}

        comment_payload = ctx.get_json(client=client, url=latest_comment_url, timeout_seconds=self.timeout_seconds)
        if not isinstance(comment_payload, dict):
            return {}

        payload = cast(dict[str, Any], comment_payload)
        body_raw = payload.get("body")
        body = body_raw if isinstance(body_raw, str) else ""
        user = payload.get("user")
        author_login: str | None = None
        if isinstance(user, dict):
            login = user.get("login")
            if isinstance(login, str):
                author_login = login

        return {
            "author": {"login": author_login} if author_login is not None else {},
            "body": body,
            "is_ci_only": _is_ci_only(body),
            "is_test_report_link_only": _is_test_report_link_only(body),
        }


def _extract_latest_comment_url(thread_payload: dict[str, Any]) -> str | None:
    subject = thread_payload.get("subject")
    if not isinstance(subject, dict):
        return None
    latest_comment_url = subject.get("latest_comment_url")
    return latest_comment_url if isinstance(latest_comment_url, str) and latest_comment_url else None


def _is_ci_only(body: str) -> bool:
    return body.strip().casefold() == "ci"


def _is_test_report_link_only(body: str) -> bool:
    return _TEST_REPORT_LINK_ONLY_RE.fullmatch(body.strip()) is not None
