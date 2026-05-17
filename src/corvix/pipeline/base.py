"""Shared request primitives for hydration and enrichment pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from corvix.types import JsonValue


class JsonFetchClient(Protocol):
    """Client capability required by data-enrichment pipelines."""

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        """Fetch JSON from a fully-qualified API URL."""
        ...


@dataclass(slots=True)
class RequestContext:
    """Per-cycle request budget and URL cache."""

    max_requests_per_cycle: int
    url_cache: dict[str, JsonValue] = field(default_factory=dict)
    request_count: int = 0

    def get_json(self, client: JsonFetchClient, url: str, timeout_seconds: float) -> JsonValue:
        """Fetch and cache a JSON payload for this cycle."""
        if url in self.url_cache:
            return self.url_cache[url]
        if self.request_count >= self.max_requests_per_cycle:
            msg = "Request budget exhausted."
            raise RuntimeError(msg)
        payload = client.fetch_json_url(url=url, timeout_seconds=timeout_seconds)
        self.request_count += 1
        self.url_cache[url] = payload
        return payload
