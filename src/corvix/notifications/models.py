"""Domain event models for notification delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class NotificationEvent:
    """Canonical event produced when a new unread notification is detected.

    This is the payload passed to every delivery target. It is deliberately
    decoupled from the internal ``NotificationRecord`` so targets only depend
    on this stable interface.
    """

    event_id: str
    """Stable identifier: ``{account_id}:{thread_id}``."""

    thread_id: str
    repository: str
    reason: str
    subject_title: str
    subject_type: str
    web_url: str | None
    updated_at: datetime
    score: float
    unread: bool
    account_id: str = "primary"


@dataclass(slots=True)
class DeliveryResult:
    """Result of a single target's delivery attempt."""

    target: str
    events_attempted: int
    events_delivered: int
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass(slots=True)
class DispatchResult:
    """Aggregated result of a fan-out dispatch to all enabled targets."""

    events: list[NotificationEvent]
    results: list[DeliveryResult] = field(default_factory=list)

    @property
    def total_delivered(self) -> int:
        return sum(r.events_delivered for r in self.results)

    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.results)
