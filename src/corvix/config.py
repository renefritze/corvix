"""YAML configuration for Corvix dashboards and polling."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_POLLING_PER_PAGE_MIN = 1
_POLLING_PER_PAGE_MAX = 50
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


@dataclass(slots=True)
class DashboardSpec:
    """Dashboard configuration for sorting, grouping, and filtering."""

    name: str
    group_by: str = "none"
    sort_by: str = "score"
    descending: bool = True
    include_read: bool = False
    max_items: int = 100
    match: MatchCriteria = field(default_factory=MatchCriteria)


@dataclass(slots=True)
class ScoringConfig:
    """Configurable scoring model for notifications."""

    unread_bonus: float = 15.0
    age_decay_per_hour: float = 0.25
    reason_weights: dict[str, float] = field(default_factory=dict)
    repository_weights: dict[str, float] = field(default_factory=dict)
    subject_type_weights: dict[str, float] = field(default_factory=dict)
    title_keyword_weights: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class PollingConfig:
    """Polling behavior for ingestion."""

    interval_seconds: int = 60
    per_page: int = 50
    max_pages: int = 5
    all: bool = False
    participating: bool = False


@dataclass(slots=True)
class GitHubConfig:
    """GitHub API configuration."""

    token_env: str = "GITHUB_TOKEN"
    api_base_url: str = "https://api.github.com"


@dataclass(slots=True)
class GitHubLatestCommentEnrichmentConfig:
    """Config for enriching comment notifications with latest-comment metadata."""

    enabled: bool = False
    timeout_seconds: float = 10.0


@dataclass(slots=True)
class GitHubPRStateEnrichmentConfig:
    """Config for enriching pull-request notifications with PR state."""

    enabled: bool = False
    timeout_seconds: float = 10.0


@dataclass(slots=True)
class EnrichmentConfig:
    """Top-level enrichment configuration."""

    enabled: bool = False
    max_requests_per_cycle: int = 25
    github_latest_comment: GitHubLatestCommentEnrichmentConfig = field(
        default_factory=GitHubLatestCommentEnrichmentConfig
    )
    github_pr_state: GitHubPRStateEnrichmentConfig = field(default_factory=GitHubPRStateEnrichmentConfig)


@dataclass(slots=True)
class StateConfig:
    """State/cache location for persisted notifications."""

    cache_file: Path = Path("~/.cache/corvix/notifications.json")


@dataclass(slots=True)
class BrowserTabTargetConfig:
    """Config for in-tab browser notification delivery."""

    enabled: bool = True
    max_per_cycle: int = 5
    cooldown_seconds: int = 10


@dataclass(slots=True)
class WebPushTargetConfig:
    """Config for background Web Push notification delivery (phase 2)."""

    enabled: bool = False
    vapid_public_key_env: str = "CORVIX_VAPID_PUBLIC_KEY"
    vapid_private_key_env: str = "CORVIX_VAPID_PRIVATE_KEY"
    subject: str = ""


@dataclass(slots=True)
class NotificationsDetectConfig:
    """Controls which records qualify for notification events."""

    include_read: bool = False
    min_score: float = 0.0


@dataclass(slots=True)
class NotificationsConfig:
    """Top-level notifications configuration."""

    enabled: bool = True
    detect: NotificationsDetectConfig = field(default_factory=NotificationsDetectConfig)
    browser_tab: BrowserTabTargetConfig = field(default_factory=BrowserTabTargetConfig)
    web_push: WebPushTargetConfig = field(default_factory=WebPushTargetConfig)


@dataclass(slots=True)
class AuthConfig:
    """Authentication mode configuration."""

    mode: str = "single_user"  # single_user | multi_user
    session_secret: str = ""


@dataclass(slots=True)
class DatabaseConfig:
    """PostgreSQL connection configuration."""

    url_env: str = "DATABASE_URL"


@dataclass(slots=True)
class AppConfig:
    """Top-level application config."""

    github: GitHubConfig = field(default_factory=GitHubConfig)
    enrichment: EnrichmentConfig = field(default_factory=EnrichmentConfig)
    polling: PollingConfig = field(default_factory=PollingConfig)
    state: StateConfig = field(default_factory=StateConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    rules: RuleSet = field(default_factory=RuleSet)
    dashboards: list[DashboardSpec] = field(default_factory=list)
    auth: AuthConfig = field(default_factory=AuthConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)

    def resolve_cache_file(self) -> Path:
        """Resolve the configured cache path."""
        return self.state.cache_file.expanduser().resolve()


DEFAULT_CONFIG = """\
github:
  token_env: GITHUB_TOKEN
  api_base_url: https://api.github.com

enrichment:
  enabled: false
  max_requests_per_cycle: 25
  github_latest_comment:
    enabled: false
    timeout_seconds: 10
  github_pr_state:
    enabled: false
    timeout_seconds: 10

