# Observability

Corvix ships with three complementary observability signals so you can run it
in production with confidence: **structured logging**, **Prometheus metrics**,
and **optional OpenTelemetry tracing**. All three are configured through
environment variables, so they fit cleanly into a Docker Compose or Kubernetes
deployment without touching `corvix.yaml`.

## Structured logging

Both the web service and the poller emit one JSON object per log line to
stdout. Every line carries a consistent schema:

```json
{"timestamp": "2026-05-26T21:44:53.105038+00:00", "level": "INFO", "logger": "corvix.services", "module": "services", "event": "poll cycle complete", "fetched": 12, "excluded": 3, "actions_taken": 1, "errors": 0}
```

- `timestamp` — UTC ISO-8601 timestamp.
- `level` — log level (`INFO`, `WARNING`, `ERROR`, …).
- `logger` / `module` — the originating logger name and module.
- `event` — the human-readable log message.
- Any extra fields passed at the call site (`fetched`, `request_id`, …) appear
  as top-level keys, so they are easy to index in a log pipeline.

During a web request, every log line is automatically tagged with the
`request_id` for that request (see [Request IDs](#request-ids)).

### Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `CORVIX_LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `CORVIX_LOG_FORMAT` | `json` | `json` for machine-readable output, or `console` for a human-friendly format during local development. |

## Prometheus metrics

The web service exposes a Prometheus endpoint at **`GET /metrics`**. It is
always public (no authentication required) so a scraper can reach it even when
`CORVIX_SECRET_TOKEN` is set, mirroring the `/api/health` endpoint.

```bash
curl http://localhost:8000/metrics
```

### Exported metrics

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `corvix_poll_cycles_total` | counter | `result` | Poll cycles run, by outcome (`success`/`error`). |
| `corvix_poll_cycle_duration_seconds` | histogram | — | Wall-clock duration of a poll cycle. |
| `corvix_notifications_fetched_total` | counter | — | Notifications fetched from GitHub. |
| `corvix_actions_taken_total` | counter | — | Automation actions executed. |
| `corvix_poll_cycle_errors_total` | counter | — | Poll cycles that raised an unhandled error. |
| `corvix_github_api_requests_total` | counter | `method`, `status` | GitHub API requests, by HTTP method and outcome (`success`, an HTTP status code, or `error`). |
| `corvix_github_api_request_duration_seconds` | histogram | `method` | GitHub API request latency. |
| `corvix_http_requests_total` | counter | `method`, `endpoint`, `status` | HTTP requests served, by route template and status code. |
| `corvix_http_request_duration_seconds` | histogram | `method`, `endpoint` | HTTP request latency. |

The `endpoint` label uses the matched **route template** (for example
`/api/v1/notifications/{account_id}/{thread_id}/dismiss`) rather than the
concrete path, so per-notification requests do not explode label cardinality.

### Scraping with Prometheus

```yaml
scrape_configs:
  - job_name: corvix
    static_configs:
      - targets: ["corvix-web:8000"]
```

The poller process records the poll-cycle and GitHub-API metrics but does not
expose its own HTTP endpoint; those counters are most useful on the web service
where `/metrics` is served. Poller health is also available via the
`corvix poller-health` command and the `/api/v1/health` endpoint.

## Request IDs

Every HTTP response includes an `X-Request-ID` header. If the incoming request
already carries an `X-Request-ID`, Corvix reuses it (so a request ID set by an
upstream reverse proxy flows through); otherwise a new one is generated. The
same ID is bound into the logging context, so all log lines emitted while
handling a request share a `request_id` field — making it straightforward to
correlate a user-visible error with its server-side logs.

## OpenTelemetry tracing (optional)

Tracing is **opt-in** and requires the `otel` extra to be installed:

```bash
uv sync --extra otel        # or: pip install "corvix[otel]"
```

Enable it by setting `CORVIX_OTEL_ENABLED=true`. Corvix creates spans for each
poll cycle (`poll_cycle`), each GitHub API request (`github.api.request`), and
each web request (`http.request`). Spans are exported over OTLP/HTTP using the
standard OpenTelemetry environment variables.

| Environment variable | Default | Description |
| --- | --- | --- |
| `CORVIX_OTEL_ENABLED` | `false` | Master switch for tracing. When false (or the `otel` extra is missing), tracing is a zero-overhead no-op. |
| `OTEL_SERVICE_NAME` | `corvix-web` / `corvix-poller` | Service name reported to your tracing backend. Takes precedence over the built-in default. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | OTLP/HTTP collector endpoint. |

Any other standard `OTEL_*` variable (headers, timeouts, resource attributes)
is honoured by the OpenTelemetry SDK directly.

### Example: export to a local collector

```bash
export CORVIX_OTEL_ENABLED=true
export OTEL_SERVICE_NAME=corvix-web
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
uvicorn corvix.web.app:app --host 0.0.0.0 --port 8000 --proxy-headers
```

When `CORVIX_OTEL_ENABLED` is unset the tracing code path adds no runtime
overhead, so it is safe to leave the instrumentation in place at all times.
