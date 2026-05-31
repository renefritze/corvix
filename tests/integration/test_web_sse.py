"""Tests for the Server-Sent Events snapshot stream (``GET /api/v1/events``)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Generator

import pytest
from litestar.exceptions import HTTPException
from litestar.response import ServerSentEvent, ServerSentEventMessage

import corvix.web.app as web_app
from corvix.web.app import _snapshot_event_generator, _sse_poll_interval, app


async def _drain(
    generator: AsyncIterator[ServerSentEventMessage],
    count: int,
) -> list[ServerSentEventMessage]:
    """Collect *count* messages from the (infinite) SSE generator, then close it."""
    messages: list[ServerSentEventMessage] = []
    try:
        for _ in range(count):
            messages.append(await generator.__anext__())
    finally:
        await generator.aclose()
    return messages


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the SSE loop's inter-tick sleep a no-op so tests run instantly."""

    async def _immediate(_seconds: float) -> None:
        return None

    monkeypatch.setattr(web_app.asyncio, "sleep", _immediate)


@pytest.fixture(autouse=True)
def _clear_snapshot_cache() -> Generator[None]:
    """Isolate the process-wide SSE body cache between tests."""
    web_app._snapshot_body_cache.clear()
    yield
    web_app._snapshot_body_cache.clear()


# --- _sse_poll_interval ---


def test_sse_poll_interval_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORVIX_SSE_POLL_INTERVAL_SECONDS", raising=False)
    assert _sse_poll_interval() == pytest.approx(web_app._SSE_DEFAULT_POLL_INTERVAL_SECONDS)


def test_sse_poll_interval_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORVIX_SSE_POLL_INTERVAL_SECONDS", "1.5")
    assert _sse_poll_interval() == pytest.approx(1.5)


@pytest.mark.parametrize("raw", ["not-a-number", "0", "-2"])
def test_sse_poll_interval_falls_back(raw: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORVIX_SSE_POLL_INTERVAL_SECONDS", raw)
    assert _sse_poll_interval() == pytest.approx(web_app._SSE_DEFAULT_POLL_INTERVAL_SECONDS)


# --- _snapshot_event_generator ---


def test_generator_pushes_only_on_change(monkeypatch: pytest.MonkeyPatch) -> None:
    bodies = iter(['{"name":"a"}', '{"name":"a"}', '{"name":"b"}'])
    # Patch the cached wrapper so each tick gets a fresh body (the real cache
    # would otherwise reuse the first build since no wall-clock time elapses).
    monkeypatch.setattr(web_app, "_cached_snapshot_event_body", lambda _dashboard, _ttl: next(bodies))
    # Force the keep-alive branch on the unchanged (second) tick.
    monkeypatch.setattr(web_app, "_SSE_KEEPALIVE_SECONDS", -1.0)

    messages = asyncio.run(_drain(_snapshot_event_generator("overview"), 3))

    assert messages[0].event == "snapshot"
    assert json.loads(messages[0].data) == {"name": "a"}
    # Unchanged payload -> no new snapshot, just a keep-alive comment.
    assert messages[1].event is None
    assert messages[1].comment == "keep-alive"
    assert messages[2].event == "snapshot"
    assert json.loads(messages[2].data) == {"name": "b"}


def test_generator_skips_keepalive_when_idle_window_not_elapsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Same payload twice with a large keep-alive window: the second tick should
    # neither push a snapshot nor emit a keep-alive, so the third (changed) tick
    # is the next message we receive.
    bodies = iter(['{"name":"a"}', '{"name":"a"}', '{"name":"b"}'])
    monkeypatch.setattr(web_app, "_cached_snapshot_event_body", lambda _dashboard, _ttl: next(bodies))
    monkeypatch.setattr(web_app, "_SSE_KEEPALIVE_SECONDS", 3600.0)

    messages = asyncio.run(_drain(_snapshot_event_generator(None), 2))

    assert [m.event for m in messages] == ["snapshot", "snapshot"]
    assert json.loads(messages[0].data) == {"name": "a"}
    assert json.loads(messages[1].data) == {"name": "b"}


def test_generator_emits_error_event_on_http_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_dashboard: str | None) -> str:
        raise HTTPException(status_code=500, detail="config broken")

    monkeypatch.setattr(web_app, "_snapshot_event_body", _boom)

    messages = asyncio.run(_drain(_snapshot_event_generator(None), 1))

    assert messages[0].event == "snapshot-error"
    payload = json.loads(messages[0].data)
    assert payload == {"detail": "config broken", "status_code": 500}


