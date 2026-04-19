"""Enrichment engine for attaching contextual data to notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeIs

from corvix.config import EnrichmentConfig
from corvix.domain import Notification
from corvix.enrichment.base import EnrichmentContext, EnrichmentProvider, JsonFetchClient


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


@dataclass(slots=True)
class EnrichmentRunResult:
    """Result of enriching one poll cycle."""

    contexts_by_notification_key: dict[str, dict[str, object]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def contexts_by_thread_id(self) -> dict[str, dict[str, object]]:
        """Backward-compatible thread-keyed view of contexts."""
        output: dict[str, dict[str, object]] = {}
        for key, value in self.contexts_by_notification_key.items():
            _, _, thread_id = key.partition(":")
            output[thread_id] = value
        return output


@dataclass(slots=True)
class EnrichmentEngine:
    """Runs configured enrichment providers over notifications."""

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

        context = EnrichmentContext(max_requests_per_cycle=self.config.max_requests_per_cycle)
        contexts_by_notification_key: dict[str, dict[str, object]] = {
            f"{notification.account_id}:{notification.thread_id}": {} for notification in notifications
        }
        errors: list[str] = []
        for notification in notifications:
            key = f"{notification.account_id}:{notification.thread_id}"
            record_context = contexts_by_notification_key[key]
            notification_client = (
                clients_by_account.get(notification.account_id, client) if clients_by_account else client
            )
            for provider in self.providers:
                try:
                    payload = provider.enrich(notification=notification, client=notification_client, ctx=context)
                except Exception as error:  # pragma: no cover - defensive fail-open contract
                    errors.append(f"provider={provider.name} thread={notification.thread_id}: {error}")
                    continue
                if payload:
                    _set_nested_namespace(record_context, provider.name, payload)
        return EnrichmentRunResult(contexts_by_notification_key=contexts_by_notification_key, errors=errors)


def _set_nested_namespace(root: dict[str, object], namespace: str, payload: dict[str, object]) -> None:
    """Merge payload under a dot-delimited namespace."""
    segments = [segment for segment in namespace.split(".") if segment]
    if not segments:
        return
    node: dict[str, object] = root
    for segment in segments[:-1]:
        raw_child = node.get(segment)
        if not _is_str_object_map(raw_child):
            child = {}
            node[segment] = child
            node = child
            continue
        node = raw_child

    leaf = segments[-1]
    existing = node.get(leaf)
    if _is_str_object_map(existing):
        existing.update(payload)
        return
    node[leaf] = dict(payload)
