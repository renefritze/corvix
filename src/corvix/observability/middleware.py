"""ASGI middleware recording per-request metrics, request IDs, and trace spans.

Sits outermost in the middleware stack so it observes every request (including
auth failures), tags each one with a ``request_id`` bound into the logging
context and echoed back in the ``X-Request-ID`` response header, and records
request counts and latency by method, endpoint, and status.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from uuid import uuid4

from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware

from corvix.observability import metrics
from corvix.observability.logging import bind_log_context, reset_log_context
from corvix.observability.tracing import span

if TYPE_CHECKING:
    from litestar.types.asgi_types import ASGIApp, Message, Receive, Scope, Send

_REQUEST_ID_HEADER = b"x-request-id"
_UNKNOWN_ENDPOINT = "unknown"


def _endpoint_label(scope: Scope) -> str:
    """Return a low-cardinality endpoint label from the matched route.

    Uses the registered path *template* (e.g. ``/api/v1/notifications/{account_id}/...``)
    rather than the concrete path so per-ID paths do not explode label cardinality.
    """
    route_handler = scope.get("route_handler")
    paths = getattr(route_handler, "paths", None)
    if paths:
        return min(paths)
    return _UNKNOWN_ENDPOINT


def _request_id(scope: Scope) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == _REQUEST_ID_HEADER:
            decoded = value.decode("latin-1").strip()
            if decoded:
                return decoded
    return uuid4().hex


class ObservabilityMiddleware(ASGIMiddleware):
    """Record request metrics, bind a request ID, and open a trace span."""

    scopes = (ScopeType.HTTP,)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Wrap the downstream app with metrics, logging context, and a span."""
        method = scope.get("method", "GET")
        request_id = _request_id(scope)
        request_id_bytes = request_id.encode("latin-1")
        status_code = 500
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = [h for h in message.get("headers", []) if h[0].lower() != _REQUEST_ID_HEADER]
                headers.append((_REQUEST_ID_HEADER, request_id_bytes))
                message["headers"] = headers
            await send(message)

        previous_context = bind_log_context(request_id=request_id)
        try:
            with span("http.request", {"http.request.method": method, "request_id": request_id}):
                await next_app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            try:
                endpoint = _endpoint_label(scope)
                metrics.http_requests_total.labels(method, endpoint, str(status_code)).inc()
                metrics.http_request_duration_seconds.labels(method, endpoint).observe(duration)
            finally:
                reset_log_context(previous_context)