polling:
  interval_seconds: 60
  per_page: 50
  max_pages: 5
  all: false
  participating: false

state:
  cache_file: ~/.cache/corvix/notifications.json

scoring:
  unread_bonus: 15
  age_decay_per_hour: 0.25
  reason_weights:
    mention: 50
    review_requested: 40
    assign: 30
    author: 10
  repository_weights:
    your-org/critical-repo: 25
  subject_type_weights:
    PullRequest: 10
  title_keyword_weights:
    security: 20
    urgent: 15

rules:
  global:
    - name: mute-bot-noise
      match:
        title_regex: ".*\\[bot\\].*"
      actions:
        - type: mark_read
      exclude_from_dashboards: true
  per_repository:
    your-org/infra:
      - name: mute-chore-prs
        match:
          title_contains_any: ["chore", "deps"]
        actions:
          - type: mark_read
        exclude_from_dashboards: true

dashboards:
  - name: overview
    group_by: reason
    sort_by: updated_at
    descending: true
    include_read: true
    max_items: 200
  - name: triage
    group_by: repository
    sort_by: score
    descending: true
    include_read: false
    max_items: 100
    match:
      reason_in: ["mention", "review_requested", "assign"]
"""


def _ensure_map(value: object, section: str) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = f"Config section '{section}' must be a map/object."
        raise ValueError(msg)
    output: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            msg = f"Config section '{section}' must use string keys."
            raise ValueError(msg)
        output[key] = item
    return output


def _ensure_list(value: object, section: str) -> list[object]:
    if isinstance(value, list):
        return [item for item in value]
    msg = f"Config section '{section}' must be a list."
    raise ValueError(msg)


def _as_bool(value: object, field: str) -> bool:
    if isinstance(value, bool):
        return value
    msg = f"Config field '{field}' must be a boolean."
    raise ValueError(msg)


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"Config field '{field}' must be an integer."
        raise ValueError(msg)
    return value


def _as_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"Config field '{field}' must be a number."
        raise ValueError(msg)
    return float(value)


def _as_str(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    msg = f"Config field '{field}' must be a string."
    raise ValueError(msg)


def _get_str(config: dict[str, object], key: str, default: str, field: str) -> str:
    if key not in config:
        return default
    return _as_str(config[key], field)


def _get_optional_str(config: dict[str, object], key: str, field: str) -> str | None:
    if key not in config or config[key] is None:
        return None
    return _as_str(config[key], field)


def _get_bool(config: dict[str, object], key: str, default: bool, field: str) -> bool:
    if key not in config:
        return default
    return _as_bool(config[key], field)


def _get_optional_bool(config: dict[str, object], key: str, field: str) -> bool | None:
    if key not in config or config[key] is None:
        return None
    return _as_bool(config[key], field)


def _get_int(config: dict[str, object], key: str, default: int, field: str) -> int:
    if key not in config:
        return default
    return _as_int(config[key], field)


def _get_float(config: dict[str, object], key: str, default: float, field: str) -> float:
    if key not in config:
        return default
    return _as_float(config[key], field)


def _get_optional_float(config: dict[str, object], key: str, field: str) -> float | None:
    if key not in config or config[key] is None:
        return None
    return _as_float(config[key], field)


def _to_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = "Expected a list."
        raise ValueError(msg)
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            msg = "Expected a list of strings."
            raise ValueError(msg)
        output.append(item)
    return output


def _parse_match(value: object) -> MatchCriteria:
    match = _ensure_map(value, "match")
    return MatchCriteria(
        repository_in=_to_str_list(match.get("repository_in")),
        repository_glob=_to_str_list(match.get("repository_glob")),
        reason_in=_to_str_list(match.get("reason_in")),
        subject_type_in=_to_str_list(match.get("subject_type_in")),
        title_contains_any=_to_str_list(match.get("title_contains_any")),
        title_regex=_get_optional_str(match, "title_regex", "match.title_regex"),
        unread=_get_optional_bool(match, "unread", "match.unread"),
        min_score=_get_optional_float(match, "min_score", "match.min_score"),
        max_age_hours=_get_optional_float(match, "max_age_hours", "match.max_age_hours"),
        context=_parse_context_predicates(match.get("context", [])),
    )


def _parse_context_predicates(value: object) -> list[ContextPredicate]:
    predicates = _ensure_list(value, "match.context")
    return [_parse_context_predicate(item) for item in predicates]


def _parse_context_predicate(value: object) -> ContextPredicate:
    predicate = _ensure_map(value, "match.context predicate")
    path_raw = predicate.get("path")
    if not isinstance(path_raw, str) or not path_raw.strip():
        msg = "Config field 'match.context[].path' is required."
        raise ValueError(msg)
    op_raw = predicate.get("op")
    if not isinstance(op_raw, str):
        supported = ", ".join(sorted(_CONTEXT_OPERATORS))
        msg = f"Config field 'match.context[].op' must be one of: {supported}."
        raise ValueError(msg)
    op = op_raw.strip()
    if op not in _CONTEXT_OPERATORS:
        supported = ", ".join(sorted(_CONTEXT_OPERATORS))
        msg = f"Config field 'match.context[].op' must be one of: {supported}."
        raise ValueError(msg)
    predicate_value = predicate.get("value")
    if op == "regex":
        if not isinstance(predicate_value, str):
            msg = "Config field 'match.context[].value' must be a string when op is 'regex'."
            raise ValueError(msg)
        try:
            re.compile(predicate_value)
        except re.error as error:
            msg = f"Config field 'match.context[].value' contains an invalid regex: {error}."
            raise ValueError(msg) from error
    return ContextPredicate(
        path=path_raw.strip(),
        op=op,
        value=predicate_value,
        case_insensitive=_get_bool(predicate, "case_insensitive", False, "match.context[].case_insensitive"),
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


def _parse_dashboards(value: object) -> list[DashboardSpec]:
    dashboards = _ensure_list(value, "dashboards")
    parsed: list[DashboardSpec] = []
    for raw_dashboard in dashboards:
        dashboard = _ensure_map(raw_dashboard, "dashboard entry")
        parsed.append(
            DashboardSpec(
                name=_get_str(dashboard, "name", "default", "dashboards[].name"),
                group_by=_get_str(dashboard, "group_by", "none", "dashboards[].group_by"),
                sort_by=_get_str(dashboard, "sort_by", "score", "dashboards[].sort_by"),
                descending=_get_bool(dashboard, "descending", True, "dashboards[].descending"),
                include_read=_get_bool(dashboard, "include_read", False, "dashboards[].include_read"),
                max_items=_get_int(dashboard, "max_items", 100, "dashboards[].max_items"),
                match=_parse_match(dashboard.get("match", {})),
            ),
        )
    return parsed


def _parse_scoring(value: object) -> ScoringConfig:
    scoring = _ensure_map(value, "scoring")
    return ScoringConfig(
        unread_bonus=_get_float(scoring, "unread_bonus", 15.0, "scoring.unread_bonus"),
        age_decay_per_hour=_get_float(scoring, "age_decay_per_hour", 0.25, "scoring.age_decay_per_hour"),
        reason_weights=_to_float_map(scoring.get("reason_weights", {}), "scoring.reason_weights"),
        repository_weights=_to_float_map(scoring.get("repository_weights", {}), "scoring.repository_weights"),
        subject_type_weights=_to_float_map(scoring.get("subject_type_weights", {}), "scoring.subject_type_weights"),
        title_keyword_weights=_to_float_map(scoring.get("title_keyword_weights", {}), "scoring.title_keyword_weights"),
    )


def _to_float_map(value: object, section: str) -> dict[str, float]:
    data = _ensure_map(value, section)
    return {key: _as_float(raw_value, f"{section}.{key}") for key, raw_value in data.items()}


def _parse_github(value: object) -> GitHubConfig:
    github = _ensure_map(value, "github")
    return GitHubConfig(
        token_env=_get_str(github, "token_env", "GITHUB_TOKEN", "github.token_env"),
        api_base_url=_get_str(github, "api_base_url", "https://api.github.com", "github.api_base_url"),
    )


def _parse_polling(value: object) -> PollingConfig:
    polling = _ensure_map(value, "polling")
    per_page = _get_int(polling, "per_page", _POLLING_PER_PAGE_MAX, "polling.per_page")
    if not _POLLING_PER_PAGE_MIN <= per_page <= _POLLING_PER_PAGE_MAX:
        msg = f"Config value 'polling.per_page' must be between {_POLLING_PER_PAGE_MIN} and {_POLLING_PER_PAGE_MAX}."
        raise ValueError(msg)
    return PollingConfig(
        interval_seconds=_get_int(polling, "interval_seconds", 60, "polling.interval_seconds"),
        per_page=per_page,
        max_pages=_get_int(polling, "max_pages", 5, "polling.max_pages"),
        all=_get_bool(polling, "all", False, "polling.all"),
        participating=_get_bool(polling, "participating", False, "polling.participating"),
    )


def _parse_enrichment(value: object) -> EnrichmentConfig:
    enrichment = _ensure_map(value, "enrichment")
    latest_comment_raw = _ensure_map(
        enrichment.get("github_latest_comment", {}),
        "enrichment.github_latest_comment",
    )
    pr_state_raw = _ensure_map(
        enrichment.get("github_pr_state", {}),
        "enrichment.github_pr_state",
    )
    return EnrichmentConfig(
        enabled=_get_bool(enrichment, "enabled", False, "enrichment.enabled"),
        max_requests_per_cycle=_get_int(
            enrichment,
            "max_requests_per_cycle",
            25,
            "enrichment.max_requests_per_cycle",
        ),
        github_latest_comment=GitHubLatestCommentEnrichmentConfig(
            enabled=_get_bool(latest_comment_raw, "enabled", False, "enrichment.github_latest_comment.enabled"),
            timeout_seconds=_get_float(
                latest_comment_raw,
                "timeout_seconds",
                10.0,
                "enrichment.github_latest_comment.timeout_seconds",
            ),
        ),
        github_pr_state=GitHubPRStateEnrichmentConfig(
            enabled=_get_bool(pr_state_raw, "enabled", False, "enrichment.github_pr_state.enabled"),
            timeout_seconds=_get_float(
                pr_state_raw,
                "timeout_seconds",
                10.0,
                "enrichment.github_pr_state.timeout_seconds",
            ),
        ),
    )


def _parse_state(value: object) -> StateConfig:
    state = _ensure_map(value, "state")
    return StateConfig(
        cache_file=Path(_get_str(state, "cache_file", "~/.cache/corvix/notifications.json", "state.cache_file"))
    )


def _parse_auth(value: object) -> AuthConfig:
    auth = _ensure_map(value, "auth")
    return AuthConfig(
        mode=_get_str(auth, "mode", "single_user", "auth.mode"),
        session_secret=_get_str(auth, "session_secret", "", "auth.session_secret"),
    )


def _parse_database(value: object) -> DatabaseConfig:
    database = _ensure_map(value, "database")
    return DatabaseConfig(url_env=_get_str(database, "url_env", "DATABASE_URL", "database.url_env"))


def _parse_notifications(value: object) -> NotificationsConfig:
    notif = _ensure_map(value, "notifications")
    detect_raw = _ensure_map(notif.get("detect", {}), "notifications.detect")
    browser_raw = _ensure_map(notif.get("browser_tab", {}), "notifications.browser_tab")
    web_push_raw = _ensure_map(notif.get("web_push", {}), "notifications.web_push")
    return NotificationsConfig(
        enabled=_get_bool(notif, "enabled", True, "notifications.enabled"),
        detect=NotificationsDetectConfig(
            include_read=_get_bool(detect_raw, "include_read", False, "notifications.detect.include_read"),
            min_score=_get_float(detect_raw, "min_score", 0.0, "notifications.detect.min_score"),
        ),
        browser_tab=BrowserTabTargetConfig(
            enabled=_get_bool(browser_raw, "enabled", True, "notifications.browser_tab.enabled"),
            max_per_cycle=_get_int(browser_raw, "max_per_cycle", 5, "notifications.browser_tab.max_per_cycle"),
            cooldown_seconds=_get_int(
                browser_raw,
                "cooldown_seconds",
                10,
                "notifications.browser_tab.cooldown_seconds",
            ),
        ),
        web_push=WebPushTargetConfig(
            enabled=_get_bool(web_push_raw, "enabled", False, "notifications.web_push.enabled"),
            vapid_public_key_env=_get_str(
                web_push_raw,
                "vapid_public_key_env",
                "CORVIX_VAPID_PUBLIC_KEY",
                "notifications.web_push.vapid_public_key_env",
            ),
            vapid_private_key_env=_get_str(
                web_push_raw,
                "vapid_private_key_env",
                "CORVIX_VAPID_PRIVATE_KEY",
                "notifications.web_push.vapid_private_key_env",
            ),
            subject=_get_str(web_push_raw, "subject", "", "notifications.web_push.subject"),
        ),
    )


def load_config(path: Path) -> AppConfig:
    """Load and validate YAML config from disk."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = "Top-level YAML must be a map/object."
        raise ValueError(msg)

    github = _parse_github(data.get("github", {}))
    enrichment = _parse_enrichment(data.get("enrichment", {}))
    polling = _parse_polling(data.get("polling", {}))
    state = _parse_state(data.get("state", {}))
    scoring = _parse_scoring(data.get("scoring", {}))
    rules = _parse_rules(data.get("rules", {}))
    dashboards = _parse_dashboards(data.get("dashboards", []))
    auth = _parse_auth(data.get("auth", {}))
    database = _parse_database(data.get("database", {}))
    notifications = _parse_notifications(data.get("notifications", {}))
    return AppConfig(
        github=github,
        enrichment=enrichment,
        polling=polling,
        state=state,
        scoring=scoring,
        rules=rules,
        dashboards=dashboards,
        auth=auth,
        database=database,
        notifications=notifications,
    )


def write_default_config(path: Path) -> None:
    """Write a starter configuration file."""
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")
