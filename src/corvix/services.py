"""Application services orchestrating ingestion, actions, and rendering."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast

from rich.console import Console

from corvix.actions import ActionExecutionContext, DismissGateway, MarkReadGateway, execute_actions
from corvix.config import AppConfig, DashboardSpec, PollingConfig
from corvix.domain import Notification, NotificationRecord, notification_key
from corvix.enrichment.base import EnrichmentProvider, JsonFetchClient
from corvix.enrichment.engine import EnrichmentEngine
from corvix.enrichment.providers.github_latest_comment import GitHubLatestCommentProvider
from corvix.enrichment.providers.github_pr_state import GitHubPRStateProvider
from corvix.ingestion import WebUrlEnricher, resolve_web_urls
from corvix.notifications.detector import detect_new_unread_events
from corvix.notifications.dispatcher import NotificationDispatcher
from corvix.notifications.models import DispatchResult
from corvix.notifications.targets.base import NotificationTarget
from corvix.presentation import DashboardRenderResult, render_dashboards
from corvix.rules import evaluate_rules
from corvix.scoring import score_notification
from corvix.storage import NotificationCache


class NotificationsClient(MarkReadGateway, JsonFetchClient, Protocol):
    """Client capabilities required by the poll cycle orchestration."""

    def fetch_notifications(self, polling: PollingConfig) -> list[Notification]:
        """Fetch notifications with configured polling options."""
        ...


@dataclass(slots=True)
class PollingSummary:
    """Result of one polling cycle."""

    fetched: int
    excluded: int
    actions_taken: int
    errors: list[str] = field(default_factory=list)
    dispatch: DispatchResult | None = None


@dataclass(slots=True)
class PollCycleInput:
    """All inputs required by :func:`run_poll_cycle`.

    Attributes:
        config: Application configuration.
        clients: GitHub notifications clients.
        cache: Persistent notification cache.
        apply_actions: If ``False``, actions are recorded as dry-run only.
        now: Override the current time (useful for testing).
        notification_targets: Optional notification dispatch targets.
    """

    config: AppConfig
    cache: NotificationCache
    clients: tuple[NotificationsClient, ...] = field(default_factory=tuple)
    client: NotificationsClient | None = None
    apply_actions: bool = False
    now: datetime | None = None
    notification_targets: list[NotificationTarget] | None = None


def run_poll_cycle(input: PollCycleInput) -> PollingSummary:  # noqa: PLR0915
    """Fetch notifications, score/evaluate, optionally execute actions, and persist cache.

    If ``input.notification_targets`` is provided (and
    ``input.config.notifications.enabled`` is ``True``) the poll cycle will
    detect newly-arrived unread notifications and fan-out delivery to each
    target after saving the snapshot.
    """
    current_time = input.now if input.now is not None else datetime.now(tz=UTC)
    active_clients = input.clients or ((input.client,) if input.client is not None else ())
    if not active_clients:
        msg = "At least one notifications client is required for polling."
        raise ValueError(msg)

    # Load previous snapshot for newness detection before overwriting.
    notif_cfg = input.config.notifications
    previous_records: list[NotificationRecord] = []
    if notif_cfg.enabled and input.notification_targets:
        _, previous_records = input.cache.load()

    notifications: list[Notification] = []
    clients_by_account: dict[str, NotificationsClient] = {}
    for client in active_clients:
        fetched = client.fetch_notifications(input.config.polling)
        notifications.extend(fetched)
        if fetched:
            clients_by_account[fetched[0].account_id] = client
    enrichers_by_account: dict[str, WebUrlEnricher] = {}
    for client in active_clients:
        if isinstance(client, WebUrlEnricher):
            account_id = getattr(client, "account_id", "primary")
            if isinstance(account_id, str) and account_id:
                enrichers_by_account[account_id] = cast(WebUrlEnricher, client)
    for notification in notifications:
        resolve_web_urls([notification], enricher=enrichers_by_account.get(notification.account_id))
    enrichment_engine = EnrichmentEngine(
        config=input.config.enrichment,
        providers=_build_enrichment_providers(input.config),
    )
    enrichment_client = active_clients[0]
    enrichment_clients: dict[str, JsonFetchClient] = {key: value for key, value in clients_by_account.items()}
    enrichment_result = enrichment_engine.run(
        notifications=notifications,
        client=enrichment_client,
        clients_by_account=enrichment_clients,
    )

    records: list[NotificationRecord] = []
    excluded = 0
    action_count = 0
    errors: list[str] = []
    for notification in notifications:
        record_context = enrichment_result.contexts_by_notification_key.get(notification_key(notification), {})
        score = score_notification(notification=notification, config=input.config.scoring, now=current_time)
        evaluation = evaluate_rules(
            notification=notification,
            score=score,
            rules=input.config.rules,
            now=current_time,
            context=record_context,
        )
        record = NotificationRecord(
            notification=notification,
            score=score,
            excluded=evaluation.excluded,
            matched_rules=evaluation.matched_rules,
            context=record_context,
        )
        gateway_client = clients_by_account.get(notification.account_id)
        if gateway_client is None:
            errors.append(f"No client found for account '{notification.account_id}'.")
            continue
        action_result = execute_actions(
            notification=notification,
            actions=evaluation.actions,
            context=ActionExecutionContext(
                gateway=gateway_client,
                apply_actions=input.apply_actions,
                dismiss_gateway=gateway_client if isinstance(gateway_client, DismissGateway) else None,
                record=record,
            ),
        )
        record.actions_taken = action_result.actions_taken
        errors.extend(action_result.errors)
        action_count += len(action_result.actions_taken)
        if evaluation.excluded:
            excluded += 1
        records.append(record)

    errors.extend(f"enrichment: {error}" for error in enrichment_result.errors)
    input.cache.save(records=records, generated_at=current_time)

    # Detect new events and dispatch to targets.
    dispatch: DispatchResult | None = None
    if notif_cfg.enabled and input.notification_targets:
        events = detect_new_unread_events(
            previous=previous_records,
            current=records,
            min_score=notif_cfg.detect.min_score,
            include_read=notif_cfg.detect.include_read,
        )
        dispatcher = NotificationDispatcher(targets=input.notification_targets)
        dispatch = dispatcher.dispatch(events)

    return PollingSummary(
        fetched=len(notifications),
        excluded=excluded,
        actions_taken=action_count,
        errors=errors,
        dispatch=dispatch,
    )


def run_watch_loop(  # noqa: PLR0913
    config: AppConfig,
    cache: NotificationCache,
    apply_actions: bool,
    clients: tuple[NotificationsClient, ...] | None = None,
    client: NotificationsClient | None = None,
    iterations: int | None = None,
) -> list[PollingSummary]:
    """Run polling loop suitable for local daemon usage."""
    runs: list[PollingSummary] = []
    active_clients = clients or ((client,) if client is not None else ())
    iteration = 0
    while iterations is None or iteration < iterations:
        runs.append(
            run_poll_cycle(
                PollCycleInput(
                    config=config,
                    clients=active_clients,
                    cache=cache,
                    apply_actions=apply_actions,
                )
            ),
        )
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


def _build_enrichment_providers(config: AppConfig) -> list[EnrichmentProvider]:
    providers: list[EnrichmentProvider] = []
    if config.enrichment.github_latest_comment.enabled:
        providers.append(
            GitHubLatestCommentProvider(
                timeout_seconds=config.enrichment.github_latest_comment.timeout_seconds,
            )
        )
    if config.enrichment.github_pr_state.enabled:
        providers.append(
            GitHubPRStateProvider(
                timeout_seconds=config.enrichment.github_pr_state.timeout_seconds,
            )
        )
    return providers
