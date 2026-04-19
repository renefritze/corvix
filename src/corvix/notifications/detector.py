"""Detect newly-arrived unread notifications by comparing snapshots."""

from __future__ import annotations

from corvix.domain import NotificationRecord, notification_key
from corvix.notifications.models import NotificationEvent


def detect_new_unread_events(
    previous: list[NotificationRecord],
    current: list[NotificationRecord],
    min_score: float = 0.0,
    include_read: bool = False,
) -> list[NotificationEvent]:
    """Return events for notifications that are new *or* newly-unread.

    A record qualifies when all of the following are true:

    * ``unread`` is ``True`` in the current snapshot, unless *include_read*
      is ``True`` in which case read records also qualify.
    * It is not excluded from dashboards and not dismissed.
    * Its ``score`` meets ``min_score``.
    * Either it did not exist in the previous snapshot *or* it existed but
      was ``unread=False`` (read → unread transition, rare but possible).

    Parameters
    ----------
    previous:
        Records from the snapshot loaded *before* the current poll cycle.
    current:
        Records produced by the current poll cycle (post-score/rules).
    min_score:
        Minimum score for a record to generate an event (default 0 — all
        unread records qualify).
    include_read:
        When ``True``, read records also generate events (default ``False``).
    """
    prev_by_id: dict[str, NotificationRecord] = {notification_key(r.notification): r for r in previous}

    events: list[NotificationEvent] = []
    for record in current:
        notification = record.notification

        if not include_read and not notification.unread:
            continue
        if record.excluded or record.dismissed:
            continue
        if record.score < min_score:
            continue

        key = notification_key(notification)
        prev = prev_by_id.get(key)
        is_new = prev is None
        became_unread = prev is not None and not prev.notification.unread

        if not (is_new or became_unread):
            continue

        events.append(
            NotificationEvent(
                event_id=key,
                account_id=notification.account_id,
                thread_id=notification.thread_id,
                repository=notification.repository,
                reason=notification.reason,
                subject_title=notification.subject_title,
                subject_type=notification.subject_type,
                web_url=notification.web_url,
                updated_at=notification.updated_at,
                score=record.score,
                unread=notification.unread,
            )
        )

    return events
