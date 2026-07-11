"""Build the typed dashboard snapshot payload.

Shared by the ``GET /api/v1/snapshot`` route handler and the SSE event
generator so both produce an identical :class:`SnapshotResponse`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from corvix.dashboarding import build_dashboard_data
from corvix.domain import PollerStatus, parse_timestamp
from corvix.web.runtime_config import _dashboard_names, _load_runtime_config, _select_dashboard
from corvix.web.schemas import (
    AccountErrorResponse,
    PollerStatusResponse,
    SnapshotResponse,
    build_snapshot_response,
)
from corvix.web.storage_provider import _get_storage


def _snapshot_impl(dashboard: str | None = None) -> SnapshotResponse:
    """Compute and return the typed snapshot payload."""
    config = _load_runtime_config()
    storage = _get_storage()
    generated_at, records = storage.load_records()
    try:
        poller_status = storage.load_status()
    except (OSError, json.JSONDecodeError):
        poller_status = PollerStatus()
    selected_dashboard = _select_dashboard(config.dashboards, dashboard)
    data = build_dashboard_data(
        records=records,
        dashboard=selected_dashboard,
        generated_at=generated_at,
    )
    last_poll_str = poller_status.last_poll_time
    stale = False
    if last_poll_str:
        try:
            last_poll = parse_timestamp(last_poll_str)
            stale = (datetime.now(tz=UTC) - last_poll) > timedelta(minutes=5)
        except ValueError:
            stale = True
    else:
        stale = True
    raw_last_error: str | None = poller_status.last_error
    if isinstance(raw_last_error, str):
        raw_last_error = raw_last_error.split("\n")[-1].strip() or raw_last_error
    poller = PollerStatusResponse(
        status=poller_status.status,
        last_poll_time=last_poll_str,
        last_error=raw_last_error,
        last_error_time=poller_status.last_error_time,
        stale=stale,
        account_errors=[
            AccountErrorResponse(account_id=e.account_id, account_label=e.account_label, error=e.error)
            for e in poller_status.account_errors
        ],
    )
    return build_snapshot_response(
        data=data,
        dashboard_names=_dashboard_names(config.dashboards),
        poller=poller,
        notifications_config=config.notifications,
    )
