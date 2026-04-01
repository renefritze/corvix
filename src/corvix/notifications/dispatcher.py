"""Fan-out dispatcher: delivers notification events to all enabled targets."""

from __future__ import annotations

import logging

from corvix.notifications.models import DeliveryResult, DispatchResult, NotificationEvent
from corvix.notifications.targets.base import NotificationTarget

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Fan-out delivery to a list of :class:`NotificationTarget` instances.

    Each target is called independently; a failure in one target never
    prevents others from receiving events.  Results are aggregated into a
    :class:`DispatchResult` for the caller (typically ``run_poll_cycle``).

    Usage::

        dispatcher = NotificationDispatcher(targets=[my_target])
        result = dispatcher.dispatch(events)
    """

    def __init__(self, targets: list[NotificationTarget]) -> None:
        self._targets = targets

    def dispatch(self, events: list[NotificationEvent]) -> DispatchResult:
        """Deliver *events* to all registered targets.

        If *events* is empty the dispatcher is a no-op and returns an empty
        :class:`DispatchResult`.
        """
        result = DispatchResult(events=events)

        if not events:
            return result

        for target in self._targets:
            try:
                delivery = target.deliver(events)
            except Exception as exc:
                logger.exception("Target '%s' raised an unexpected error", target.name)
                delivery = DeliveryResult(
                    target=target.name,
                    events_attempted=len(events),
                    events_delivered=0,
                    errors=[str(exc)],
                )
            else:
                if delivery.errors:
                    for err in delivery.errors:
                        logger.warning("Target '%s' delivery error: %s", target.name, err)
                else:
                    logger.debug(
                        "Target '%s' delivered %d/%d events",
                        target.name,
                        delivery.events_delivered,
                        delivery.events_attempted,
                    )

            result.results.append(delivery)

        return result
