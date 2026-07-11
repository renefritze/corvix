"""Tests for the context-enrichment providers (latest-comment, pr-state).

The engine-level behaviours these providers rely on — cross-provider URL cache,
request budget, and non-fatal provider failure — are covered against the
unified engine in ``tests/unit/test_pipeline_engine.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.provider import PipelineContext
from corvix.pipeline.providers.github_latest_comment import GitHubLatestCommentProvider
from corvix.pipeline.providers.github_pr_state import GitHubPRStateProvider
from corvix.types import JsonValue


def _notification(
    *,
    thread_id: str = "1",
    reason: str = "comment",
    thread_url: str | None = None,
    subject_type: str = "Issue",
    subject_url: str | None = None,
) -> Notification:
    return Notification(
        thread_id=thread_id,
        repository="org/repo",
        reason=reason,
        subject_title="Ping",
        subject_type=subject_type,
        unread=True,
        updated_at=datetime.now(tz=UTC),
        thread_url=thread_url or f"https://api.example.com/notifications/threads/{thread_id}",
        subject_url=subject_url,
    )


class _FakeClient(JsonFetchClient):
    def __init__(self, responses: dict[str, JsonValue], account_id: str = "primary") -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.api_base_url = "https://api.example.com"
        self.account_id = account_id

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        self.calls.append(url)
        return self.responses[url]


def test_latest_comment_provider_flags_ci_only() -> None:
    provider = GitHubLatestCommentProvider(timeout_seconds=2.0)
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/1": {
                "subject": {"latest_comment_url": "https://api.example.com/repos/org/repo/issues/comments/99"}
            },
            "https://api.example.com/repos/org/repo/issues/comments/99": {
                "user": {"login": "codecov[bot]"},
                "body": "   CI\n",
            },
        }
    )
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(notification=_notification(thread_id="1"), client=client, ctx=context)

    assert payload["author"] == {"login": "codecov[bot]"}
    assert payload["is_ci_only"] is True
    assert payload["is_test_report_link_only"] is False


def test_latest_comment_provider_flags_test_report_link_only() -> None:
    provider = GitHubLatestCommentProvider(timeout_seconds=2.0)
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/2": {
                "subject": {"latest_comment_url": "https://api.example.com/repos/org/repo/issues/comments/100"}
            },
            "https://api.example.com/repos/org/repo/issues/comments/100": {
                "user": {"login": "someone"},
                "body": "[Test report](https://example.com/report)",
            },
        }
    )
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(notification=_notification(thread_id="2"), client=client, ctx=context)

    assert payload["is_ci_only"] is False
    assert payload["is_test_report_link_only"] is True


def test_latest_comment_provider_skips_non_comment_reason() -> None:
    provider = GitHubLatestCommentProvider()
    client = _FakeClient(responses={})
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(notification=_notification(reason="mention"), client=client, ctx=context)

    assert payload == {}
    assert client.calls == []


def test_pr_state_provider_skips_non_pr_notification() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    client = _FakeClient(responses={})
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="Issue", subject_url="https://api.example.com/repos/org/repo/issues/1"),
        client=client,
        ctx=context,
    )

    assert payload == {}
    assert client.calls == []


def test_pr_state_provider_skips_notification_without_subject_url() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    client = _FakeClient(responses={})
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="PullRequest", subject_url=None),
        client=client,
        ctx=context,
    )

    assert payload == {}
    assert client.calls == []


def test_pr_state_provider_enriches_open_pr() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    subject_url = "https://api.example.com/repos/org/repo/pulls/123"
    client = _FakeClient(
        responses={
            subject_url: {
                "state": "open",
                "merged": False,
                "draft": False,
                "user": {"login": "alice"},
            }
        }
    )
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="PullRequest", subject_url=subject_url),
        client=client,
        ctx=context,
    )

    assert payload == {
        "state": "open",
        "merged": False,
        "draft": False,
        "author": {"login": "alice"},
    }


def test_pr_state_provider_enriches_merged_pr() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    subject_url = "https://api.example.com/repos/org/repo/pulls/456"
    client = _FakeClient(
        responses={
            subject_url: {
                "state": "closed",
                "merged": True,
                "draft": False,
                "user": {"login": "dependabot[bot]"},
            }
        }
    )
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="PullRequest", subject_url=subject_url),
        client=client,
        ctx=context,
    )

    assert payload["state"] == "closed"
    assert payload["merged"] is True
    assert payload["author"] == {"login": "dependabot[bot]"}


def test_pr_state_provider_returns_empty_author_when_user_missing() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    subject_url = "https://api.example.com/repos/org/repo/pulls/789"
    client = _FakeClient(
        responses={
            subject_url: {
                "state": "closed",
                "merged": False,
                "draft": True,
            }
        }
    )
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="PullRequest", subject_url=subject_url),
        client=client,
        ctx=context,
    )

    assert payload["author"] == {}
    assert payload["draft"] is True


def test_pr_state_provider_ignores_malformed_payload() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    subject_url = "https://api.example.com/repos/org/repo/pulls/999"
    client = _FakeClient(responses={subject_url: "not-an-object"})
    context = PipelineContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="PullRequest", subject_url=subject_url),
        client=client,
        ctx=context,
    )

    assert payload == {}
