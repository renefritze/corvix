"""Enrichment engine — thin wrapper around :class:`~corvix.pipeline.engine.PipelineEngine`.

Kept for backward compatibility; new code should use
:class:`corvix.pipeline.engine.PipelineEngine` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.config import EnrichmentConfig
from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentProvider
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.engine import PipelineEngine


@dataclass(slots=True)
class EnrichmentRunResult:
    """Result of enriching one poll cycle."""

    contexts_by_notification_key: dict[str, dict[str, object]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def contexts_by_thread_id(self) -> dict[str, dict[str, object]]:
        """Backward-compatible thread-keyed view of contexts."""
        return {key.rpartition(":")[2]: value for key, value in self.contexts_by_notification_key.items()}


@dataclass(slots=True)
class EnrichmentEngine:
    """Runs configured enrichment providers over notifications.

    .. deprecated::
        Prefer :class:`corvix.pipeline.engine.PipelineEngine` directly.
        This class is a thin wrapper maintained for backward compatibility.
    """

    config: EnrichmentConfig
    providers: list[EnrichmentProvider]

    def run(
        self,
        notifications: list[Notification],
        client: JsonFetchClient,
        clients_by_account: dict[str, JsonFetchClient] | None = None,
    ) -> EnrichmentRunResult:
        """Run enabled providers for all notifications in one cycle."""
        if not self.config.enabled or not self.providers:
            return EnrichmentRunResult(
                contexts_by_notification_key={
                    f"{notification.account_id}:{notification.thread_id}": {} for notification in notifications
                },
                errors=[],
            )

        engine = PipelineEngine(
            providers=list(self.providers),
            max_requests_per_cycle=self.config.max_requests_per_cycle,
        )
        result = engine.run(
            notifications=notifications,
            client=client,
            clients_by_account=clients_by_account,
        )
        return EnrichmentRunResult(
            contexts_by_notification_key=result.contexts_by_notification_key,
            errors=result.errors,
        )
