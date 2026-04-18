"""Litestar app serving Corvix dashboard data and UI."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict
from importlib.resources import files
from os import environ
from pathlib import Path

import uvicorn
from litestar import Litestar, Response, get, post
from litestar.config.compression import CompressionConfig
from litestar.datastructures.headers import CacheControlHeader
from litestar.exceptions import HTTPException
from litestar.static_files import create_static_files_router

from corvix.config import AppConfig, DashboardSpec, GitHubAccountConfig, load_config
from corvix.dashboarding import build_dashboard_data
from corvix.env import get_env_value
from corvix.ingestion import GitHubNotificationsClient
from corvix.storage import NotificationCache

logger = logging.getLogger(__name__)

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

_STATIC_ROOT = files("corvix.web").joinpath("static")
_STATIC_ASSETS_DIR = str(_STATIC_ROOT.joinpath("assets"))
_ASSET_FILENAMES = ("app.js", "index.css", "favicon.svg")
_ASSET_CACHE_CONTROL = CacheControlHeader(public=True, max_age=31536000, immutable=True)


def _asset_version_token() -> str:
    digest = hashlib.sha256()
    found_asset = False
    for asset_name in _ASSET_FILENAMES:
        asset_file = _STATIC_ROOT.joinpath("assets", asset_name)
        if not asset_file.is_file():
            continue
        found_asset = True
        digest.update(asset_name.encode("utf-8"))
        digest.update(asset_file.read_bytes())
    if not found_asset:
        return "dev"
    return digest.hexdigest()[:12]


_INDEX_HTML_TEMPLATE = _STATIC_ROOT.joinpath("index.html").read_text(encoding="utf-8")
INDEX_HTML = _INDEX_HTML_TEMPLATE.replace("__ASSET_VERSION__", _asset_version_token())


@get("/", sync_to_thread=False)
def index() -> Response[str]:
    """Serve the dashboard single-page UI."""
    return Response(content=INDEX_HTML, media_type="text/html")


@get("/dashboards/{dashboard_name:str}", sync_to_thread=False)
def dashboard_index(dashboard_name: str) -> Response[str]:
    """Serve the dashboard SPA for bookmarkable dashboard URLs."""
    del dashboard_name
    return Response(content=INDEX_HTML, media_type="text/html")


@get("/api/health", sync_to_thread=False)
def health() -> dict[str, str]:
    """Health endpoint for container checks."""
    return {"status": "ok"}


@get("/api/themes", sync_to_thread=False)
def api_themes() -> dict[str, object]:
    """Return available theme presets."""
    return {"themes": THEMES}


@get("/api/dashboards", sync_to_thread=False)
def dashboards() -> dict[str, object]:
    """List configured dashboard names."""
    config = _load_runtime_config()
    names = _dashboard_names(config.dashboards)
    return {"dashboard_names": names}


@get("/api/snapshot", sync_to_thread=False)
def snapshot(dashboard: str | None = None) -> dict[str, object]:
    """Return the selected dashboard data from cache."""
    config = _load_runtime_config()
    generated_at, records = NotificationCache(path=config.resolve_cache_file()).load()
    selected_dashboard = _select_dashboard(config.dashboards, dashboard)
    data = build_dashboard_data(
        records=records,
        dashboard=selected_dashboard,
        generated_at=generated_at,
    )
    payload = asdict(data)
    payload["dashboard_names"] = _dashboard_names(config.dashboards)
    notif_cfg = config.notifications
    payload["notifications_config"] = {
        "enabled": notif_cfg.enabled,
        "browser_tab": {
            "enabled": notif_cfg.browser_tab.enabled,
            "max_per_cycle": notif_cfg.browser_tab.max_per_cycle,
            "cooldown_seconds": notif_cfg.browser_tab.cooldown_seconds,
        },
    }
    return payload


@post("/api/notifications/{account_id:str}/{thread_id:str}/dismiss", sync_to_thread=True)
def dismiss_notification(account_id: str, thread_id: str) -> Response[None]:
    """Dismiss a notification thread (removes it from the GitHub inbox).

    Calls DELETE /notifications/threads/{id} on GitHub, then marks the record
    as dismissed in local storage. Returns 204 No Content on success.
    """
    return _dismiss_notification_impl(account_id=account_id, thread_id=thread_id)


@post("/api/notifications/{thread_id:str}/dismiss", sync_to_thread=True)
def dismiss_notification_default_account(thread_id: str) -> Response[None]:
    """Backward-compatible dismiss endpoint for default account."""
    config = _load_runtime_config()
    return _dismiss_notification_impl(account_id=_default_account_id(config), thread_id=thread_id)


@post("/api/notifications/{account_id:str}/{thread_id:str}/mark-read", sync_to_thread=True)
def mark_notification_read(account_id: str, thread_id: str) -> Response[None]:
    """Mark a notification thread as read in GitHub and local storage."""
    return _mark_notification_read_impl(account_id=account_id, thread_id=thread_id)


@post("/api/notifications/{thread_id:str}/mark-read", sync_to_thread=True)
def mark_notification_read_default_account(thread_id: str) -> Response[None]:
    """Backward-compatible mark-read endpoint for default account."""
    config = _load_runtime_config()
    return _mark_notification_read_impl(account_id=_default_account_id(config), thread_id=thread_id)


def _dismiss_notification_impl(account_id: str, thread_id: str) -> Response[None]:
    config = _load_runtime_config()
    account = _require_account(config=config, account_id=account_id)
    try:
        token = get_env_value(account.token_env)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    if not token:
        msg = f"GitHub token env var '{account.token_env}' (or '{account.token_env}_FILE') is not set."
        raise HTTPException(status_code=500, detail=msg)
    client = GitHubNotificationsClient(token=token, api_base_url=account.api_base_url)
    try:
        client.dismiss_thread(thread_id)
    except Exception as error:
        logger.exception("Failed to dismiss thread", extra={"thread_id": thread_id})
        msg = f"Failed to dismiss thread {thread_id}: {error}"
        raise HTTPException(status_code=502, detail=msg) from error

    cache = NotificationCache(path=config.resolve_cache_file())
    cache.dismiss_record(user_id="", account_id=account_id, thread_id=thread_id)
    return Response(content=None, status_code=204)


def _mark_notification_read_impl(account_id: str, thread_id: str) -> Response[None]:
    config = _load_runtime_config()
    account = _require_account(config=config, account_id=account_id)
    try:
        token = get_env_value(account.token_env)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    if not token:
        msg = f"GitHub token env var '{account.token_env}' (or '{account.token_env}_FILE') is not set."
        raise HTTPException(status_code=500, detail=msg)

    client = GitHubNotificationsClient(token=token, api_base_url=account.api_base_url)
    try:
        client.mark_thread_read(thread_id)
    except Exception as error:
        logger.exception("Failed to mark thread as read", extra={"thread_id": thread_id})
        msg = f"Failed to mark thread {thread_id} as read."
        raise HTTPException(status_code=502, detail=msg) from error

    cache = NotificationCache(path=config.resolve_cache_file())
    cache.mark_record_read(user_id="", account_id=account_id, thread_id=thread_id)
    return Response(content=None, status_code=204)


def _require_account(config: AppConfig, account_id: str) -> GitHubAccountConfig:
    for account in config.github.accounts:
        if account.id == account_id:
            return account
    msg = f"GitHub account '{account_id}' not found in config."
    raise HTTPException(status_code=404, detail=msg)


def _default_account_id(config: AppConfig) -> str:
    if not config.github.accounts:
        msg = "No GitHub accounts configured."
        raise HTTPException(status_code=500, detail=msg)
    return config.github.accounts[0].id


def _load_runtime_config() -> AppConfig:
    config_path = Path(environ.get("CORVIX_CONFIG", "corvix.yaml"))
    if not config_path.exists():
        msg = f"Config file '{config_path}' does not exist."
        raise HTTPException(status_code=500, detail=msg)
    try:
        return load_config(config_path)
    except ValueError as error:
        msg = f"Invalid config at '{config_path}': {error}"
        raise HTTPException(status_code=500, detail=msg) from error


def _select_dashboard(
    dashboards: list[DashboardSpec],
    selected_name: str | None,
) -> DashboardSpec:
    available = dashboards or [DashboardSpec(name="default", group_by="repository", sort_by="score")]
    if selected_name is None:
        return available[0]
    for dashboard in available:
        if dashboard.name == selected_name:
            return dashboard
    msg = f"Dashboard '{selected_name}' not found."
    raise HTTPException(status_code=404, detail=msg)


def _dashboard_names(dashboards: list[DashboardSpec]) -> list[str]:
    available = dashboards or [DashboardSpec(name="default", group_by="repository", sort_by="score")]
    return [dashboard.name for dashboard in available]


app = Litestar(
    route_handlers=[
        index,
        dashboard_index,
        health,
        api_themes,
        dashboards,
        snapshot,
        dismiss_notification,
        dismiss_notification_default_account,
        mark_notification_read,
        mark_notification_read_default_account,
        create_static_files_router(
            path="/assets",
            directories=[_STATIC_ASSETS_DIR],
            cache_control=_ASSET_CACHE_CONTROL,
        ),
    ],
    compression_config=CompressionConfig(backend="gzip", minimum_size=500),
)


def run() -> None:
    """Run app with uvicorn."""
    host = environ.get("CORVIX_WEB_HOST", "0.0.0.0")
    port = int(environ.get("CORVIX_WEB_PORT", "8000"))
    reload_enabled = environ.get("CORVIX_WEB_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "corvix.web.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=["src"],
    )
