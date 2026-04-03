"""Rule matching for filtering and action triggering."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from typing import TypeIs

from corvix.config import MatchCriteria, RuleAction, RuleSet
from corvix.domain import Notification


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


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
    context: Mapping[str, object] | None = None,
) -> RuleEvaluation:
    """Evaluate global and per-repository rules."""
    current_time = now if now is not None else datetime.now(tz=UTC)
    candidate_rules = [*rules.global_rules, *rules.per_repository.get(notification.repository, [])]
    matched_rules: list[str] = []
    actions: list[RuleAction] = []
    excluded = False
    active_context = context if context is not None else {}
    for rule in candidate_rules:
        if not matches_criteria(rule.match, notification, score, current_time, context=active_context):
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
    context: Mapping[str, object] | None = None,
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

    repository_glob_matches = not criteria.repository_glob or any(
        fnmatchcase(notification.repository, pattern) for pattern in criteria.repository_glob
    )
    context_predicates_match = _matches_context_predicates(criteria=criteria, context=context or {})

    return (
        (not criteria.repository_in or notification.repository in criteria.repository_in)
        and repository_glob_matches
        and (not criteria.reason_in or notification.reason in criteria.reason_in)
        and (not criteria.subject_type_in or notification.subject_type in criteria.subject_type_in)
        and title_matches_tokens
        and regex_matches
        and unread_matches
        and score_matches
        and age_matches
        and context_predicates_match
    )


def _matches_context_predicates(criteria: MatchCriteria, context: Mapping[str, object]) -> bool:
    if not criteria.context:
        return True
    for predicate in criteria.context:
        path_exists, path_value = _resolve_context_path(context=context, path=predicate.path)
        if not _evaluate_context_predicate(
            op=predicate.op,
            path_exists=path_exists,
            path_value=path_value,
            expected=predicate.value,
            case_insensitive=predicate.case_insensitive,
        ):
            return False
    return True


def _resolve_context_path(context: Mapping[str, object], path: str) -> tuple[bool, object | None]:
    node: object = context
    for segment in path.split("."):
        if not _is_str_object_map(node):
            return False, None
        if segment not in node:
            return False, None
        node = node[segment]
    return True, node


def _evaluate_context_predicate(
    *,
    op: str,
    path_exists: bool,
    path_value: object | None,
    expected: object | None,
    case_insensitive: bool,
) -> bool:
    if op == "exists":
        expected_exists = bool(expected) if expected is not None else True
        return path_exists == expected_exists
    if not path_exists:
        return False
    if op == "regex":
        if not isinstance(path_value, str) or not isinstance(expected, str):
            return False
        flags = re.IGNORECASE if case_insensitive else 0
        try:
            return re.search(expected, path_value, flags=flags) is not None
        except re.error:
            return False
    evaluators = {
        "equals": _equals(path_value, expected, case_insensitive),
        "not_equals": not _equals(path_value, expected, case_insensitive),
        "contains": _contains(path_value, expected, case_insensitive),
        "in": _in_values(path_value, expected, case_insensitive),
    }
    return evaluators.get(op, False)


def _equals(left: object | None, right: object | None, case_insensitive: bool) -> bool:
    if case_insensitive and isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    return left == right


def _contains(path_value: object | None, expected: object | None, case_insensitive: bool) -> bool:
    if isinstance(path_value, str) and isinstance(expected, str):
        left = path_value.casefold() if case_insensitive else path_value
        right = expected.casefold() if case_insensitive else expected
        return right in left
    if isinstance(path_value, (list, tuple, set, frozenset)):
        return any(_equals(item, expected, case_insensitive) for item in path_value)
    return False


def _in_values(path_value: object | None, expected: object | None, case_insensitive: bool) -> bool:
    if not isinstance(expected, (list, tuple, set, frozenset)):
        return False
    return any(_equals(path_value, candidate, case_insensitive) for candidate in expected)
