"""Shared request primitives for hydration and enrichment pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from corvix.types import JsonValue


class JsonFetchClient(Protocol):
    """Client capability required by data-enrichment pipelines."""

    api_base_url: str
    """Trusted base URL of the upstream API (e.g. ``https://api.github.com``).

    Providers use this to construct upstream API URLs from trusted config rather
    than from data received in API responses, which prevents SSRF taint flows.
    """

    account_id: str
    """Identifies which account's credentials this client authenticates requests with.

    Used to scope the per-cycle URL cache (see :class:`RequestContext`) so a
    payload fetched with one account's token is never served to another
    account's notification.
    """

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        """Fetch JSON from a fully-qualified API URL."""
        ...


@dataclass(slots=True)
class RequestContext:
    """Per-cycle request budget and URL cache, scoped per account."""

    max_requests_per_cycle: int
    url_cache: dict[tuple[str, str], JsonValue] = field(default_factory=dict)
    request_count: int = 0

    def get_json(self, client: JsonFetchClient, url: str, timeout_seconds: float) -> JsonValue:
        """Fetch and cache a JSON payload for this cycle.

        The cache is keyed by ``(client.account_id, url)`` rather than by URL
        alone, so a payload fetched under one account's token is never handed
        back to a request made on behalf of a different account, even when
        two accounts share the same URL (e.g. both watching the same repo).
        """
        key = (client.account_id, url)
        if key in self.url_cache:
            return self.url_cache[key]
        if self.request_count >= self.max_requests_per_cycle:
            msg = "Request budget exhausted."
            raise RuntimeError(msg)
        payload = client.fetch_json_url(url=url, timeout_seconds=timeout_seconds)
        self.request_count += 1
        self.url_cache[key] = payload
        return payload
