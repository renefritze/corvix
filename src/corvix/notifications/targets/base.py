"""NotificationTarget protocol — the extension point for all delivery channels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from corvix.notifications.models import DeliveryResult, NotificationEvent


@runtime_checkable
class NotificationTarget(Protocol):
    """Delivery channel for notification events.

    Implement this protocol to add a new notification channel (browser push,
    Slack, webhook, email, …).  ``deliver`` is only called when there is at
    least one event to process.

    Errors raised inside ``deliver`` are caught by the dispatcher and surfaced
    in ``DeliveryResult.errors``; they never propagate to the poll loop.
    """

    @property
    def name(self) -> str:
        """Human-readable identifier used in logs and metrics."""
        ...

    def deliver(
        self,
        events: list[NotificationEvent],
    ) -> DeliveryResult:
        """Deliver *events* to this channel.

        Must return a ``DeliveryResult`` even on partial failure.
        Implementations are responsible for their own rate-limiting,
        retries, and idempotency.
        """
        ...
