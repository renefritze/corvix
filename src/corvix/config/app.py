"""AppConfig root model, auxiliary config classes, and load_config/write_default_config."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from corvix.config._utils import (
    _ensure_map,
    _get_bool,
    _get_float,
    _get_int,
    _get_str,
)
from corvix.config.dashboards import DashboardSpec, _parse_dashboards
from corvix.config.github import DEFAULT_GITHUB_API_BASE_URL, GitHubConfig, _parse_github
from corvix.config.notifications import NotificationsConfig, _parse_notifications
from corvix.config.rules import RuleSet, _parse_rules
from corvix.config.scoring import ScoringConfig, _parse_scoring

_POLLING_PER_PAGE_MIN = 1
_POLLING_PER_PAGE_MAX = 50


@dataclass(slots=True)
class PollingConfig:
    """Polling behavior for ingestion."""

    interval_seconds: int = 60
    request_timeout_seconds: float = 30.0
    per_page: int = 50
    max_pages: int = 5
    all: bool = False
    participating: bool = False


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
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)

    def resolve_cache_file(self) -> Path:
        """Resolve the configured cache path."""
        return self.state.cache_file.expanduser().resolve()


DEFAULT_CONFIG = f"""\
github:
  accounts:
    - id: primary
      label: Primary
      token_env: GITHUB_TOKEN
      api_base_url: {DEFAULT_GITHUB_API_BASE_URL}

# Optional enrichment providers that add context used by rules/dashboards.
enrichment:
  # Master switch for all enrichment providers.
  enabled: false
  # Global request budget shared by providers each poll cycle.
  max_requests_per_cycle: 25
  # Adds github.latest_comment.* context for comment-based filtering.
  github_latest_comment:
    # Enable latest-comment metadata lookups.
    enabled: false
    # HTTP timeout per request made by this provider.
    timeout_seconds: 10
  # Adds github.pr_state.* context for PR-state/author filtering.
  github_pr_state:
    # Enable pull-request state metadata lookups.
    enabled: false
    # HTTP timeout per request made by this provider.
    timeout_seconds: 10

# Polling behavior for fetching notifications from GitHub.
polling:
  # Watch-loop delay between poll cycles, in seconds.
  interval_seconds: 60
  # HTTP timeout per GitHub API request, in seconds.
  request_timeout_seconds: 30
  # GitHub page size per request (valid range: 1-50).
  per_page: 50
  # Maximum pages to fetch per cycle to cap API usage.
  max_pages: 5
  # Include notifications from repositories you are not participating in.
  all: false
  # Restrict results to threads you participate in when true.
  participating: false

# Priority scoring model used when sort_by=score.
scoring:
  # Points added to unread notifications.
  unread_bonus: 15
  # Points subtracted per hour since last update.
  age_decay_per_hour: 0.25
  # Extra points by GitHub reason (mention/review_requested/etc).
  reason_weights:
    mention: 50
    review_requested: 40
    assign: 30
    author: 10
  # Per-repository score adjustments (repo full_name -> points).
  repository_weights:
    your-org/critical-repo: 25
  # Score adjustments by subject type (Issue, PullRequest, etc).
  subject_type_weights:
    PullRequest: 10
  # Case-insensitive keyword boosts when title contains the key.
  title_keyword_weights:
    security: 20
    urgent: 15

# Automation rules evaluated for each notification after scoring.
rules:
  # Rules applied to all repositories.
  global:
    # Rule name appears in matched_rules for traceability.
    - name: mute-bot-noise
      # Match criteria: all provided fields must match.
      match:
        # Regex against notification title.
        title_regex: ".*\\[bot\\].*"
      # Actions to execute when the rule matches.
      actions:
        # mark_read marks a thread as read (dry-run unless apply_actions=true).
        - type: mark_read
      # Hide matching records from dashboards while still processing them.
      exclude_from_dashboards: true
  # Repository-specific rules map: repo full_name -> list of rules.
  per_repository:
    your-org/infra:
      - name: mute-chore-prs
        match:
          # Match when title contains any listed keyword.
          title_contains_any: ["chore", "deps"]
        actions:
          - type: mark_read
        exclude_from_dashboards: true

# Event detection + delivery targets for user-facing notifications.
notifications:
  # Master switch for event detection and dispatch.
  enabled: true
  # Controls which records qualify as notification events.
  detect:
    # Include read records in event detection when true.
    include_read: false
    # Minimum score threshold required for event emission.
    min_score: 0
  # In-tab browser delivery target (shown while dashboard tab is open).
  browser_tab:
    # Enable browser-tab deliveries.
    enabled: true
    # Max events sent to this target per poll cycle.
    max_per_cycle: 5
    # Per-thread delivery cooldown in seconds to suppress repeats.
    cooldown_seconds: 10
  # Background Web Push delivery target.
  web_push:
    # Enable Web Push delivery.
    enabled: false
    # Env var name containing VAPID public key.
    vapid_public_key_env: CORVIX_VAPID_PUBLIC_KEY
    # Env var name containing VAPID private key.
    vapid_private_key_env: CORVIX_VAPID_PRIVATE_KEY
    # Web Push contact subject (recommended: mailto:<team@example.com>).
    subject: ""

