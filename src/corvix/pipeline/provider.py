"""Unified provider interfaces and shared context for the pipeline."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient, RequestContext
from corvix.types import JsonValue


class PipelineContext(RequestContext):
    """Per-cycle request budget and URL cache shared across all pipeline providers.

    A single :class:`PipelineContext` is created per :meth:`PipelineEngine.run`
    call and passed to every provider, so that URL responses cached by a
    field-completion provider are visible to subsequent context providers in the
    same cycle.
    """

    def get_json(self, client: JsonFetchClient, url: str, timeout_seconds: float) -> JsonValue:
        """Fetch and cache a JSON payload; raises if the request budget is exhausted."""
        key = (client.account_id, url)
        if key not in self.url_cache and self.request_count >= self.max_requests_per_cycle:
            msg = "Pipeline request budget exhausted."
            raise RuntimeError(msg)
        return super().get_json(client=client, url=url, timeout_seconds=timeout_seconds)


@runtime_checkable
class FieldProvider(Protocol):
    """Provider that completes missing canonical fields on a :class:`~corvix.domain.Notification`.

    Field providers mutate the notification in-place by returning a (possibly
    replaced) :class:`~corvix.domain.Notification` with missing required fields
    filled in (e.g. ``subject_url``, ``web_url``).
    """

    name: str

    def hydrate(
        self,
        _notification: Notification,
        _client: JsonFetchClient,
        _ctx: PipelineContext,
        /,
    ) -> Notification:
        """Return a notification with any missing required fields filled in."""
        ...


@runtime_checkable
class ContextProvider(Protocol):
    """Provider that attaches optional contextual data to a :class:`~corvix.domain.Notification`.

    Context providers return a mapping that is merged under the provider's
    ``name`` namespace in :attr:`~corvix.domain.NotificationRecord.context`.
    """

    name: str

    def enrich(
        self,
        _notification: Notification,
        _client: JsonFetchClient,
        _ctx: PipelineContext,
        /,
    ) -> dict[str, object]:
        """Return a mapping of context data to attach under this provider's namespace."""
        ...
