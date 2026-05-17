"""Hydration engine for completing canonical notification fields."""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.domain import Notification
from corvix.hydration.base import HydrationContext, HydrationProvider
from corvix.pipeline.base import JsonFetchClient


@dataclass(slots=True)
class HydrationRunResult:
    """Result of hydrating one poll cycle."""

    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HydrationEngine:
    """Runs hydration providers over notifications."""

    providers: list[HydrationProvider]
    max_requests_per_cycle: int = 25

    def run(
        self,
        notifications: list[Notification],
        client: JsonFetchClient,
        clients_by_account: dict[str, JsonFetchClient] | None = None,
    ) -> HydrationRunResult:
        if not self.providers:
            return HydrationRunResult(errors=[])

        context = HydrationContext(max_requests_per_cycle=self.max_requests_per_cycle)
        errors: list[str] = []
        for notification in notifications:
            notification_client = (
                clients_by_account.get(notification.account_id, client) if clients_by_account else client
            )
            for provider in self.providers:
                try:
                    provider.hydrate(notification=notification, client=notification_client, ctx=context)
                except Exception as error:  # pragma: no cover - defensive fail-open contract
                    errors.append(f"provider={provider.name} thread={notification.thread_id}: {error}")
        return HydrationRunResult(errors=errors)
