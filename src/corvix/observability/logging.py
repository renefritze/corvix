"""Structured JSON logging for Corvix.

Provides :func:`configure_logging`, which installs a single stdout handler on
the root logger emitting one JSON object per line with a consistent schema:
``timestamp``, ``level``, ``logger``, ``module``, ``event`` and any extra
fields passed via ``logger.*(..., extra={...})``.

A :mod:`contextvars`-based context (see :func:`bind_log_context`) lets request
scoped fields such as ``request_id`` be attached to every log line emitted while
handling a request without threading them through every call.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from os import environ

# Standard ``logging.LogRecord`` attributes; anything else attached to a record
# (via ``extra={...}``) is treated as a structured field and serialised.
_RESERVED_RECORD_KEYS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

_log_context: ContextVar[dict[str, object] | None] = ContextVar("corvix_log_context", default=None)

_LOG_FORMAT_JSON = "json"
_LOG_FORMAT_CONSOLE = "console"

# The handler installed by :func:`configure_logging`; reused across calls so we
# never stack duplicate handlers (e.g. uvicorn reload, multiple CLI commands).
_handler: logging.Handler | None = None


def _current_context() -> dict[str, object]:
    return _log_context.get() or {}


def bind_log_context(**fields: object) -> dict[str, object] | None:
    """Merge *fields* into the current logging context and return the previous one.

    The returned value should be passed to :func:`reset_log_context` to restore
    the prior state (typically in a ``finally`` block).
    """
    previous = _log_context.get()
    _log_context.set({**(previous or {}), **fields})
    return previous


def reset_log_context(previous: dict[str, object] | None) -> None:
    """Restore a logging context previously returned by :func:`bind_log_context`."""
    _log_context.set(previous)


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "event": record.getMessage(),
        }
        payload.update(_current_context())
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str)


def _build_handler(log_format: str) -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stdout)
    if log_format == _LOG_FORMAT_CONSOLE:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s"))
    else:
        handler.setFormatter(JsonFormatter())
    return handler


def configure_logging(level: str | None = None, log_format: str | None = None) -> None:
    """Install the structured logging handler on the root logger.

    ``level`` defaults to ``CORVIX_LOG_LEVEL`` (then ``INFO``) and ``log_format``
    to ``CORVIX_LOG_FORMAT`` (then ``json``; ``console`` selects a human-readable
    formatter for local development). Safe to call multiple times — the Corvix
    handler is only installed once.
    """
    global _handler  # noqa: PLW0603
    resolved_level = (level or environ.get("CORVIX_LOG_LEVEL", "INFO")).upper()
    resolved_format = (log_format or environ.get("CORVIX_LOG_FORMAT", _LOG_FORMAT_JSON)).lower()

    root = logging.getLogger()
    root.setLevel(resolved_level)

    if _handler is not None:
        _handler.setLevel(resolved_level)
        return

    _handler = _build_handler(resolved_format)
    _handler.setLevel(resolved_level)
    root.addHandler(_handler)
