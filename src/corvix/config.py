"""YAML configuration for Corvix dashboards and polling."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class MatchCriteria:
    """Filter fields for rules and dashboards."""

    repository_in: list[str] = field(default_factory=list)
    reason_in: list[str] = field(default_factory=list)
    subject_type_in: list[str] = field(default_factory=list)
    title_contains_any: list[str] = field(default_factory=list)
    title_regex: str | None = None
    unread: bool | None = None
    min_score: float | None = None
    max_age_hours: float | None = None


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

    interval_seconds: int = 300
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
class StateConfig:
    """State/cache location for persisted notifications."""

    cache_file: Path = Path("~/.cache/corvix/notifications.json")


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
    polling: PollingConfig = field(default_factory=PollingConfig)
    state: StateConfig = field(default_factory=StateConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    rules: RuleSet = field(default_factory=RuleSet)
    dashboards: list[DashboardSpec] = field(default_factory=list)
    auth: AuthConfig = field(default_factory=AuthConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    def resolve_cache_file(self) -> Path:
        """Resolve the configured cache path."""
        return self.state.cache_file.expanduser().resolve()


DEFAULT_CONFIG = """\
github:
  token_env: GITHUB_TOKEN
  api_base_url: https://api.github.com

polling:
  interval_seconds: 300
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
  - name: triage
    group_by: repository
    sort_by: score
    descending: true
    include_read: false
    max_items: 100
    match:
      reason_in: ["mention", "review_requested", "assign"]
  - name: overview
    group_by: reason
    sort_by: updated_at
    descending: true
    include_read: true
    max_items: 200
"""


def load_config(path: Path) -> AppConfig:
    """Load and validate YAML config from disk."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = "Top-level YAML must be a map/object."
        raise ValueError(msg)

    github = _parse_github(data.get("github", {}))
    polling = _parse_polling(data.get("polling", {}))
    state = _parse_state(data.get("state", {}))
    scoring = _parse_scoring(data.get("scoring", {}))
    rules = _parse_rules(data.get("rules", {}))
    dashboards = _parse_dashboards(data.get("dashboards", []))
    auth = _parse_auth(data.get("auth", {}))
    database = _parse_database(data.get("database", {}))
    return AppConfig(
        github=github,
        polling=polling,
        state=state,
        scoring=scoring,
        rules=rules,
        dashboards=dashboards,
        auth=auth,
        database=database,
    )


def write_default_config(path: Path) -> None:
    """Write a starter configuration file."""
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")


def _ensure_map(value: object, section: str) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    msg = f"Config section '{section}' must be a map/object."
    raise ValueError(msg)


def _ensure_list(value: object, section: str) -> list[object]:
    if isinstance(value, list):
        return value
    msg = f"Config section '{section}' must be a list."
    raise ValueError(msg)


def _to_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = "Expected a list."
        raise ValueError(msg)
    return [str(item) for item in value]


def _parse_match(value: object) -> MatchCriteria:
    match = _ensure_map(value, "match")
    return MatchCriteria(
        repository_in=_to_str_list(match.get("repository_in")),
        reason_in=_to_str_list(match.get("reason_in")),
        subject_type_in=_to_str_list(match.get("subject_type_in")),
        title_contains_any=_to_str_list(match.get("title_contains_any")),
        title_regex=str(match["title_regex"]) if "title_regex" in match else None,
        unread=bool(match["unread"]) if "unread" in match else None,
        min_score=float(match["min_score"]) if "min_score" in match else None,
        max_age_hours=float(match["max_age_hours"]) if "max_age_hours" in match else None,
    )


def _parse_rules(value: object) -> RuleSet:
    rules_map = _ensure_map(value, "rules")
    global_rules = [_parse_rule(item) for item in _ensure_list(rules_map.get("global", []), "rules.global")]
    per_repo_rules: dict[str, list[Rule]] = {}
    per_repo = _ensure_map(rules_map.get("per_repository", {}), "rules.per_repository")
    for repository, raw_rules in per_repo.items():
        key = str(repository)
        per_repo_rules[key] = [_parse_rule(item) for item in _ensure_list(raw_rules, f"rules.per_repository.{key}")]
    return RuleSet(global_rules=global_rules, per_repository=per_repo_rules)


