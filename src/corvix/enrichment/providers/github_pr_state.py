"""GitHub pull-request state enrichment provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeIs

from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentContext, JsonFetchClient


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


@dataclass(slots=True)
class GitHubPRStateProvider:
    """Enriches pull-request notifications with state metadata."""

    timeout_seconds: float = 10.0
    name: str = "github.pr_state"

    def enrich(
        self,
        notification: Notification,
        client: JsonFetchClient,
        ctx: EnrichmentContext,
    ) -> dict[str, object]:
        """Return pull-request state metadata under the provider namespace."""
        if notification.subject_type != "PullRequest" or not notification.subject_url:
            return {}

        payload = ctx.get_json(client=client, url=notification.subject_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(payload):
            return {}

        state = payload.get("state")
        merged = payload.get("merged")
        draft = payload.get("draft")

        user = payload.get("user")
        author_login: str | None = None
        if _is_str_object_map(user):
            login = user.get("login")
            if isinstance(login, str):
                author_login = login

        return {
            "state": state if isinstance(state, str) else "",
            "merged": merged if isinstance(merged, bool) else False,
            "draft": draft if isinstance(draft, bool) else False,
            "author": {"login": author_login} if author_login is not None else {},
        }
