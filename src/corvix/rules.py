"""Rule matching for filtering and action triggering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from corvix.config import MatchCriteria, RuleAction, RuleSet
from corvix.domain import Notification


@dataclass(slots=True)
class RuleEvaluation:
    """Result of evaluating all rules against one notification."""

    matched_rules: list[str] = field(default_factory=list)
    actions: list[RuleAction] = field(default_factory=list)
    excluded: bool = False


def evaluate_rules(
    notification: Notification,
    score: float,
    rules: RuleSet,
    now: datetime | None = None,
) -> RuleEvaluation:
    """Evaluate global and per-repository rules."""
    current_time = now if now is not None else datetime.now(tz=UTC)
    candidate_rules = [*rules.global_rules, *rules.per_repository.get(notification.repository, [])]
    matched_rules: list[str] = []
    actions: list[RuleAction] = []
    excluded = False
    for rule in candidate_rules:
        if not matches_criteria(rule.match, notification, score, current_time):
            continue
        matched_rules.append(rule.name)
        actions.extend(rule.actions)
        excluded = excluded or rule.exclude_from_dashboards
    return RuleEvaluation(matched_rules=matched_rules, actions=actions, excluded=excluded)


def matches_criteria(
    criteria: MatchCriteria,
    notification: Notification,
    score: float,
    now: datetime,
) -> bool:
    """Check whether a notification satisfies configured criteria."""
    title = notification.subject_title
    title_matches_tokens = not criteria.title_contains_any or any(
        token.lower() in title.lower() for token in criteria.title_contains_any
    )
    regex_matches = criteria.title_regex is None or re.search(criteria.title_regex, title) is not None
    unread_matches = criteria.unread is None or notification.unread == criteria.unread
    score_matches = criteria.min_score is None or score >= criteria.min_score
    age_matches = True
    if criteria.max_age_hours is not None:
        age_hours = max(0.0, (now - notification.updated_at).total_seconds() / 3600.0)
        age_matches = age_hours <= criteria.max_age_hours

    return (
        (not criteria.repository_in or notification.repository in criteria.repository_in)
        and (not criteria.reason_in or notification.reason in criteria.reason_in)
        and (not criteria.subject_type_in or notification.subject_type in criteria.subject_type_in)
        and title_matches_tokens
        and regex_matches
        and unread_matches
        and score_matches
        and age_matches
    )
