"""Application services orchestrating ingestion, actions, and rendering."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from rich.console import Console

from corvix.actions import execute_actions
from corvix.config import AppConfig, DashboardSpec
from corvix.domain import NotificationRecord
from corvix.ingestion import GitHubNotificationsClient, WebUrlEnricher, resolve_web_urls
from corvix.presentation import DashboardRenderResult, render_dashboards
from corvix.rules import evaluate_rules
from corvix.scoring import score_notification
from corvix.storage import NotificationCache


@dataclass(slots=True)
class PollingSummary:
    """Result of one polling cycle."""

    fetched: int
    excluded: int
    actions_taken: int
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PollOptions:
    """Per-cycle options for a polling run."""

    apply_actions: bool = False
    now: datetime | None = None
    enricher: WebUrlEnricher | None = None


def run_poll_cycle(
    config: AppConfig,
    client: GitHubNotificationsClient,
    cache: NotificationCache,
    options: PollOptions,
) -> PollingSummary:
    """Fetch notifications, score/evaluate, optionally execute actions, and persist cache."""
    current_time = options.now if options.now is not None else datetime.now(tz=UTC)
    notifications = client.fetch_notifications(config.polling)
    resolve_web_urls(notifications, enricher=options.enricher)

    records: list[NotificationRecord] = []
    excluded = 0
    action_count = 0
    errors: list[str] = []
    for notification in notifications:
        score = score_notification(notification=notification, config=config.scoring, now=current_time)
        evaluation = evaluate_rules(
            notification=notification,
            score=score,
            rules=config.rules,
            now=current_time,
        )
        action_result = execute_actions(
            notification=notification,
            actions=evaluation.actions,
            gateway=client,
            apply_actions=options.apply_actions,
            dismiss_gateway=client,
        )
        errors.extend(action_result.errors)
        action_count += len(action_result.actions_taken)
        if evaluation.excluded:
            excluded += 1
        records.append(
            NotificationRecord(
                notification=notification,
                score=score,
                excluded=evaluation.excluded,
                matched_rules=evaluation.matched_rules,
                actions_taken=action_result.actions_taken,
            ),
        )

    cache.save(records=records, generated_at=current_time)
    return PollingSummary(
        fetched=len(notifications),
        excluded=excluded,
        actions_taken=action_count,
        errors=errors,
    )


def run_watch_loop(
    config: AppConfig,
    client: GitHubNotificationsClient,
    cache: NotificationCache,
    options: PollOptions,
    iterations: int | None = None,
) -> list[PollingSummary]:
    """Run polling loop suitable for local daemon usage."""
    runs: list[PollingSummary] = []
    iteration = 0
    while iterations is None or iteration < iterations:
        runs.append(run_poll_cycle(config=config, client=client, cache=cache, options=options))
        iteration += 1
        if iterations is not None and iteration >= iterations:
            break
        time.sleep(config.polling.interval_seconds)
    return runs


def render_cached_dashboards(
    config: AppConfig,
    cache: NotificationCache,
    console: Console,
    dashboard_name: str | None = None,
) -> list[DashboardRenderResult]:
    """Load persisted records and render dashboards."""
    generated_at, records = cache.load()
    dashboards = _select_dashboards(config, dashboard_name)
    return render_dashboards(
        console=console,
        records=records,
        dashboards=dashboards,
        generated_at=generated_at,
    )


def _select_dashboards(config: AppConfig, dashboard_name: str | None) -> list[DashboardSpec]:
    dashboards = config.dashboards or [
        DashboardSpec(name="default", group_by="repository", sort_by="score"),
    ]
    if dashboard_name is None:
        return dashboards
    selected = [dashboard for dashboard in dashboards if dashboard.name == dashboard_name]
    if not selected:
        msg = f"Dashboard '{dashboard_name}' not found."
        raise ValueError(msg)
    return selected
