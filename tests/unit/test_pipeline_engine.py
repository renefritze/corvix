"""Tests for the unified PipelineEngine and its provider protocols."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient, RequestContext
from corvix.pipeline.engine import PipelineEngine, PipelineRunResult, _set_nested_namespace
from corvix.pipeline.provider import ContextProvider, FieldProvider, PipelineContext
from corvix.types import JsonValue

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _notification(
    *,
    thread_id: str = "1",
    account_id: str = "primary",
    subject_url: str | None = None,
    web_url: str | None = None,
    reason: str = "mention",
) -> Notification:
    return Notification(
        thread_id=thread_id,
        account_id=account_id,
        repository="org/repo",
        reason=reason,
        subject_title="Test",
        subject_type="Issue",
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        thread_url=f"https://api.example.com/notifications/threads/{thread_id}",
        subject_url=subject_url,
        web_url=web_url,
    )


class _FakeClient:
    def __init__(self, responses: dict[str, JsonValue], api_base_url: str = "https://api.example.com") -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.api_base_url = api_base_url

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        del timeout_seconds
        self.calls.append(url)
        return self.responses[url]


# ---------------------------------------------------------------------------
# Minimal provider stubs
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _TaggingFieldProvider:
    """Appends a marker to web_url so tests can verify ordering."""

    name: str = "test.field"
    tag: str = "TAGGED"

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> Notification:
        del client
        del ctx
        return replace(notification, web_url=self.tag)


@dataclass(slots=True)
class _CapturingContextProvider:
    """Records the web_url it sees when enrich() is called."""

    name: str = "test.context"
    seen_web_urls: list[str | None] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.seen_web_urls is None:
            self.seen_web_urls = []

    def enrich(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> dict[str, object]:
        del client
        del ctx
        self.seen_web_urls.append(notification.web_url)
        return {"captured_web_url": notification.web_url}


@dataclass(slots=True)
class _FetchingContextProvider:
    """Makes one HTTP request per notification."""

    name: str = "test.fetching"

    def enrich(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> dict[str, object]:
        url = f"https://api.example.com/{notification.thread_id}"
        ctx.get_json(client=client, url=url, timeout_seconds=1.0)
        return {"ok": True}


@dataclass(slots=True)
class _CachingFieldProvider:
    """Fetches a URL to fill web_url; uses the cycle cache."""

    name: str = "test.caching_field"

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> Notification:
        payload = ctx.get_json(client=client, url="https://api.example.com/shared", timeout_seconds=1.0)
        url = str(payload) if not isinstance(payload, dict) else str(payload.get("url", ""))
        return replace(notification, web_url=url)


@dataclass(slots=True)
class _CachingContextProvider:
    """Reads the same URL as _CachingFieldProvider to verify cross-provider cache."""

    name: str = "test.caching_context"

    def enrich(self, _notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> dict[str, object]:
        payload = ctx.get_json(client=client, url="https://api.example.com/shared", timeout_seconds=1.0)
        return {"shared": payload}


@dataclass(slots=True)
class _BoomProvider:
    """Always raises when dispatched as a FieldProvider."""

    name: str = "test.boom"

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> Notification:
        del client, ctx
        raise RuntimeError(f"boom {notification.thread_id}")


# ---------------------------------------------------------------------------
# Protocol isinstance() checks
# ---------------------------------------------------------------------------


def test_field_provider_protocol_isinstance() -> None:
    provider = _TaggingFieldProvider()
    assert isinstance(provider, FieldProvider)
    assert not isinstance(provider, ContextProvider)


def test_context_provider_protocol_isinstance() -> None:
    provider = _CapturingContextProvider()
    assert isinstance(provider, ContextProvider)
    assert not isinstance(provider, FieldProvider)


# ---------------------------------------------------------------------------
# PipelineEngine — empty providers
# ---------------------------------------------------------------------------


def test_engine_empty_providers_returns_notifications_unchanged() -> None:
    n = _notification()
    engine = PipelineEngine(providers=[])

    result = engine.run(notifications=[n], client=_FakeClient(responses={}))

    assert result.notifications == [n]
    assert result.errors == []
    assert result.contexts_by_notification_key == {"primary:1": {}}


# ---------------------------------------------------------------------------
# PipelineEngine — field-first ordering
# ---------------------------------------------------------------------------


def test_context_provider_sees_hydrated_notification() -> None:
    """ContextProvider must see the notification *after* FieldProvider ran."""
    n = _notification(web_url=None)
    field_prov = _TaggingFieldProvider(tag="https://github.com/org/repo/issues/1")
    ctx_prov = _CapturingContextProvider()
    engine = PipelineEngine(providers=[field_prov, ctx_prov])

    result = engine.run(notifications=[n], client=_FakeClient(responses={}))

    assert result.notifications[0].web_url == "https://github.com/org/repo/issues/1"
    assert ctx_prov.seen_web_urls == ["https://github.com/org/repo/issues/1"]


def test_field_provider_after_context_provider_still_updates_notification() -> None:
    """FieldProvider placed after a ContextProvider still updates the notification."""
    n = _notification(web_url=None)
    ctx_prov = _CapturingContextProvider()
    field_prov = _TaggingFieldProvider(tag="set-by-field")
    engine = PipelineEngine(providers=[ctx_prov, field_prov])

    result = engine.run(notifications=[n], client=_FakeClient(responses={}))

    # ContextProvider ran first and saw no web_url
    assert ctx_prov.seen_web_urls == [None]
    # FieldProvider ran after and updated the notification
    assert result.notifications[0].web_url == "set-by-field"


# ---------------------------------------------------------------------------
# PipelineEngine — URL cache shared across all providers
# ---------------------------------------------------------------------------


def test_shared_url_cache_between_field_and_context_providers() -> None:
    """A URL fetched by a FieldProvider must not be re-fetched by a ContextProvider."""
    n = _notification()
    client = _FakeClient(responses={"https://api.example.com/shared": {"url": "https://github.com/org/repo"}})

    engine = PipelineEngine(
        providers=[_CachingFieldProvider(), _CachingContextProvider()],
        max_requests_per_cycle=10,
    )
    result = engine.run(notifications=[n], client=client)

    # Only one HTTP request total — cache was shared between the two providers
    assert client.calls == ["https://api.example.com/shared"]
    assert result.notifications[0].web_url == "https://github.com/org/repo"
    assert result.contexts_by_notification_key["primary:1"]["test"]["caching_context"]["shared"] == {
        "url": "https://github.com/org/repo",
    }


# ---------------------------------------------------------------------------
# PipelineEngine — shared budget across all providers
# ---------------------------------------------------------------------------


def test_shared_budget_exhausted_across_providers() -> None:
    """A single budget is consumed by both field and context providers."""
    notifications = [_notification(thread_id="1"), _notification(thread_id="2")]
    client = _FakeClient(
        responses={
            "https://api.example.com/1": {},
            "https://api.example.com/2": {},
        },
    )
    engine = PipelineEngine(
        providers=[_FetchingContextProvider()],
        max_requests_per_cycle=1,
    )

    result = engine.run(notifications=notifications, client=client)

    # First notification succeeds; second exhausts the budget
    assert client.calls == ["https://api.example.com/1"]
    assert result.contexts_by_notification_key["primary:1"].get("test", {}).get("fetching") == {"ok": True}
    assert result.contexts_by_notification_key["primary:2"] == {}
    assert result.errors
    assert "budget exhausted" in result.errors[0].casefold()


# ---------------------------------------------------------------------------
# PipelineEngine — fail-open error handling
# ---------------------------------------------------------------------------


def test_field_provider_failure_is_non_fatal() -> None:
    n = _notification()
    boom = _BoomProvider()
    engine = PipelineEngine(providers=[boom])

    result = engine.run(notifications=[n], client=_FakeClient(responses={}))

    assert result.notifications[0] == n  # unchanged since provider failed
    assert len(result.errors) == 1
    assert "boom 1" in result.errors[0]


# ---------------------------------------------------------------------------
# PipelineEngine — multiple notifications
# ---------------------------------------------------------------------------


def test_multiple_notifications_all_processed() -> None:
    notifications = [_notification(thread_id=str(i)) for i in range(3)]
    field_prov = _TaggingFieldProvider(tag="tagged")
    ctx_prov = _CapturingContextProvider()
    engine = PipelineEngine(providers=[field_prov, ctx_prov])

    result = engine.run(notifications=notifications, client=_FakeClient(responses={}))

    assert len(result.notifications) == 3
    assert all(n.web_url == "tagged" for n in result.notifications)
    assert len(result.contexts_by_notification_key) == 3


# ---------------------------------------------------------------------------
# PipelineEngine — clients_by_account routing
# ---------------------------------------------------------------------------


def test_clients_by_account_routes_to_correct_client() -> None:
    n1 = _notification(thread_id="1", account_id="account-a")
    n2 = _notification(thread_id="2", account_id="account-b")
    client_a = _FakeClient(responses={}, api_base_url="https://a.example.com")
    client_b = _FakeClient(responses={}, api_base_url="https://b.example.com")
    default_client = _FakeClient(responses={}, api_base_url="https://default.example.com")

    seen: list[tuple[str, str]] = []

    @dataclass(slots=True)
    class _SpyFieldProvider:
        name: str = "test.spy"

        def hydrate(self, notification: Notification, client: JsonFetchClient, _ctx: PipelineContext) -> Notification:
            seen.append((notification.thread_id, client.api_base_url))
            return notification

    engine = PipelineEngine(providers=[_SpyFieldProvider()])
    engine.run(
        notifications=[n1, n2],
        client=default_client,
        clients_by_account={"account-a": client_a, "account-b": client_b},
    )

    assert ("1", "https://a.example.com") in seen
    assert ("2", "https://b.example.com") in seen


def test_missing_account_falls_back_to_default_client() -> None:
    n = _notification(thread_id="1", account_id="unknown")
    default_client = _FakeClient(responses={}, api_base_url="https://default.example.com")
    seen: list[str] = []

    @dataclass(slots=True)
    class _SpyProvider:
        name: str = "test.spy"

        def hydrate(self, notification: Notification, client: JsonFetchClient, _ctx: PipelineContext) -> Notification:
            seen.append(client.api_base_url)
            return notification

    engine = PipelineEngine(providers=[_SpyProvider()])
    engine.run(notifications=[n], client=default_client, clients_by_account={"other-account": _FakeClient({})})

    assert seen == ["https://default.example.com"]


# ---------------------------------------------------------------------------
# PipelineRunResult — contexts_by_thread_id property
# ---------------------------------------------------------------------------


def test_contexts_by_thread_id_strips_account_prefix() -> None:
    result = PipelineRunResult(
        notifications=[],
        contexts_by_notification_key={
            "account-a:t1": {"key": "val1"},
            "account-b:t2": {"key": "val2"},
        },
        errors=[],
    )

    by_thread = result.contexts_by_thread_id

    assert by_thread["t1"] == {"key": "val1"}
    assert by_thread["t2"] == {"key": "val2"}


# ---------------------------------------------------------------------------
# _set_nested_namespace helper
# ---------------------------------------------------------------------------


def test_set_nested_namespace_simple_key() -> None:
    root: dict[str, object] = {}
    _set_nested_namespace(root, "foo", {"a": 1})
    assert root == {"foo": {"a": 1}}


def test_set_nested_namespace_dot_delimited() -> None:
    root: dict[str, object] = {}
    _set_nested_namespace(root, "github.pr_state", {"state": "open"})
    assert root == {"github": {"pr_state": {"state": "open"}}}


def test_set_nested_namespace_merges_into_existing() -> None:
    root: dict[str, object] = {"github": {"pr_state": {"state": "open"}}}
    _set_nested_namespace(root, "github.pr_state", {"merged": True})
    assert root == {"github": {"pr_state": {"state": "open", "merged": True}}}


def test_set_nested_namespace_empty_segments_is_noop() -> None:
    root: dict[str, object] = {}
    _set_nested_namespace(root, "...", {})  # all dots, no real segments
    assert root == {}


def test_set_nested_namespace_overwrites_non_dict_intermediate() -> None:
    root: dict[str, object] = {"github": "not-a-dict"}
    _set_nested_namespace(root, "github.pr_state", {"state": "open"})
    assert root == {"github": {"pr_state": {"state": "open"}}}


# ---------------------------------------------------------------------------
# PipelineContext — budget error message
# ---------------------------------------------------------------------------


def test_pipeline_context_budget_error_message() -> None:
    ctx = PipelineContext(max_requests_per_cycle=0)
    client = _FakeClient(responses={})

    with pytest.raises(RuntimeError, match="[Pp]ipeline request budget exhausted"):
        ctx.get_json(client=client, url="https://api.example.com/anything", timeout_seconds=1.0)


def test_request_context_base_budget_error_message() -> None:
    """The base RequestContext raises its own budget message when exhausted."""
    ctx = RequestContext(max_requests_per_cycle=0)
    client = _FakeClient(responses={})

    with pytest.raises(RuntimeError, match="[Rr]equest budget exhausted"):
        ctx.get_json(client=client, url="https://api.example.com/anything", timeout_seconds=1.0)
