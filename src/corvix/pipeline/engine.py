"""Unified pipeline engine for field completion and context enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeIs

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.provider import ContextProvider, FieldProvider, PipelineContext


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _set_nested_namespace(root: dict[str, object], namespace: str, payload: dict[str, object]) -> None:
    """Merge *payload* under a dot-delimited *namespace* in *root*."""
    segments = [segment for segment in namespace.split(".") if segment]
    if not segments:
        return
    node: dict[str, object] = root
    for segment in segments[:-1]:
        raw_child = node.get(segment)
        if not _is_str_object_map(raw_child):
            child: dict[str, object] = {}
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


@dataclass(slots=True)
class PipelineRunResult:
    """Result of one :class:`PipelineEngine` run.

    Combines the outputs of field-completion providers (updated notifications)
    and context providers (per-notification context maps) into a single
    result object.
    """

    notifications: list[Notification] = field(default_factory=list)
    contexts_by_notification_key: dict[str, dict[str, object]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def contexts_by_thread_id(self) -> dict[str, dict[str, object]]:
        """Backward-compatible thread-keyed view of :attr:`contexts_by_notification_key`."""
        output: dict[str, dict[str, object]] = {}
        for key, value in self.contexts_by_notification_key.items():
            _, _, thread_id = key.rpartition(":")
            output[thread_id] = value
        return output


@dataclass(slots=True)
class PipelineEngine:
    """Runs field-completion and context-enrichment providers in a single unified pass.

    Providers are dispatched by structural type:

    * :class:`~corvix.pipeline.provider.FieldProvider` — the ``hydrate()`` method
      is called; its return value replaces the current notification so that
      subsequent providers see the updated state.
    * :class:`~corvix.pipeline.provider.ContextProvider` — the ``enrich()``
      method is called; non-empty payloads are merged under the provider's
      dot-delimited ``name`` namespace in the notification's context map.

    A single :class:`~corvix.pipeline.provider.PipelineContext` is shared across
    all providers and all notifications in one :meth:`run` call, so URL responses
    cached by an early provider are available to later providers without an
    additional HTTP round-trip.
    """

    providers: list[FieldProvider | ContextProvider]
    max_requests_per_cycle: int = 25

    def run(
        self,
        notifications: list[Notification],
        client: JsonFetchClient,
        clients_by_account: dict[str, JsonFetchClient] | None = None,
    ) -> PipelineRunResult:
        """Run all providers over every notification in one cycle.

        Field-completion and context-enrichment providers are interleaved in
        declaration order: each provider sees the notification state produced by
        the preceding providers in the same pass.
        """
        contexts_by_notification_key: dict[str, dict[str, object]] = {
            f"{n.account_id}:{n.thread_id}": {} for n in notifications
        }

        if not self.providers:
            return PipelineRunResult(
                notifications=list(notifications),
                contexts_by_notification_key=contexts_by_notification_key,
                errors=[],
            )

        context = PipelineContext(max_requests_per_cycle=self.max_requests_per_cycle)
        errors: list[str] = []
        hydrated: list[Notification] = list(notifications)

        for i, notification in enumerate(notifications):
            key = f"{notification.account_id}:{notification.thread_id}"
            notification_client = (
                clients_by_account.get(notification.account_id, client)
                if clients_by_account
                else client
            )
            current = notification
            for provider in self.providers:
                try:
                    if hasattr(provider, "hydrate"):
                        current = provider.hydrate(  # type: ignore[union-attr]
                            notification=current,
                            client=notification_client,
                            ctx=context,
                        )
                    elif hasattr(provider, "enrich"):
                        payload = provider.enrich(  # type: ignore[union-attr]
                            notification=current,
                            client=notification_client,
                            ctx=context,
                        )
                        if payload:
                            _set_nested_namespace(contexts_by_notification_key[key], provider.name, payload)
                except Exception as error:
                    provider_name = getattr(provider, "name", repr(provider))
                    errors.append(f"provider={provider_name} thread={current.thread_id}: {error}")
            hydrated[i] = current

        return PipelineRunResult(
            notifications=hydrated,
            contexts_by_notification_key=contexts_by_notification_key,
            errors=errors,
        )
