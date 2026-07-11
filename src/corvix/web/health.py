"""Health endpoints and their supporting helpers.

Serves ``GET /api/v1/health`` (the versioned health check) and ``GET
/api/health`` (an unversioned, always-public alias kept so container health
checks — docker-compose, e2e, Lighthouse — need not track the API version).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

from litestar import Response, get
from litestar.exceptions import HTTPException

from corvix.domain import PollerStatus, parse_timestamp
from corvix.web.runtime_config import _load_runtime_config
from corvix.web.storage_provider import _get_storage

logger = logging.getLogger(__name__)


def _health_error(poller_status: PollerStatus) -> dict[str, object]:
    raw_detail: str | None = poller_status.last_error
    if isinstance(raw_detail, str):
        raw_detail = raw_detail.split("\n")[-1].strip() or raw_detail
    return {"status": "unhealthy", "reason": "poller_error", "detail": raw_detail}


def _health_check_staleness(last_poll_str: str) -> dict[str, object]:
    try:
        last_poll = parse_timestamp(last_poll_str)
    except ValueError:
        return {"status": "unhealthy", "reason": "invalid_poll_time"}
    staleness = datetime.now(tz=UTC) - last_poll
    if staleness > timedelta(minutes=5):
        return {
            "status": "unhealthy",
            "reason": "stale",
            "last_poll_seconds_ago": int(staleness.total_seconds()),
        }
    return {"status": "ok"}


def _read_health_poller_status() -> PollerStatus | dict[str, object]:
    """Resolve the poller status for the health check, or a failure payload."""
    try:
        _load_runtime_config()
    except HTTPException:
        return {"status": "unhealthy", "reason": "config_unavailable"}
    try:
        storage = _get_storage()
    except HTTPException:
        return {"status": "unhealthy", "reason": "storage_unavailable"}
    try:
        return storage.load_status()
    except (OSError, json.JSONDecodeError):
        return {"status": "unhealthy", "reason": "invalid_cache"}
    except Exception:
        logger.exception("Failed to read poller status from storage")
        return {"status": "unhealthy", "reason": "storage_unavailable"}


def _health_impl() -> Response[dict[str, object]]:
    """Compute and return the health check response.

    Both health endpoints are always public (issue #131), even when
    ``CORVIX_SECRET_TOKEN`` is set, so the response body is trimmed to a bare
    ``{"status": ...}`` — no ``reason``, ``detail``, or other internals that
    could leak service state to an unauthenticated caller. The full detail
    (``poller_status.last_error``, per-account errors, ...) remains available
    to authenticated clients via ``/api/v1/snapshot``.
    """
    poller_status = _read_health_poller_status()
    payload: dict[str, object]
    if isinstance(poller_status, dict):
        payload = poller_status
    elif poller_status.status == "error":
        payload = _health_error(poller_status)
    elif poller_status.status in {"unknown", "starting"}:
        payload = {"status": "unhealthy", "reason": "poller_not_running"}
    else:
        last_poll_str = poller_status.last_poll_time
        if not last_poll_str:
            payload = {"status": "unhealthy", "reason": "invalid_poll_time"}
        else:
            payload = _health_check_staleness(last_poll_str)
    status = payload.get("status", "unhealthy")
    status_code = HTTPStatus.OK if status == "ok" else HTTPStatus.SERVICE_UNAVAILABLE
    return Response(
        content={"status": status},
        status_code=int(status_code),
        media_type="application/json",
    )


@get("/api/v1/health")
def health() -> Response[dict[str, object]]:
    """Health endpoint for container checks.

    Returns 200 with {"status": "ok"} when config and storage are readable,
    the poller is running, and the poller's last poll time is not stale.
    Returns 503 with {"status": "unhealthy"} otherwise.

    This endpoint is always public, so the response carries no further
    detail; see the authenticated ``/api/v1/snapshot`` endpoint for
    poller error detail.
    """
    return _health_impl()


# ---------------------------------------------------------------------------
# /api/health — unversioned container-healthcheck alias (kept intentionally)
# ---------------------------------------------------------------------------
# docker-compose's healthcheck (and the e2e/Lighthouse harnesses) probe
# ``/api/health``.  It is a stable, always-public alias of ``/api/v1/health``
# kept so those container checks need not track the API version.  Every other
# unversioned ``/api/*`` alias was removed (see issue #127); the frontend uses
# ``/api/v1/*`` exclusively.


@get("/api/health")
def health_container() -> Response[dict[str, object]]:
    """Unversioned health alias for container healthchecks; see ``/api/v1/health``."""
    return _health_impl()
