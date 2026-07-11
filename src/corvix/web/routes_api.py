"""Versioned ``/api/v1/*`` JSON route handlers (plus ``/metrics``).

Thin decorated handlers that delegate to the implementation helpers in
``snapshot``, ``rule_snippets``, and ``actions``; this module owns only the
HTTP surface (paths, verbs, response types) and the theme presets.
"""

from __future__ import annotations

from litestar import Response, get, post

from corvix.observability import metrics as _metrics
from corvix.web.actions import _dismiss_notification_impl, _mark_notification_read_impl
from corvix.web.rule_snippets import _notification_rule_snippets_impl
from corvix.web.runtime_config import _dashboard_names, _load_runtime_config
from corvix.web.schemas import RuleSnippetsResponse, SnapshotResponse
from corvix.web.snapshot import _snapshot_impl

THEMES: dict[str, dict[str, str]] = {
    "midnight": {
        "bg": "#07111f",
        "surface": "#0e1a2b",
        "surface_elevated": "#132238",
        "ink": "#edf3ff",
        "muted": "#8fa3c7",
        "accent": "#74c0fc",
        "line": "#223753",
        "ok": "#59d7a4",
        "danger": "#ff7b72",
    },
    "graphite": {
        "bg": "#0d1117",
        "surface": "#161b22",
        "surface_elevated": "#1f2937",
        "ink": "#f5f7fb",
        "muted": "#95a3b8",
        "accent": "#f2cc60",
        "line": "#2d3748",
        "ok": "#56d364",
        "danger": "#ff938a",
    },
}


@get("/metrics", sync_to_thread=False)
def metrics_endpoint() -> Response[bytes]:
    """Expose Prometheus metrics in text exposition format for scraping."""
    payload, content_type = _metrics.render_latest()
    # Litestar appends "; charset=utf-8" to text media types, so strip any
    # charset already present in the Prometheus content type to avoid a duplicate.
    media_type = content_type.split("; charset=", 1)[0]
    return Response(content=payload, media_type=media_type)


@get("/api/v1/themes", sync_to_thread=False)
def api_themes() -> dict[str, object]:
    """Return available theme presets."""
    return {"themes": THEMES}


@get("/api/v1/dashboards")
def dashboards() -> dict[str, object]:
    """List configured dashboard names."""
    config = _load_runtime_config()
    names = _dashboard_names(config.dashboards)
    return {"dashboard_names": names}


@get("/api/v1/snapshot")
def snapshot(dashboard: str | None = None) -> SnapshotResponse:
    """Return the selected dashboard data from storage."""
    return _snapshot_impl(dashboard=dashboard)


@get("/api/v1/notifications/{account_id:str}/{thread_id:str}/rule-snippets")
def notification_rule_snippets(
    account_id: str,
    thread_id: str,
    dashboard: str | None = None,
) -> RuleSnippetsResponse:
    """Return prefilled ignore-rule snippets for a notification."""
    return _notification_rule_snippets_impl(account_id=account_id, thread_id=thread_id, dashboard=dashboard)


@post("/api/v1/notifications/{account_id:str}/{thread_id:str}/dismiss", sync_to_thread=True)
def dismiss_notification(account_id: str, thread_id: str) -> Response[None]:
    """Dismiss a notification thread (removes it from the GitHub inbox).

    Calls DELETE /notifications/threads/{id} on GitHub, then marks the record
    as dismissed in local storage. Returns 204 No Content on success.
    """
    return _dismiss_notification_impl(account_id=account_id, thread_id=thread_id)


@post("/api/v1/notifications/{account_id:str}/{thread_id:str}/mark-read", sync_to_thread=True)
def mark_notification_read(account_id: str, thread_id: str) -> Response[None]:
    """Mark a notification thread as read in GitHub and local storage."""
    return _mark_notification_read_impl(account_id=account_id, thread_id=thread_id)
