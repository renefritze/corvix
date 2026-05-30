"""Prometheus metrics for Corvix.

Defines the counters and histograms exported on the ``/metrics`` endpoint and
recorded throughout the poll cycle, GitHub API client, and web request path.
:func:`render_latest` produces the text exposition payload served to scrapers.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# --- Poll cycle ----------------------------------------------------------------

poll_cycles_total = Counter(
    "corvix_poll_cycles_total",
    "Number of poll cycles run, labelled by outcome.",
    ["result"],
)
poll_cycle_duration_seconds = Histogram(
    "corvix_poll_cycle_duration_seconds",
    "Wall-clock duration of a poll cycle in seconds.",
)
notifications_fetched_total = Counter(
    "corvix_notifications_fetched_total",
    "Total notifications fetched from GitHub across poll cycles.",
)
actions_taken_total = Counter(
    "corvix_actions_taken_total",
    "Total automation actions executed across poll cycles.",
)
poll_cycle_errors_total = Counter(
    "corvix_poll_cycle_errors_total",
    "Total poll cycles that raised an unhandled error.",
)

# --- GitHub API client ---------------------------------------------------------

github_api_requests_total = Counter(
    "corvix_github_api_requests_total",
    "GitHub API requests issued, labelled by HTTP method and outcome status.",
    ["method", "status"],
)
github_api_request_duration_seconds = Histogram(
    "corvix_github_api_request_duration_seconds",
    "Latency of GitHub API requests in seconds.",
    ["method"],
)

# --- Web requests --------------------------------------------------------------

http_requests_total = Counter(
    "corvix_http_requests_total",
    "HTTP requests served, labelled by method, endpoint, and status code.",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "corvix_http_request_duration_seconds",
    "Latency of HTTP requests in seconds, labelled by method and endpoint.",
    ["method", "endpoint"],
)


def render_latest() -> tuple[bytes, str]:
    """Return the Prometheus exposition payload and its content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
