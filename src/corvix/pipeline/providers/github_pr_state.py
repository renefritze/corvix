"""GitHub pull-request state enrichment provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeIs

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.provider import PipelineContext


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
        ctx: PipelineContext,
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

        labels: list[str] = []
        raw_labels = payload.get("labels")
        if isinstance(raw_labels, list):
            for item in raw_labels:
                if _is_str_object_map(item):
                    name = item.get("name")
                    if isinstance(name, str):
                        labels.append(name)

        result: dict[str, object] = {
            "state": state if isinstance(state, str) else "",
            "merged": merged if isinstance(merged, bool) else False,
            "draft": draft if isinstance(draft, bool) else False,
            "author": {"login": author_login} if author_login is not None else {},
            "labels": labels,
        }

        # Viewer-aware fields are only present when the account login is configured;
        # rules referencing them simply do not match otherwise.
        viewer_login = (getattr(client, "account_login", "") or "").strip()
        if viewer_login:
            result["viewer_is_author"] = author_login is not None and author_login.casefold() == viewer_login.casefold()
            result["viewer_review_state"] = self._viewer_review_state(
                subject_url=notification.subject_url,
                client=client,
                ctx=ctx,
                viewer_login=viewer_login,
            )
        return result

    def _viewer_review_state(
        self,
        subject_url: str,
        client: JsonFetchClient,
        ctx: PipelineContext,
        viewer_login: str,
    ) -> str:
        """Return the viewer's latest decisive review state (APPROVED/DISMISSED/...) or ``NONE``.

        COMMENTED/PENDING reviews do not change approval standing, so they are
        skipped: an APPROVED followed by a comment still counts as approved.
        """
        try:
            reviews = ctx.get_json(
                client=client,
                url=f"{subject_url}/reviews?per_page=100",
                timeout_seconds=self.timeout_seconds,
            )
        except Exception:
            return "NONE"
        if not isinstance(reviews, list):
            return "NONE"
        state = "NONE"
        for review in reviews:
            if not _is_str_object_map(review):
                continue
            user = review.get("user")
            if not _is_str_object_map(user):
                continue
            login = user.get("login")
            if not isinstance(login, str) or login.casefold() != viewer_login.casefold():
                continue
            review_state = review.get("state")
            if isinstance(review_state, str) and review_state not in ("COMMENTED", "PENDING"):
                state = review_state
        return state
