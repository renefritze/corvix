"""Idempotency / deduplication helpers for notification delivery."""

from __future__ import annotations

from corvix.notifications.models import NotificationEvent


def dedupe_events(
    events: list[NotificationEvent],
    seen: set[str],
) -> tuple[list[NotificationEvent], set[str]]:
    """Filter *events* to those not already in *seen*.

    Returns a tuple of (fresh_events, updated_seen_set).  The returned
    set is a new object; the caller should replace their reference so the
    state advances correctly across poll cycles.

    Parameters
    ----------
    events:
        Candidate events from the current poll cycle.
    seen:
        Set of ``event_id`` values already delivered in previous cycles.
    """
    fresh: list[NotificationEvent] = []
    new_seen = set(seen)
    for event in events:
        if event.event_id not in new_seen:
            fresh.append(event)
            new_seen.add(event.event_id)
    return fresh, new_seen


def make_seen_set(events: list[NotificationEvent]) -> set[str]:
    """Build an initial ``seen`` set from a list of already-delivered events."""
    return {e.event_id for e in events}
