"""Enrichment engine for attaching contextual data to notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from corvix.config import EnrichmentConfig
from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentContext, EnrichmentProvider
from corvix.ingestion import GitHubNotificationsClient


@dataclass(slots=True)
class EnrichmentRunResult:
    """Result of enriching one poll cycle."""

    contexts_by_thread_id: dict[str, dict[str, object]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EnrichmentEngine:
    """Runs configured enrichment providers over notifications."""

    config: EnrichmentConfig
    providers: list[EnrichmentProvider]

    def run(
        self,
        notifications: list[Notification],
        client: GitHubNotificationsClient,
    ) -> EnrichmentRunResult:
        """Run enabled providers for all notifications in one cycle."""
        if not self.config.enabled or not self.providers:
            return EnrichmentRunResult(
                contexts_by_thread_id={notification.thread_id: {} for notification in notifications},
                errors=[],
            )

        context = EnrichmentContext(max_requests_per_cycle=self.config.max_requests_per_cycle)
        contexts_by_thread_id: dict[str, dict[str, object]] = {
            notification.thread_id: {} for notification in notifications
        }
        errors: list[str] = []
        for notification in notifications:
            record_context = contexts_by_thread_id[notification.thread_id]
            for provider in self.providers:
                try:
                    payload = provider.enrich(notification=notification, client=client, ctx=context)
                except Exception as error:  # pragma: no cover - defensive fail-open contract
                    errors.append(f"provider={provider.name} thread={notification.thread_id}: {error}")
                    continue
                if payload:
                    _set_nested_namespace(record_context, provider.name, payload)
        return EnrichmentRunResult(contexts_by_thread_id=contexts_by_thread_id, errors=errors)


def _set_nested_namespace(root: dict[str, object], namespace: str, payload: dict[str, object]) -> None:
    """Merge payload under a dot-delimited namespace."""
    segments = [segment for segment in namespace.split(".") if segment]
    if not segments:
        return
    node: dict[str, object] = root
    for segment in segments[:-1]:
        raw_child = node.get(segment)
        if not isinstance(raw_child, dict):
            child = {}
            node[segment] = child
            node = child
            continue
        node = cast(dict[str, object], raw_child)

    leaf = segments[-1]
    existing = node.get(leaf)
    if isinstance(existing, dict):
        existing_map = cast(dict[str, object], existing)
        existing_map.update(payload)
        return
    node[leaf] = dict(payload)
