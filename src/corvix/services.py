"""Application services orchestrating ingestion, actions, and rendering."""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol

from rich.console import Console

from corvix.actions import ActionExecutionContext, DismissGateway, MarkReadGateway, execute_actions
from corvix.config import AppConfig, DashboardSpec, PollingConfig, available_dashboards
from corvix.domain import Notification, NotificationRecord, PollerStatus, format_timestamp, notification_key
from corvix.enrichment.base import EnrichmentProvider
from corvix.enrichment.engine import EnrichmentEngine
from corvix.enrichment.providers.github_latest_comment import GitHubLatestCommentProvider
from corvix.enrichment.providers.github_pr_state import GitHubPRStateProvider
from corvix.hydration.base import HydrationProvider
from corvix.hydration.engine import HydrationEngine
from corvix.hydration.providers.github_thread_subject import GitHubThreadSubjectProvider
from corvix.hydration.providers.github_web_url import GitHubWebUrlProvider
from corvix.notifications.detector import detect_new_unread_events
from corvix.notifications.dispatcher import NotificationDispatcher
from corvix.notifications.models import DispatchResult
from corvix.notifications.targets.base import NotificationTarget
from corvix.pipeline.base import JsonFetchClient
from corvix.presentation import DashboardRenderResult, render_dashboards
from corvix.rules import evaluate_rules
from corvix.scoring import score_notification
from corvix.storage import NotificationCache

logger = logging.getLogger(__name__)


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


def run_poll_cycle(cycle_input: PollCycleInput) -> PollingSummary:
    """Fetch notifications, score/evaluate, optionally execute actions, and persist cache.

    If ``cycle_input.notification_targets`` is provided (and
    ``cycle_input.config.notifications.enabled`` is ``True``) the poll cycle will
    detect newly-arrived unread notifications and fan-out delivery to each
    target after saving the snapshot.
    """
    current_time = cycle_input.now if cycle_input.now is not None else datetime.now(tz=UTC)
    active_clients = _resolve_active_clients(cycle_input)
    previous_records = _load_previous_records(cycle_input)

    notifications, clients_by_account = _fetch_notifications(cycle_input.config.polling, active_clients)

    hydration_engine = HydrationEngine(
        providers=_build_hydration_providers(),
        max_requests_per_cycle=cycle_input.config.enrichment.max_requests_per_cycle,
    )
    hydration_client = active_clients[0]
    hydration_clients: dict[str, JsonFetchClient] = dict(clients_by_account)
    hydration_result = hydration_engine.run(
        notifications=notifications,
        client=hydration_client,
        clients_by_account=hydration_clients,
    )
    notifications = hydration_result.notifications

    enrichment_engine = EnrichmentEngine(
        config=cycle_input.config.enrichment,
        providers=_build_enrichment_providers(cycle_input.config),
    )
    enrichment_client = active_clients[0]
    enrichment_clients: dict[str, JsonFetchClient] = dict(clients_by_account)
    enrichment_result = enrichment_engine.run(
        notifications=notifications,
        client=enrichment_client,
        clients_by_account=enrichment_clients,
    )

    records, excluded, action_count, errors = _process_notifications(
        notifications=notifications,
        cycle_input=cycle_input,
        current_time=current_time,
        clients_by_account=clients_by_account,
        contexts_by_notification_key=enrichment_result.contexts_by_notification_key,
    )
    errors.extend(f"hydration: {error}" for error in hydration_result.errors)
    errors.extend(f"enrichment: {error}" for error in enrichment_result.errors)
    cycle_input.cache.save(
        records=records,
        generated_at=current_time,
        poller_status=PollerStatus(
            status="ok",
            last_poll_time=format_timestamp(current_time),
            last_error=None,
            last_error_time=None,
        ),
    )

    dispatch = _dispatch_notification_events(cycle_input, previous_records, records)

    return PollingSummary(
        fetched=len(notifications),
        excluded=excluded,
        actions_taken=action_count,
        errors=errors,
        dispatch=dispatch,
    )


def _resolve_active_clients(cycle_input: PollCycleInput) -> tuple[NotificationsClient, ...]:
    active_clients = cycle_input.clients or ((cycle_input.client,) if cycle_input.client is not None else ())
    if not active_clients:
        msg = "At least one notifications client is required for polling."
        raise ValueError(msg)
    return active_clients


def _load_previous_records(cycle_input: PollCycleInput) -> list[NotificationRecord]:
    if cycle_input.config.notifications.enabled and cycle_input.notification_targets:
        _, previous_records = cycle_input.cache.load()
        return previous_records
    return []