# Dashboards rendered in UI; first entry is selected by default.
dashboards:
  # Unique dashboard name used in routes and selector.
  - name: overview
    # Grouping key: none | repository | reason | subject_type.
    group_by: reason
    # Sort key: score | updated_at | repository | reason | subject_type | title.
    sort_by: updated_at
    # Sort order for selected sort_by field.
    descending: true
    # Include read records when true.
    include_read: true
    # Maximum records shown (<=0 means no truncation).
    max_items: 200
  - name: triage
    # Grouping key: none | repository | reason | subject_type.
    group_by: repository
    # Sort key: score | updated_at | repository | reason | subject_type | title.
    sort_by: score
    # Sort order for selected sort_by field.
    descending: true
    # Include read records when true.
    include_read: false
    # Maximum records shown (<=0 means no truncation).
    max_items: 100
    # Additional include filter (same schema as rule match).
    match:
      reason_in: ["mention", "review_requested", "assign"]
    # Exclusion filters applied after match/include checks.
    ignore_rules:
      - reason_in: ["comment"]
        context:
          # Dot path into enrichment context payload.
          - path: github.latest_comment.is_ci_only
            # Predicate operator: equals | not_equals | contains | regex | in | exists.
            op: equals
            # Value compared by the operator.
            value: true

# Database settings (used by DB-backed storage/migrations/commands).
database:
  # Env var holding SQLAlchemy database URL (also supports <VAR>_FILE).
  url_env: DATABASE_URL
"""


def _parse_polling(value: object) -> PollingConfig:
    polling = _ensure_map(value, "polling")
    per_page = _get_int(polling, "per_page", _POLLING_PER_PAGE_MAX, "polling.per_page")
    if not _POLLING_PER_PAGE_MIN <= per_page <= _POLLING_PER_PAGE_MAX:
        msg = f"Config value 'polling.per_page' must be between {_POLLING_PER_PAGE_MIN} and {_POLLING_PER_PAGE_MAX}."
        raise ValueError(msg)
    request_timeout_seconds = _get_float(
        polling,
        "request_timeout_seconds",
        30.0,
        "polling.request_timeout_seconds",
    )
    if request_timeout_seconds <= 0:
        msg = "Config value 'polling.request_timeout_seconds' must be greater than 0."
        raise ValueError(msg)
    return PollingConfig(
        interval_seconds=_get_int(polling, "interval_seconds", 60, "polling.interval_seconds"),
        request_timeout_seconds=request_timeout_seconds,
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
    max_requests_per_cycle = _get_int(
        enrichment,
        "max_requests_per_cycle",
        25,
        "enrichment.max_requests_per_cycle",
    )
    if max_requests_per_cycle < 0:
        msg = "Config value 'enrichment.max_requests_per_cycle' must be >= 0."
        raise ValueError(msg)
    latest_comment_timeout = _get_float(
        latest_comment_raw,
        "timeout_seconds",
        10.0,
        "enrichment.github_latest_comment.timeout_seconds",
    )
    if latest_comment_timeout <= 0:
        msg = "Config value 'enrichment.github_latest_comment.timeout_seconds' must be greater than 0."
        raise ValueError(msg)
    pr_state_timeout = _get_float(
        pr_state_raw,
        "timeout_seconds",
        10.0,
        "enrichment.github_pr_state.timeout_seconds",
    )
    if pr_state_timeout <= 0:
        msg = "Config value 'enrichment.github_pr_state.timeout_seconds' must be greater than 0."
        raise ValueError(msg)
    return EnrichmentConfig(
        enabled=_get_bool(enrichment, "enabled", False, "enrichment.enabled"),
        max_requests_per_cycle=max_requests_per_cycle,
        github_latest_comment=GitHubLatestCommentEnrichmentConfig(
            enabled=_get_bool(latest_comment_raw, "enabled", False, "enrichment.github_latest_comment.enabled"),
            timeout_seconds=latest_comment_timeout,
        ),
        github_pr_state=GitHubPRStateEnrichmentConfig(
            enabled=_get_bool(pr_state_raw, "enabled", False, "enrichment.github_pr_state.enabled"),
            timeout_seconds=pr_state_timeout,
        ),
    )


def _parse_state(value: object) -> StateConfig:
    state = _ensure_map(value, "state")
    return StateConfig(
        cache_file=Path(_get_str(state, "cache_file", "~/.cache/corvix/notifications.json", "state.cache_file"))
    )


def _parse_database(value: object) -> DatabaseConfig:
    database = _ensure_map(value, "database")
    return DatabaseConfig(url_env=_get_str(database, "url_env", "DATABASE_URL", "database.url_env"))


def load_config(path: Path) -> AppConfig:
    """Load and validate YAML config from disk."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        msg = f"Failed to parse config file '{path}': {error}"
        raise ValueError(msg) from error
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
        database=database,
        notifications=notifications,
    )


def write_default_config(path: Path) -> None:
    """Write a starter configuration file."""
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")
