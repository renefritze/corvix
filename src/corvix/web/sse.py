"""Server-Sent Events: push snapshot updates instead of client-side polling.

The server polls storage on a short interval and pushes a ``snapshot`` event
only when the serialized payload actually changes, so idle connections cost a
periodic comparison (plus an occasional keep-alive) rather than a full response
on every tick.  Browsers reconnect automatically via EventSource, and the
frontend falls back to interval polling when SSE is unavailable.

A short-lived, process-wide cache of the serialized body (keyed by dashboard)
collapses the storage reads of concurrent connections watching the same
dashboard into roughly one read per poll interval, instead of one read per
connection per tick.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
from collections.abc import AsyncIterator
from os import environ
from time import monotonic

from litestar import get
from litestar.exceptions import HTTPException
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.serialization import encode_json

from corvix.web.snapshot import _snapshot_impl

logger = logging.getLogger(__name__)

_SSE_DEFAULT_POLL_INTERVAL_SECONDS = 3.0
_SSE_KEEPALIVE_SECONDS = 20.0


def _sse_poll_interval() -> float:
    """Return the server-side SSE poll interval in seconds.

    Read from ``CORVIX_SSE_POLL_INTERVAL_SECONDS``; falls back to the default
    when unset, non-numeric, or non-positive.
    """
    raw = environ.get("CORVIX_SSE_POLL_INTERVAL_SECONDS")
    if raw is None:
        return _SSE_DEFAULT_POLL_INTERVAL_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return _SSE_DEFAULT_POLL_INTERVAL_SECONDS
    return value if value > 0 else _SSE_DEFAULT_POLL_INTERVAL_SECONDS


def _snapshot_event_body(dashboard: str | None) -> str:
    """Build the snapshot payload and serialize it to a compact JSON string.

    Uses msgspec (the encoder Litestar uses for the equivalent HTTP route) so the
    SSE body and the ``GET /api/v1/snapshot`` response share one serialization
    path and stay byte-for-byte consistent.
    """
    payload = _snapshot_impl(dashboard=dashboard)
    return encode_json(payload).decode("utf-8")


# Process-wide cache of the most recently built SSE body per dashboard, used to
# deduplicate the storage reads of concurrent connections. Guarded by a lock so
# only one worker thread rebuilds at a time; the set of dashboards is bounded by
# config, so the dict does not grow without bound.
_snapshot_body_cache: dict[str | None, tuple[float, str]] = {}
_snapshot_body_cache_lock = threading.Lock()


def _cached_snapshot_event_body(dashboard: str | None, ttl: float) -> str:
    """Return the snapshot body for *dashboard*, reusing a build newer than *ttl*.

    Within a ``ttl``-second window (one poll interval) concurrent SSE
    connections watching the same dashboard share a single storage read and
    serialization. A strict ``age < ttl`` comparison means a lone connection,
    whose ticks are spaced one interval apart, still rebuilds every tick — so
    the cache adds no latency in the common single-client case.
    """
    now = monotonic()
    with _snapshot_body_cache_lock:
        cached = _snapshot_body_cache.get(dashboard)
        if cached is not None and now - cached[0] < ttl:
            return cached[1]
        body = _snapshot_event_body(dashboard)
        _snapshot_body_cache[dashboard] = (monotonic(), body)
        return body


def _snapshot_error_payload(error: Exception) -> str:
    """Serialize an SSE ``snapshot-error`` payload for *error*.

    ``HTTPException`` carries a client-safe detail and status code; any other
    exception is reported generically (its message is not leaked to the client).
    """
    if isinstance(error, HTTPException):
        detail = error.detail if isinstance(error.detail, str) else "Unable to build snapshot."
        status_code = error.status_code
    else:
        detail = "Internal server error."
        status_code = 500
    return json.dumps({"detail": detail, "status_code": status_code})


async def _snapshot_event_generator(dashboard: str | None) -> AsyncIterator[ServerSentEventMessage]:
    """Yield SSE messages for *dashboard*, pushing only on change.

    Emits a ``snapshot`` event whenever the serialized payload differs from the
    last one sent, a ``snapshot-error`` event when the payload cannot be
    produced, and a comment-only keep-alive when nothing has changed for a while
    (so proxies do not drop an idle connection).  The blocking storage read runs
    in a worker thread to avoid stalling the event loop.

    Any error building the snapshot is reported to the client and the stream
    keeps running, recovering on a later tick; this avoids tearing down the
    connection (and triggering a client reconnection storm) on a transient
    storage or serialization failure.
    """
    interval = _sse_poll_interval()
    last_digest: str | None = None
    last_emit = monotonic()
    while True:
        try:
            body = await asyncio.to_thread(_cached_snapshot_event_body, dashboard, interval)
        except Exception as error:
            if not isinstance(error, HTTPException):
                logger.exception("Unexpected error building SSE snapshot")
            # A distinct event name (not "error") so it does not collide with
            # the EventSource connection-error event on the client.
            yield ServerSentEventMessage(data=_snapshot_error_payload(error), event="snapshot-error")
            last_digest = None
            last_emit = monotonic()
            await asyncio.sleep(interval)
            continue
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        now = monotonic()
        if digest != last_digest:
            last_digest = digest
            last_emit = now
            yield ServerSentEventMessage(data=body, event="snapshot")
        elif now - last_emit >= _SSE_KEEPALIVE_SECONDS:
            last_emit = now
            yield ServerSentEventMessage(comment="keep-alive")
        await asyncio.sleep(interval)


@get("/api/v1/events")
async def events(dashboard: str | None = None) -> ServerSentEvent:
    """Stream dashboard snapshots as Server-Sent Events.

    Replaces fixed-interval client polling: the connection stays open and the
    server pushes a ``snapshot`` event only when the data changes, cutting both
    latency and per-cycle overhead when nothing has happened.
    """
    return ServerSentEvent(_snapshot_event_generator(dashboard))
