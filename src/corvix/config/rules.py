"""Rule domain model and YAML parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from corvix.config._utils import (
    _ensure_list,
    _ensure_map,
    _get_bool,
    _get_optional_bool,
    _get_optional_float,
    _get_optional_str,
    _get_str,
    _to_str_list,
)

_CONTEXT_OPERATORS = {"equals", "not_equals", "contains", "regex", "in", "exists"}


@dataclass(slots=True)
class ContextPredicate:
    """Predicate evaluated against enriched notification context."""

    path: str
    op: str
    value: object | None = None
    case_insensitive: bool = False


@dataclass(slots=True)
class MatchCriteria:
    """Filter fields for rules and dashboards."""

    repository_in: list[str] = field(default_factory=list)
    repository_glob: list[str] = field(default_factory=list)
    reason_in: list[str] = field(default_factory=list)
    subject_type_in: list[str] = field(default_factory=list)
    title_contains_any: list[str] = field(default_factory=list)
    title_regex: str | None = None
    unread: bool | None = None
    min_score: float | None = None
    max_age_hours: float | None = None
    context: list[ContextPredicate] = field(default_factory=list)


@dataclass(slots=True)
class RuleAction:
    """Action emitted when a rule matches."""

    action_type: str


@dataclass(slots=True)
class Rule:
    """Global or repository-scoped automation rule."""

    name: str
    match: MatchCriteria = field(default_factory=MatchCriteria)
    actions: list[RuleAction] = field(default_factory=list)
    exclude_from_dashboards: bool = False


@dataclass(slots=True)
class RuleSet:
    """Collection of global and per-repository rules."""

    global_rules: list[Rule] = field(default_factory=list)
    per_repository: dict[str, list[Rule]] = field(default_factory=dict)


def _parse_match(value: object, *, section: str = "match") -> MatchCriteria:
    match = _ensure_map(value, section)
    return MatchCriteria(
        repository_in=_to_str_list(match.get("repository_in")),
        repository_glob=_to_str_list(match.get("repository_glob")),
        reason_in=_to_str_list(match.get("reason_in")),
        subject_type_in=_to_str_list(match.get("subject_type_in")),
        title_contains_any=_to_str_list(match.get("title_contains_any")),
        title_regex=_get_optional_str(match, "title_regex", f"{section}.title_regex"),
        unread=_get_optional_bool(match, "unread", f"{section}.unread"),
        min_score=_get_optional_float(match, "min_score", f"{section}.min_score"),
        max_age_hours=_get_optional_float(match, "max_age_hours", f"{section}.max_age_hours"),
        context=_parse_context_predicates(match.get("context", []), section=f"{section}.context"),
    )


def _parse_context_predicates(value: object, *, section: str = "match.context") -> list[ContextPredicate]:
    predicates = _ensure_list(value, section)
    return [_parse_context_predicate(item, section=f"{section}[]") for item in predicates]


def _parse_context_predicate(value: object, *, section: str = "match.context[]") -> ContextPredicate:
    predicate = _ensure_map(value, f"{section} predicate")
    path_raw = predicate.get("path")
    if not isinstance(path_raw, str) or not path_raw.strip():
        msg = f"Config field '{section}.path' is required."
        raise ValueError(msg)
    op_raw = predicate.get("op")
    if not isinstance(op_raw, str):
        supported = ", ".join(sorted(_CONTEXT_OPERATORS))
        msg = f"Config field '{section}.op' must be one of: {supported}."
        raise ValueError(msg)
    op = op_raw.strip()
    if op not in _CONTEXT_OPERATORS:
        supported = ", ".join(sorted(_CONTEXT_OPERATORS))
        msg = f"Config field '{section}.op' must be one of: {supported}."
        raise ValueError(msg)
    predicate_value = predicate.get("value")
    if op == "regex":
        if not isinstance(predicate_value, str):
            msg = f"Config field '{section}.value' must be a string when op is 'regex'."
            raise ValueError(msg)
        try:
            re.compile(predicate_value)
        except re.error as error:
            msg = f"Config field '{section}.value' contains an invalid regex: {error}."
            raise ValueError(msg) from error
    return ContextPredicate(
        path=path_raw.strip(),
        op=op,
        value=predicate_value,
        case_insensitive=_get_bool(predicate, "case_insensitive", False, f"{section}.case_insensitive"),
    )


def _parse_rules(value: object) -> RuleSet:
    rules_map = _ensure_map(value, "rules")
    global_rules = [_parse_rule(item) for item in _ensure_list(rules_map.get("global", []), "rules.global")]
    per_repo_rules: dict[str, list[Rule]] = {}
    per_repo = _ensure_map(rules_map.get("per_repository", {}), "rules.per_repository")
    for repository, raw_rules in per_repo.items():
        per_repo_rules[repository] = [
            _parse_rule(item) for item in _ensure_list(raw_rules, f"rules.per_repository.{repository}")
        ]
    return RuleSet(global_rules=global_rules, per_repository=per_repo_rules)


def _parse_rule(value: object) -> Rule:
    rule_map = _ensure_map(value, "rule")
    name = _get_str(rule_map, "name", "unnamed-rule", "rule.name")
    actions_payload = _ensure_list(rule_map.get("actions", []), f"rule '{name}' actions")
    actions: list[RuleAction] = []
    for action in actions_payload:
        action_map = _ensure_map(action, "rule action")
        action_type = _get_str(action_map, "type", "", "rule action.type").strip()
        if not action_type:
            msg = "Config field 'rule action.type' is required."
            raise ValueError(msg)
        actions.append(RuleAction(action_type=action_type))
    return Rule(
        name=name,
        match=_parse_match(rule_map.get("match", {})),
        actions=actions,
        exclude_from_dashboards=_get_bool(
            rule_map,
            "exclude_from_dashboards",
            False,
            "rule.exclude_from_dashboards",
        ),
    )
