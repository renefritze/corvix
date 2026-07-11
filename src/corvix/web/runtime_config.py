"""Runtime ``AppConfig`` cache and dashboard selection helpers.

AppConfig is expensive to produce (YAML read + full parse).  We cache the
result at module level and invalidate it only when the config file's mtime
changes.  A plain stat() per request is orders of magnitude cheaper than a
full YAML re-parse, so we still detect on-disk edits without re-reading
unconditionally on every HTTP request.

The three cache fields live in a single mutable object so they can be
updated without ``global`` statements (which ruff PLW0603 flags).
"""

from __future__ import annotations

import logging
import signal
from os import environ
from pathlib import Path

from litestar.exceptions import HTTPException

from corvix.config import AppConfig, DashboardSpec, available_dashboards, load_config

logger = logging.getLogger(__name__)


class _ConfigCache:
    """Mutable container for the module-level AppConfig cache."""

    config: AppConfig | None = None
    path: str | None = None
    mtime: float | None = None


_config_cache = _ConfigCache()


def _clear_config_cache() -> None:
    """Discard the cached AppConfig so the next request reloads from disk."""
    _config_cache.config = None
    _config_cache.path = None
    _config_cache.mtime = None
    logger.info("Config cache cleared; config will be reloaded on the next request.")


def _load_runtime_config() -> AppConfig:
    """Return the cached AppConfig, re-parsing from disk only when the file changes.

    Config is read from the path in the ``CORVIX_CONFIG`` environment variable
    (default: ``corvix.yaml``).  The file's mtime is checked on every call; the
    YAML is only re-parsed when either the path or the mtime differs from the
    last successful load, eliminating redundant I/O on every request.
    """
    config_path = Path(environ.get("CORVIX_CONFIG", "corvix.yaml"))
    config_path_str = str(config_path)

    if not config_path.exists():
        msg = f"Config file '{config_path}' does not exist."
        raise HTTPException(status_code=500, detail=msg)

    try:
        mtime = config_path.stat().st_mtime
    except OSError as error:
        msg = f"Unable to read config at '{config_path}': {error}"
        raise HTTPException(status_code=500, detail=msg) from error

    if _config_cache.config is not None and _config_cache.path == config_path_str and _config_cache.mtime == mtime:
        return _config_cache.config

    try:
        config = load_config(config_path)
    except ValueError as error:
        msg = f"Invalid config at '{config_path}': {error}"
        raise HTTPException(status_code=500, detail=msg) from error
    except OSError as error:
        msg = f"Unable to read config at '{config_path}': {error}"
        raise HTTPException(status_code=500, detail=msg) from error

    _config_cache.config = config
    _config_cache.path = config_path_str
    _config_cache.mtime = mtime
    logger.debug("Config loaded from '%s' (mtime=%.3f).", config_path, mtime)
    return config


def _install_sighup_handler() -> None:
    """Register a SIGHUP handler that clears the config cache.

    Sending ``SIGHUP`` to the server process forces the config to be reloaded
    from disk on the next request without restarting the process::

        kill -HUP <pid>

    The handler is a no-op on platforms that do not support SIGHUP (e.g. Windows).
    """
    try:
        signal.signal(signal.SIGHUP, lambda _sig, _frame: _clear_config_cache())
        logger.debug("SIGHUP handler installed for config reload.")
    except (AttributeError, OSError):
        pass  # SIGHUP is not available on all platforms (e.g. Windows)


_install_sighup_handler()


def _select_dashboard(
    dashboards: list[DashboardSpec],
    selected_name: str | None,
) -> DashboardSpec:
    available = available_dashboards(dashboards)
    if selected_name is None:
        return available[0]
    for dashboard in available:
        if dashboard.name == selected_name:
            return dashboard
    msg = f"Dashboard '{selected_name}' not found."
    raise HTTPException(status_code=404, detail=msg)


def _dashboard_names(dashboards: list[DashboardSpec]) -> list[str]:
    available = available_dashboards(dashboards)
    return [dashboard.name for dashboard in available]
