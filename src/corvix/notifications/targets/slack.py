"""Slack incoming-webhook notification target.

This is the built-in reference :class:`~corvix.notifications.targets.base.NotificationTarget`
implementation.  It posts one Slack message per newly-arrived unread GitHub
notification to a configured incoming-webhook URL.  See
``docs/new_notification_target.md`` for how to add your own channel.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from corvix.notifications.models import DeliveryResult, NotificationEvent

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(slots=True)
class SlackTarget:
    """Posts a Slack message for each new GitHub notification.

    Parameters
    ----------
    webhook_url:
        Slack incoming-webhook URL. Resolved from an env var by the CLI so the
        secret never lives in ``corvix.yaml``.
    enabled:
        When ``False`` the target is a no-op (delivers nothing). The CLI already
        skips disabled targets, but this keeps the target safe to construct
        directly.
    timeout_seconds:
        Per-request HTTP timeout.
    """

    webhook_url: str
    enabled: bool = True
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS

    @property
    def name(self) -> str:
        return "slack"

    def deliver(self, events: list[NotificationEvent]) -> DeliveryResult:
        """Post one message per event; never raise (errors go in the result)."""
        if not self.enabled:
            return DeliveryResult(target=self.name, events_attempted=len(events), events_delivered=0)

        errors: list[str] = []
        delivered = 0
        for event in events:
            try:
                self._post(_format_message(event))
            except (urllib.error.URLError, OSError, ValueError) as exc:
                logger.warning("Slack delivery failed for thread %s: %s", event.thread_id, exc)
                errors.append(f"{event.thread_id}: {exc}")
            else:
                delivered += 1

        return DeliveryResult(
            target=self.name,
            events_attempted=len(events),
            events_delivered=delivered,
            errors=errors,
        )

    def _post(self, text: str) -> None:
        payload = json.dumps({"text": text}).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds):
            pass


def _format_message(event: NotificationEvent) -> str:
    """Render a Slack message body for a single notification event."""
    header = f"*{event.subject_title}*"
    meta = f"`{event.repository}` · {event.reason} · {event.subject_type}"
    if event.account_id and event.account_id != "primary":
        meta += f" · {event.account_id}"
    link = f"\n<{event.web_url}|Open on GitHub>" if event.web_url else ""
    return f"{header}\n{meta}{link}"
