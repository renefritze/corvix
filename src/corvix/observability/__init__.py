"""Observability for Corvix: structured logging, Prometheus metrics, OTel tracing.

* Structured JSON logging via :func:`configure_logging` (always available).
* Prometheus metrics via the :mod:`corvix.observability.metrics` module and the
  ``/metrics`` web endpoint.
* Optional OpenTelemetry tracing via :func:`setup_tracing` and :func:`span`
  (requires the ``otel`` extra and ``CORVIX_OTEL_ENABLED``).
"""

from __future__ import annotations

from corvix.observability.logging import (
    bind_log_context,
    configure_logging,
    reset_log_context,
)
from corvix.observability.tracing import is_enabled, setup_tracing, span

__all__ = [
    "bind_log_context",
    "configure_logging",
    "is_enabled",
    "reset_log_context",
    "setup_tracing",
    "span",
]
