"""Tests for enrichment engine and providers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeIs

from corvix.config import EnrichmentConfig
from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentContext, EnrichmentProvider, JsonFetchClient
from corvix.enrichment.engine import EnrichmentEngine
from corvix.enrichment.providers.github_latest_comment import GitHubLatestCommentProvider
from corvix.enrichment.providers.github_pr_state import GitHubPRStateProvider
from corvix.types import JsonValue


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


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
    def __init__(self, responses: dict[str, JsonValue]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        self.calls.append(url)
        return self.responses[url]


class _CachingProvider(EnrichmentProvider):
    name = "test.cache"

    def enrich(self, notification: Notification, client: JsonFetchClient, ctx: EnrichmentContext) -> dict[str, object]:
        first = ctx.get_json(client=client, url="https://api.example.com/a", timeout_seconds=1.0)
        second = ctx.get_json(client=client, url="https://api.example.com/a", timeout_seconds=1.0)
        return {"same_payload": first == second, "thread": notification.thread_id}


class _BudgetProvider(EnrichmentProvider):
    name = "test.budget"

    def enrich(self, notification: Notification, client: JsonFetchClient, ctx: EnrichmentContext) -> dict[str, object]:
        ctx.get_json(client=client, url=f"https://api.example.com/{notification.thread_id}", timeout_seconds=1.0)
        return {"ok": True}


class _BrokenProvider(EnrichmentProvider):
    name = "test.broken"

    def enrich(self, notification: Notification, client: JsonFetchClient, ctx: EnrichmentContext) -> dict[str, object]:
        del client
        del ctx
        raise RuntimeError(f"boom {notification.thread_id}")


def _require_nested_value(root: dict[str, object], *path: str) -> object:
    node: object = root
    for segment in path:
        assert _is_str_object_map(node)
        assert segment in node
        node = node[segment]
    return node


def test_engine_dedupes_url_fetches_with_cycle_cache() -> None:
    providers: list[EnrichmentProvider] = [_CachingProvider()]
    engine = EnrichmentEngine(config=EnrichmentConfig(enabled=True), providers=providers)
    notifications = [_notification(thread_id="1"), _notification(thread_id="2")]
    client = _FakeClient(responses={"https://api.example.com/a": {"v": 1}})

    result = engine.run(notifications=notifications, client=client)

    assert client.calls == ["https://api.example.com/a"]
    assert _require_nested_value(result.contexts_by_thread_id["1"], "test", "cache", "same_payload") is True
    assert _require_nested_value(result.contexts_by_thread_id["2"], "test", "cache", "same_payload") is True


def test_engine_respects_request_budget() -> None:
    providers: list[EnrichmentProvider] = [_BudgetProvider()]
    engine = EnrichmentEngine(config=EnrichmentConfig(enabled=True, max_requests_per_cycle=1), providers=providers)
    notifications = [_notification(thread_id="1"), _notification(thread_id="2")]
    client = _FakeClient(responses={"https://api.example.com/1": {}, "https://api.example.com/2": {}})

    result = engine.run(notifications=notifications, client=client)

    assert client.calls == ["https://api.example.com/1"]
    assert _require_nested_value(result.contexts_by_thread_id["1"], "test", "budget", "ok") is True
    assert result.contexts_by_thread_id["2"] == {}
    assert result.errors
    assert "budget exhausted" in result.errors[0].casefold()


def test_engine_provider_failure_is_non_fatal() -> None:
    providers: list[EnrichmentProvider] = [_BrokenProvider()]
    engine = EnrichmentEngine(config=EnrichmentConfig(enabled=True), providers=providers)
    notifications = [_notification(thread_id="1")]
    client = _FakeClient(responses={})

    result = engine.run(notifications=notifications, client=client)

    assert result.contexts_by_thread_id["1"] == {}
    assert result.errors == ["provider=test.broken thread=1: boom 1"]


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
    context = EnrichmentContext(max_requests_per_cycle=10)

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
    context = EnrichmentContext(max_requests_per_cycle=10)

    payload = provider.enrich(notification=_notification(thread_id="2"), client=client, ctx=context)

    assert payload["is_ci_only"] is False
    assert payload["is_test_report_link_only"] is True


def test_latest_comment_provider_skips_non_comment_reason() -> None:
    provider = GitHubLatestCommentProvider()
    client = _FakeClient(responses={})
    context = EnrichmentContext(max_requests_per_cycle=10)

    payload = provider.enrich(notification=_notification(reason="mention"), client=client, ctx=context)

    assert payload == {}
    assert client.calls == []


def test_pr_state_provider_skips_non_pr_notification() -> None:
    provider = GitHubPRStateProvider(timeout_seconds=2.0)
    client = _FakeClient(responses={})
    context = EnrichmentContext(max_requests_per_cycle=10)

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
    context = EnrichmentContext(max_requests_per_cycle=10)

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
    context = EnrichmentContext(max_requests_per_cycle=10)

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
    context = EnrichmentContext(max_requests_per_cycle=10)

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
    context = EnrichmentContext(max_requests_per_cycle=10)

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
    context = EnrichmentContext(max_requests_per_cycle=10)

    payload = provider.enrich(
        notification=_notification(subject_type="PullRequest", subject_url=subject_url),
        client=client,
        ctx=context,
    )

    assert payload == {}
