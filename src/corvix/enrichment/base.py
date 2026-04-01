"""Provider interfaces and shared context for enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from corvix.domain import Notification
from corvix.ingestion import GitHubNotificationsClient


class EnrichmentProvider(Protocol):
    """Protocol implemented by enrichment providers."""

    name: str

    def enrich(
        self,
        notification: Notification,
        client: GitHubNotificationsClient,
        ctx: EnrichmentContext,
    ) -> dict[str, object]: ...


@dataclass(slots=True)
class EnrichmentContext:
    """Per-cycle provider context with request budget and URL cache."""

    max_requests_per_cycle: int
    url_cache: dict[str, object] = field(default_factory=dict)
    request_count: int = 0

    def get_json(
        self,
        client: GitHubNotificationsClient,
        url: str,
        timeout_seconds: float,
    ) -> object:
        """Fetch and cache a JSON payload for this cycle."""
        if url in self.url_cache:
            return self.url_cache[url]
        if self.request_count >= self.max_requests_per_cycle:
            msg = "Enrichment request budget exhausted."
            raise RuntimeError(msg)
        payload = client.fetch_json_url(url=url, timeout_seconds=timeout_seconds)
        self.request_count += 1
        self.url_cache[url] = payload
        return payload
