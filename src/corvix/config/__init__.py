"""Corvix configuration package.

This package exposes every public name that was previously in the monolithic
``corvix/config.py`` module so that all existing imports continue to work
without modification.

Sub-modules:

* ``config.rules``         — MatchCriteria, ContextPredicate, Rule, RuleSet, RuleAction
* ``config.dashboards``    — DashboardSpec + dashboard helpers
* ``config.scoring``       — ScoringConfig
* ``config.notifications`` — NotificationsConfig and delivery-target configs
* ``config.github``        — GitHubAccountConfig, GitHubConfig
* ``config.app``           — AppConfig, auxiliary configs, load_config, write_default_config
"""

from __future__ import annotations

# Re-export everything from sub-modules so ``from corvix.config import X`` works unchanged.
from corvix.config.app import (
    DEFAULT_CONFIG,
    AppConfig,
    AuthConfig,
    DatabaseConfig,
    EnrichmentConfig,
    GitHubLatestCommentEnrichmentConfig,
    GitHubPRStateEnrichmentConfig,
    PollingConfig,
    StateConfig,
    load_config,
    write_default_config,
)
from corvix.config.dashboards import (
    NO_FILTERS_DASHBOARD_NAME,
    DashboardSpec,
    available_dashboards,
    default_dashboard,
    is_no_filters_dashboard,
    no_filters_dashboard,
)
from corvix.config.github import (
    DEFAULT_GITHUB_API_BASE_URL,
    GitHubAccountConfig,
    GitHubConfig,
)
from corvix.config.notifications import (
    BrowserTabTargetConfig,
    NotificationsConfig,
    NotificationsDetectConfig,
    WebPushTargetConfig,
)
from corvix.config.rules import (
    ContextPredicate,
    MatchCriteria,
    Rule,
    RuleAction,
    RuleSet,
)
from corvix.config.scoring import ScoringConfig

__all__ = [
    "DEFAULT_CONFIG",
    "DEFAULT_GITHUB_API_BASE_URL",
    "NO_FILTERS_DASHBOARD_NAME",
    "AppConfig",
    "AuthConfig",
    "BrowserTabTargetConfig",
    "ContextPredicate",
    "DashboardSpec",
    "DatabaseConfig",
    "EnrichmentConfig",
    "GitHubAccountConfig",
    "GitHubConfig",
    "GitHubLatestCommentEnrichmentConfig",
    "GitHubPRStateEnrichmentConfig",
    "MatchCriteria",
    "NotificationsConfig",
    "NotificationsDetectConfig",
    "PollingConfig",
    "Rule",
    "RuleAction",
    "RuleSet",
    "ScoringConfig",
    "StateConfig",
    "WebPushTargetConfig",
    "available_dashboards",
    "default_dashboard",
    "is_no_filters_dashboard",
    "load_config",
    "no_filters_dashboard",
    "write_default_config",
]