def _parse_rule(value: object) -> Rule:
    rule_map = _ensure_map(value, "rule")
    name = str(rule_map.get("name", "unnamed-rule"))
    actions_payload = _ensure_list(rule_map.get("actions", []), f"rule '{name}' actions")
    actions = [
        RuleAction(action_type=str(_ensure_map(action, "rule action").get("type", ""))) for action in actions_payload
    ]
    return Rule(
        name=name,
        match=_parse_match(rule_map.get("match", {})),
        actions=actions,
        exclude_from_dashboards=bool(rule_map.get("exclude_from_dashboards", False)),
    )


def _parse_dashboards(value: object) -> list[DashboardSpec]:
    dashboards = _ensure_list(value, "dashboards")
    parsed: list[DashboardSpec] = []
    for raw_dashboard in dashboards:
        dashboard = _ensure_map(raw_dashboard, "dashboard entry")
        name = str(dashboard.get("name", "default"))
        parsed.append(
            DashboardSpec(
                name=name,
                group_by=str(dashboard.get("group_by", "none")),
                sort_by=str(dashboard.get("sort_by", "score")),
                descending=bool(dashboard.get("descending", True)),
                include_read=bool(dashboard.get("include_read", False)),
                max_items=int(dashboard.get("max_items", 100)),
                match=_parse_match(dashboard.get("match", {})),
            ),
        )
    return parsed


def _parse_scoring(value: object) -> ScoringConfig:
    scoring = _ensure_map(value, "scoring")
    return ScoringConfig(
        unread_bonus=float(scoring.get("unread_bonus", 15.0)),
        age_decay_per_hour=float(scoring.get("age_decay_per_hour", 0.25)),
        reason_weights=_to_float_map(scoring.get("reason_weights", {}), "scoring.reason_weights"),
        repository_weights=_to_float_map(scoring.get("repository_weights", {}), "scoring.repository_weights"),
        subject_type_weights=_to_float_map(scoring.get("subject_type_weights", {}), "scoring.subject_type_weights"),
        title_keyword_weights=_to_float_map(scoring.get("title_keyword_weights", {}), "scoring.title_keyword_weights"),
    )


def _to_float_map(value: object, section: str) -> dict[str, float]:
    data = _ensure_map(value, section)
    return {str(key): float(raw_value) for key, raw_value in data.items()}


def _parse_github(value: object) -> GitHubConfig:
    github = _ensure_map(value, "github")
    return GitHubConfig(
        token_env=str(github.get("token_env", "GITHUB_TOKEN")),
        api_base_url=str(github.get("api_base_url", "https://api.github.com")),
    )


def _parse_polling(value: object) -> PollingConfig:
    polling = _ensure_map(value, "polling")
    return PollingConfig(
        interval_seconds=int(polling.get("interval_seconds", 300)),
        per_page=int(polling.get("per_page", 50)),
        max_pages=int(polling.get("max_pages", 5)),
        all=bool(polling.get("all", False)),
        participating=bool(polling.get("participating", False)),
    )


def _parse_state(value: object) -> StateConfig:
    state = _ensure_map(value, "state")
    return StateConfig(cache_file=Path(str(state.get("cache_file", "~/.cache/corvix/notifications.json"))))


def _parse_auth(value: object) -> AuthConfig:
    auth = _ensure_map(value, "auth")
    return AuthConfig(
        mode=str(auth.get("mode", "single_user")),
        session_secret=str(auth.get("session_secret", "")),
    )


def _parse_database(value: object) -> DatabaseConfig:
    database = _ensure_map(value, "database")
    return DatabaseConfig(url_env=str(database.get("url_env", "DATABASE_URL")))