def test_generator_reports_unexpected_error_without_leaking_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_dashboard: str | None) -> str:
        raise RuntimeError("psycopg connection refused: host=secret-db")

    monkeypatch.setattr(web_app, "_snapshot_event_body", _boom)

    messages = asyncio.run(_drain(_snapshot_event_generator(None), 1))

    assert messages[0].event == "snapshot-error"
    payload = json.loads(messages[0].data)
    # The raw exception text must not be leaked to the client.
    assert payload == {"detail": "Internal server error.", "status_code": 500}


# --- _cached_snapshot_event_body ---


def test_cached_body_is_reused_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def _build(_dashboard: str | None) -> str:
        calls["n"] += 1
        return f'{{"build":{calls["n"]}}}'

    monkeypatch.setattr(web_app, "_snapshot_event_body", _build)

    first = web_app._cached_snapshot_event_body("overview", ttl=100.0)
    second = web_app._cached_snapshot_event_body("overview", ttl=100.0)

    # A single storage read is shared by both callers within the TTL window.
    assert first == second == '{"build":1}'
    assert calls["n"] == 1


def test_cached_body_rebuilds_when_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def _build(_dashboard: str | None) -> str:
        calls["n"] += 1
        return f'{{"build":{calls["n"]}}}'

    monkeypatch.setattr(web_app, "_snapshot_event_body", _build)

    # ttl=0 means no cached entry is ever fresh (strict age < ttl), so every
    # call rebuilds -- this is the lone-client case that must not be slowed.
    web_app._cached_snapshot_event_body("overview", ttl=0.0)
    web_app._cached_snapshot_event_body("overview", ttl=0.0)

    assert calls["n"] == 2


def test_cached_body_is_keyed_by_dashboard(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def _build(dashboard: str | None) -> str:
        calls["n"] += 1
        return json.dumps({"dashboard": dashboard})

    monkeypatch.setattr(web_app, "_snapshot_event_body", _build)

    overview = web_app._cached_snapshot_event_body("overview", ttl=100.0)
    triage = web_app._cached_snapshot_event_body("triage", ttl=100.0)

    # Distinct dashboards do not share a cache entry.
    assert json.loads(overview) == {"dashboard": "overview"}
    assert json.loads(triage) == {"dashboard": "triage"}
    assert calls["n"] == 2


def test_generator_recovers_after_error(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"calls": 0}

    def _flaky(_dashboard: str | None) -> str:
        state["calls"] += 1
        if state["calls"] == 1:
            raise HTTPException(status_code=503, detail="storage down")
        return '{"name":"ok"}'

    monkeypatch.setattr(web_app, "_snapshot_event_body", _flaky)

    messages = asyncio.run(_drain(_snapshot_event_generator(None), 2))

    assert messages[0].event == "snapshot-error"
    assert messages[1].event == "snapshot"
    assert json.loads(messages[1].data) == {"name": "ok"}


def test_events_route_is_registered() -> None:
    """The SSE endpoint is wired into the application's routes."""
    assert "/api/v1/events" in {route.path for route in app.routes}


def test_snapshot_generator_wraps_in_sse_response() -> None:
    """The snapshot generator can back a Litestar SSE response."""
    response = ServerSentEvent(_snapshot_event_generator("overview"))
    assert isinstance(response, ServerSentEvent)
