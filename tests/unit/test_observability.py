"""Unit tests for the observability package: logging, metrics, and tracing."""

from __future__ import annotations

import json
import logging
import sys
from types import SimpleNamespace

import pytest

from corvix.observability import logging as obs_logging
from corvix.observability import metrics, tracing
from corvix.observability.logging import (
    JsonFormatter,
    bind_log_context,
    configure_logging,
    reset_log_context,
)
from corvix.observability.middleware import _endpoint_label, _request_id


def _make_record(message: str = "hello", *, level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord(
        name="corvix.test",
        level=level,
        pathname=__file__,
        lineno=10,
        msg=message,
        args=(),
        exc_info=None,
    )


class TestJsonFormatter:
    def test_emits_core_schema_fields(self) -> None:
        payload = json.loads(JsonFormatter().format(_make_record("started")))
        assert payload["event"] == "started"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "corvix.test"
        assert "timestamp" in payload
        assert "module" in payload

    def test_includes_extra_fields(self) -> None:
        record = _make_record()
        record.fetched = 7  # type: ignore[attr-defined]
        payload = json.loads(JsonFormatter().format(record))
        assert payload["fetched"] == 7

    def test_formats_message_args(self) -> None:
        record = logging.LogRecord(
            name="corvix.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="count=%d",
            args=(3,),
            exc_info=None,
        )
        assert json.loads(JsonFormatter().format(record))["event"] == "count=3"

    def test_serialises_exception_info(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord(
                name="corvix.test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=10,
                msg="failed",
                args=(),
                exc_info=sys.exc_info(),
            )
        payload = json.loads(JsonFormatter().format(record))
        assert "ValueError" in payload["exc_info"]

    def test_serialises_stack_info(self) -> None:
        record = _make_record()
        record.stack_info = "Stack (most recent call last):\n  frame"
        payload = json.loads(JsonFormatter().format(record))
        assert "Stack" in payload["stack_info"]


class TestLogContext:
    def test_bind_and_reset_context(self) -> None:
        token = bind_log_context(request_id="rid-9")
        try:
            payload = json.loads(JsonFormatter().format(_make_record()))
            assert payload["request_id"] == "rid-9"
        finally:
            reset_log_context(token)
        payload_after = json.loads(JsonFormatter().format(_make_record()))
        assert "request_id" not in payload_after


class TestConfigureLogging:
    def test_installs_single_handler_and_is_idempotent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(obs_logging, "_handler", None)
        root = logging.getLogger()
        existing = list(root.handlers)
        try:
            configure_logging(level="DEBUG")
            assert obs_logging._handler is not None
            handler = obs_logging._handler
            assert handler in root.handlers
            assert root.level == logging.DEBUG
            # Second call must not stack another handler.
            configure_logging(level="WARNING")
            assert obs_logging._handler is handler
            assert root.handlers.count(handler) == 1
            assert handler.level == logging.WARNING
        finally:
            if obs_logging._handler is not None and obs_logging._handler not in existing:
                root.removeHandler(obs_logging._handler)
            monkeypatch.setattr(obs_logging, "_handler", None)

    def test_console_format_uses_plain_formatter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(obs_logging, "_handler", None)
        root = logging.getLogger()
        existing = list(root.handlers)
        try:
            configure_logging(level="INFO", log_format="console")
            assert not isinstance(obs_logging._handler.formatter, JsonFormatter)
        finally:
            if obs_logging._handler is not None and obs_logging._handler not in existing:
                root.removeHandler(obs_logging._handler)
            monkeypatch.setattr(obs_logging, "_handler", None)


class TestMetrics:
    def test_render_latest_returns_text_payload(self) -> None:
        payload, content_type = metrics.render_latest()
        assert content_type.startswith("text/plain")
        assert b"corvix_poll_cycles_total" in payload

    def test_counter_increment_appears_in_output(self) -> None:
        metrics.github_api_requests_total.labels("GET", "418").inc()
        payload, _ = metrics.render_latest()
        assert 'corvix_github_api_requests_total{method="GET",status="418"}' in payload.decode()


class TestTracingDisabled:
    def test_is_disabled_by_default(self) -> None:
        assert tracing.is_enabled() is False

    def test_setup_returns_false_when_not_requested(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CORVIX_OTEL_ENABLED", raising=False)
        assert tracing.setup_tracing() is False

    def test_span_is_noop_when_disabled(self) -> None:
        with tracing.span("noop", {"k": "v"}) as current:
            assert current is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("true", True), ("1", True), ("YES", True), ("off", False), ("", False), (None, False)],
    )
    def test_truthy(self, value: str | None, expected: bool) -> None:
        assert tracing._truthy(value) is expected

    def test_setup_warns_when_extra_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORVIX_OTEL_ENABLED", "true")
        monkeypatch.setattr(tracing, "_enabled", False)
        monkeypatch.setattr(tracing, "_OTEL_AVAILABLE", False)
        assert tracing.setup_tracing() is False

    def test_setup_returns_true_when_already_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(tracing, "_enabled", True)
        assert tracing.setup_tracing() is True


class TestTracingEnabled:
    def test_setup_and_span_record(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("opentelemetry.sdk.trace.export.in_memory_span_exporter")
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: PLC0415
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: PLC0415
            InMemorySpanExporter,
        )

        exporter = InMemorySpanExporter()
        monkeypatch.setenv("CORVIX_OTEL_ENABLED", "true")
        monkeypatch.setattr(tracing, "_enabled", False)
        monkeypatch.setattr(tracing, "OTLPSpanExporter", lambda: exporter)
        monkeypatch.setattr(tracing, "BatchSpanProcessor", SimpleSpanProcessor)
        try:
            assert tracing.setup_tracing(service_name="corvix-test") is True
            assert tracing.is_enabled() is True
            with tracing.span("unit-span", {"attr": "value"}) as current:
                assert current is not None
            names = [span.name for span in exporter.get_finished_spans()]
            assert "unit-span" in names
        finally:
            monkeypatch.setattr(tracing, "_enabled", False)


class TestEndpointLabel:
    def test_uses_route_template(self) -> None:
        scope = {"route_handler": SimpleNamespace(paths={"/api/v1/snapshot"})}
        assert _endpoint_label(scope) == "/api/v1/snapshot"

    def test_falls_back_to_unknown(self) -> None:
        assert _endpoint_label({}) == "unknown"


class TestRequestId:
    def test_reads_inbound_header(self) -> None:
        scope = {"headers": [(b"x-request-id", b"abc-1")]}
        assert _request_id(scope) == "abc-1"

    def test_generates_when_absent(self) -> None:
        generated = _request_id({"headers": []})
        assert len(generated) == 32
