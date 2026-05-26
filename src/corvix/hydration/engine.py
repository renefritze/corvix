"""Hydration engine — thin wrapper around :class:`~corvix.pipeline.engine.PipelineEngine`.

Kept for backward compatibility; new code should use
:class:`corvix.pipeline.engine.PipelineEngine` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.domain import Notification
from corvix.hydration.base import HydrationProvider
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.engine import PipelineEngine


@dataclass(slots=True)
class HydrationRunResult:
    """Result of hydrating one poll cycle."""

    notifications: list[Notification] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HydrationEngine:
    """Runs hydration providers over notifications.

    .. deprecated::
        Prefer :class:`corvix.pipeline.engine.PipelineEngine` directly.
        This class is a thin wrapper maintained for backward compatibility.
    """

    providers: list[HydrationProvider]
    max_requests_per_cycle: int = 25

    def run(
        self,
        notifications: list[Notification],
        client: JsonFetchClient,
        clients_by_account: dict[str, JsonFetchClient] | None = None,
    ) -> HydrationRunResult:
        engine = PipelineEngine(
            providers=list(self.providers),
            max_requests_per_cycle=self.max_requests_per_cycle,
        )
        result = engine.run(
            notifications=notifications,
            client=client,
            clients_by_account=clients_by_account,
        )
        return HydrationRunResult(notifications=result.notifications, errors=result.errors)
