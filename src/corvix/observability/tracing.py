"""Optional OpenTelemetry tracing for Corvix.

Tracing is opt-in: it requires the ``otel`` extra to be installed *and*
``CORVIX_OTEL_ENABLED`` to be truthy. When either is missing, :func:`span` is a
zero-overhead no-op so call sites never need to branch on availability.

The OTLP exporter honours the standard ``OTEL_*`` environment variables (e.g.
``OTEL_EXPORTER_OTLP_ENDPOINT``); only ``CORVIX_OTEL_ENABLED`` and an optional
service-name override are Corvix-specific.
"""

from __future__ import annotations

import atexit
import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from os import environ
from typing import Any

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when extra is absent
    _OTEL_AVAILABLE = False

_TRACER_NAME = "corvix"
_enabled = False


def _truthy(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    """Return whether tracing has been successfully configured."""
    return _enabled


def setup_tracing(service_name: str | None = None) -> bool:
    """Configure the global tracer provider when tracing is requested.

    Returns ``True`` when tracing is active afterwards. A no-op (returning
    ``False``) when ``CORVIX_OTEL_ENABLED`` is not truthy or the ``otel`` extra
    is not installed. Safe to call multiple times.
    """
    global _enabled  # noqa: PLW0603
    if _enabled:
        return True
    if not _truthy(environ.get("CORVIX_OTEL_ENABLED")):
        return False
    if not _OTEL_AVAILABLE:
        logger.warning("CORVIX_OTEL_ENABLED is set but the 'otel' extra is not installed; tracing disabled.")
        return False

    resolved_name = environ.get("OTEL_SERVICE_NAME") or service_name or "corvix"
    provider = TracerProvider(resource=Resource.create({"service.name": resolved_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    atexit.register(provider.shutdown)
    _enabled = True
    logger.info("OpenTelemetry tracing enabled", extra={"service_name": resolved_name})
    return True


@contextmanager
def span(name: str, attributes: Mapping[str, Any] | None = None) -> Iterator[Any]:
    """Start a span as the current context, or no-op when tracing is disabled.

    Yields the active span (or ``None`` when disabled). Exceptions raised in the
    block are recorded on the span and re-raised.
    """
    if not _enabled or not _OTEL_AVAILABLE:
        yield None
        return
    tracer = trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(name) as current_span:
        if attributes:
            for key, value in attributes.items():
                current_span.set_attribute(key, value)
        yield current_span
