"""Provider interfaces and shared context for enrichment."""

from __future__ import annotations

from typing import Protocol

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient, RequestContext
from corvix.types import JsonValue


class EnrichmentProvider(Protocol):
    """Protocol implemented by enrichment providers."""

    name: str

    def enrich(
        self,
        notification: Notification,
        client: JsonFetchClient,
        ctx: EnrichmentContext,
    ) -> dict[str, object]: ...


class EnrichmentContext(RequestContext):
    """Per-cycle provider context with request budget and URL cache."""

    def get_json(self, client: JsonFetchClient, url: str, timeout_seconds: float) -> JsonValue:
        """Fetch and cache a JSON payload for this cycle."""
        try:
            return super().get_json(client=client, url=url, timeout_seconds=timeout_seconds)
        except RuntimeError as error:
            if "budget exhausted" not in str(error).casefold():
                raise
            msg = "Enrichment request budget exhausted."
            raise RuntimeError(msg) from error