def _fetch_notifications(
    polling: PollingConfig,
    active_clients: tuple[NotificationsClient, ...],
) -> tuple[list[Notification], dict[str, NotificationsClient]]:
    notifications: list[Notification] = []
    clients_by_account: dict[str, NotificationsClient] = {}
    for client in active_clients:
        fetched = client.fetch_notifications(polling)
        notifications.extend(fetched)
        if fetched:
            clients_by_account[fetched[0].account_id] = client
    return notifications, clients_by_account


def _process_notifications(
    notifications: list[Notification],
    cycle_input: PollCycleInput,
    current_time: datetime,
    clients_by_account: dict[str, NotificationsClient],
    contexts_by_notification_key: dict[str, dict[str, object]],
) -> tuple[list[NotificationRecord], int, int, list[str]]:
    records: list[NotificationRecord] = []
    excluded = 0
    action_count = 0
    errors: list[str] = []
    for notification in notifications:
        record_context = contexts_by_notification_key.get(notification_key(notification), {})
        score = score_notification(notification=notification, config=cycle_input.config.scoring, now=current_time)
        evaluation = evaluate_rules(
            notification=notification,
            score=score,
            rules=cycle_input.config.rules,
            now=current_time,
            context=record_context,
        )
        record = NotificationRecord(
            notification=notification,
            score=score,
            excluded=evaluation.excluded,
            matched_rules=tuple(evaluation.matched_rules),
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
                apply_actions=cycle_input.apply_actions,
                dismiss_gateway=gateway_client if isinstance(gateway_client, DismissGateway) else None,
                record=record,
            ),
        )
        new_notification = (
            replace(notification, unread=False)
            if "mark_read" in action_result.actions_taken
            else notification
        )
        record = replace(
            record,
            notification=new_notification,
            actions_taken=tuple(action_result.actions_taken),
            dismissed=record.dismissed or "dismiss" in action_result.actions_taken,
        )
        errors.extend(action_result.errors)
        action_count += len(action_result.actions_taken)
        if evaluation.excluded:
            excluded += 1
        records.append(record)
    return records, excluded, action_count, errors


def _dispatch_notification_events(
    cycle_input: PollCycleInput,
    previous_records: list[NotificationRecord],
    records: list[NotificationRecord],
) -> DispatchResult | None:
    notif_cfg = cycle_input.config.notifications
    if not notif_cfg.enabled or not cycle_input.notification_targets:
        return None
    events = detect_new_unread_events(
        previous=previous_records,
        current=records,
        min_score=notif_cfg.detect.min_score,
        include_read=notif_cfg.detect.include_read,
    )
    dispatcher = NotificationDispatcher(targets=cycle_input.notification_targets)
    return dispatcher.dispatch(events)


def _handle_cycle_error(iteration: int, cache: NotificationCache, runs: list[PollingSummary]) -> None:
    """Record a poll-cycle failure and persist the error status."""
    error_time = datetime.now(tz=UTC)
    error_trace = traceback.format_exc()
    error_msg = error_trace.splitlines()[-1].strip() if error_trace.strip() else "poll cycle failed"
    logger.exception("Poll cycle failed on iteration %d", iteration)
    runs.append(PollingSummary(fetched=0, excluded=0, actions_taken=0, errors=[error_msg]))
    try:
        last_poll_time = cache.load_status().last_poll_time
    except (OSError, ValueError):
        last_poll_time = None
    try:
        cache.save_status(
            PollerStatus(
                status="error",
                last_poll_time=last_poll_time,
                last_error=error_msg,
                last_error_time=format_timestamp(error_time),
            )
        )
    except Exception:
        logger.warning("Failed to persist poller error status", exc_info=True)


def run_watch_loop(
    cycle_input: PollCycleInput,
    iterations: int | None = None,
) -> list[PollingSummary]:
    """Run polling loop suitable for local daemon usage."""
    runs: list[PollingSummary] = []
    iteration = 0
    while iterations is None or iteration < iterations:
        try:
            runs.append(run_poll_cycle(cycle_input))
        except Exception:
            _handle_cycle_error(iteration, cycle_input.cache, runs)
        iteration += 1
        if iterations is not None and iteration >= iterations:
            break
        time.sleep(cycle_input.config.polling.interval_seconds)
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
    dashboards = available_dashboards(config.dashboards)
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


def _build_hydration_providers() -> list[HydrationProvider]:
    return [
        GitHubThreadSubjectProvider(),
        GitHubWebUrlProvider(),
    ]
