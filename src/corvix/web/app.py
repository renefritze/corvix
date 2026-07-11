"""Litestar app serving Corvix dashboard data and UI.

This module is the thin assembly layer: it imports the route handlers from the
focused ``corvix.web.*`` modules, wires them into a single :class:`Litestar`
app with middleware and OpenAPI config, and exposes ``run()`` for ``corvix
serve`` / ``corvix-web``.  The route handlers and their business logic live in:

- ``routes_pages`` — SPA/index serving, login/logout, session cookies
- ``routes_api`` — ``/api/v1/*`` JSON handlers and ``/metrics``
- ``sse`` — the Server-Sent Events snapshot stream
- ``health`` — ``/api/v1/health`` and the ``/api/health`` container alias
- ``snapshot`` / ``rule_snippets`` / ``actions`` — API implementation helpers
- ``storage_provider`` / ``runtime_config`` / ``assets`` — shared state and assets
"""

from __future__ import annotations

from os import environ

import uvicorn
from litestar import Litestar
from litestar.config.compression import CompressionConfig
from litestar.openapi import OpenAPIConfig
from litestar.static_files import create_static_files_router

from corvix.env import get_env_value
from corvix.observability import configure_logging, setup_tracing
from corvix.observability.middleware import ObservabilityMiddleware
from corvix.web.assets import _ASSET_CACHE_CONTROL, _STATIC_ASSETS_DIR
from corvix.web.health import health, health_container
from corvix.web.middleware import TokenAuthMiddleware
from corvix.web.routes_api import (
    api_themes,
    dashboards,
    dismiss_notification,
    mark_notification_read,
    metrics_endpoint,
    notification_rule_snippets,
    snapshot,
)
from corvix.web.routes_pages import dashboard_index, index, login, login_page, logout
from corvix.web.sse import events


def _configure_observability() -> None:
    """Configure structured logging and optional tracing at app startup.

    Runs as a Litestar startup hook so it applies whether the app is launched
    via ``corvix serve`` or directly through ``uvicorn corvix.web.app:app``.
    """
    configure_logging()
    setup_tracing(service_name="corvix-web")


def _validate_secret_config() -> None:
    """Refuse to start when the secret token env vars are misconfigured.

    ``get_env_value`` cannot tell which of ``CORVIX_SECRET_TOKEN`` and
    ``CORVIX_SECRET_TOKEN_FILE`` should win when both are set. Failing fast
    here — rather than silently disabling auth at request time — is the
    preferred fix for the fail-open anti-pattern described in issue #128.
    """
    try:
        get_env_value("CORVIX_SECRET_TOKEN")
    except ValueError as error:
        raise RuntimeError(str(error)) from error


app = Litestar(
    route_handlers=[
        index,
        dashboard_index,
        login_page,
        login,
        logout,
        metrics_endpoint,
        # /api/v1/ — versioned routes (current)
        health,
        api_themes,
        dashboards,
        snapshot,
        events,
        notification_rule_snippets,
        dismiss_notification,
        mark_notification_read,
        # /api/health — unversioned container-healthcheck alias (kept intentionally)
        health_container,
        create_static_files_router(
            path="/assets",
            directories=[_STATIC_ASSETS_DIR],
            cache_control=_ASSET_CACHE_CONTROL,
        ),
    ],
    middleware=[ObservabilityMiddleware(), TokenAuthMiddleware()],
    on_startup=[_validate_secret_config, _configure_observability],
    compression_config=CompressionConfig(backend="gzip", minimum_size=500),
    openapi_config=OpenAPIConfig(
        title="Corvix API",
        # Schema version of the HTTP contract, not the package version: bumped
        # deliberately when the API shape changes so the generated OpenAPI
        # document (and the TypeScript types derived from it) stay stable.
        version="1.0.0",
        description="JSON API backing the Corvix dashboard single-page app.",
    ),
)


def run() -> None:
    """Run app with uvicorn."""
    host = environ.get("CORVIX_WEB_HOST", "0.0.0.0")  # nosec B104 - intentional; Docker/container deployments need all-interfaces
    port = int(environ.get("CORVIX_WEB_PORT", "8000"))
    reload_enabled = environ.get("CORVIX_WEB_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "corvix.web.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=["src"],
    )
