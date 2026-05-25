"""Provider interfaces and shared context for hydration."""

from __future__ import annotations

from typing import Protocol

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient, RequestContext


class HydrationProvider(Protocol):
    """Protocol implemented by hydration providers."""

    name: str

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: HydrationContext) -> Notification: ...


class HydrationContext(RequestContext):
    """Per-cycle provider context with request budget and URL cache."""
