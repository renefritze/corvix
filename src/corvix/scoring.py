"""Custom scoring logic for ranking notifications."""

from __future__ import annotations

from datetime import UTC, datetime

from corvix.config import ScoringConfig
from corvix.domain import Notification


def score_notification(
    notification: Notification,
    config: ScoringConfig,
    now: datetime | None = None,
) -> float:
    """Compute a configurable score used for dashboard sorting."""
    current_time = now if now is not None else datetime.now(tz=UTC)
    score = 0.0
    if notification.unread:
        score += config.unread_bonus

    score += config.reason_weights.get(notification.reason, 0.0)
    score += config.repository_weights.get(notification.repository, 0.0)
    score += config.subject_type_weights.get(notification.subject_type, 0.0)

    title_lower = notification.subject_title.lower()
    for keyword, weight in config.title_keyword_weights.items():
        if keyword.lower() in title_lower:
            score += weight

    age_hours = max(0.0, (current_time - notification.updated_at).total_seconds() / 3600.0)
    score -= age_hours * config.age_decay_per_hour
    return score
