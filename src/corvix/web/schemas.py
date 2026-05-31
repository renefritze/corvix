"""Typed response schemas for the Corvix web API.

These dataclasses are the single source of truth for the JSON shapes returned
by the ``/api/v1`` route handlers. Litestar serializes them directly and
auto-generates an OpenAPI document from their annotations; the frontend's
TypeScript types are code-generated from that document (see
``scripts/export_openapi.py`` and ``frontend/src/api-types.gen.ts``).

Every field is required (no defaults) so the generated OpenAPI schema marks
each property as required and the TypeScript types never become accidentally
optional. ``str | None`` fields map to a nullable-but-present property, matching
how the handlers always emit the key.
"""

from __future__ import annotations

from dataclasses import dataclass

from corvix.config.notifications import NotificationsConfig
from corvix.dashboarding import DashboardData, DashboardItem


@dataclass(slots=True)
class DashboardItemResponse:
    """A single notification row rendered by the dashboard table."""

    account_id: str
    account_label: str
    thread_id: str
    repository: str
    reason: str
    subject_type: str
    subject_title: str
    unread: bool
    updated_at: str
    score: float
    web_url: str | None
    matched_rules: list[str]
    actions_taken: list[str]


@dataclass(slots=True)
class DashboardGroupResponse:
    """A group of dashboard items (e.g. grouped by repository or reason)."""

    name: str
    items: list[DashboardItemResponse]


@dataclass(slots=True)
class DashboardSummaryResponse:
    """Aggregate counts shown in the dashboard shell."""

    unread_items: int
    read_items: int
    group_count: int
    repository_count: int
    reason_count: int


@dataclass(slots=True)
class PollerStatusResponse:
    """Poller health surfaced to the UI for the staleness warning banner."""

    status: str
    last_poll_time: str | None
    last_error: str | None
    last_error_time: str | None
    stale: bool


@dataclass(slots=True)
class BrowserTabNotificationsConfigResponse:
    """In-tab browser notification settings echoed to the frontend."""

    enabled: bool
    max_per_cycle: int
    cooldown_seconds: int


@dataclass(slots=True)
class NotificationsConfigResponse:
    """Notification configuration relevant to the browser client."""

    enabled: bool
    browser_tab: BrowserTabNotificationsConfigResponse


@dataclass(slots=True)
class SnapshotResponse:
    """Full dashboard snapshot returned by ``GET /api/v1/snapshot``."""

    name: str
    include_read: bool
    sort_by: str
    descending: bool
    generated_at: str | None
    groups: list[DashboardGroupResponse]
    total_items: int
    summary: DashboardSummaryResponse
    dashboard_names: list[str]
    poller: PollerStatusResponse
    notifications_config: NotificationsConfigResponse | None


@dataclass(slots=True)
class RuleSnippetsResponse:
    """Prefilled ignore-rule snippets for a single notification."""

    dashboard_name: str
    dashboard_ignore_rule_snippet: str
    global_exclude_rule_snippet: str
    dashboard_ignore_rule_with_context_snippet: str | None
    global_exclude_rule_with_context_snippet: str | None
    has_context: bool


def _dashboard_item_response(item: DashboardItem) -> DashboardItemResponse:
    """Convert a ``dashboarding.DashboardItem`` into its response schema."""
    return DashboardItemResponse(
        account_id=item.account_id,
        account_label=item.account_label,
        thread_id=item.thread_id,
        repository=item.repository,
        reason=item.reason,
        subject_type=item.subject_type,
        subject_title=item.subject_title,
        unread=item.unread,
        updated_at=item.updated_at,
        score=item.score,
        web_url=item.web_url,
        matched_rules=list(item.matched_rules),
        actions_taken=list(item.actions_taken),
    )


def build_snapshot_response(
    *,
    data: DashboardData,
    dashboard_names: list[str],
    poller: PollerStatusResponse,
    notifications_config: NotificationsConfig | None,
) -> SnapshotResponse:
    """Assemble a typed :class:`SnapshotResponse` from dashboard data.

    Centralizes the mapping from the internal ``DashboardData`` dataclass (plus
    the already-resolved poller status and config state) to the wire schema so
    the route handler stays thin and the contract lives in one place.
    """
    notif: NotificationsConfigResponse | None = None
    if notifications_config is not None:
        browser = notifications_config.browser_tab
        notif = NotificationsConfigResponse(
            enabled=notifications_config.enabled,
            browser_tab=BrowserTabNotificationsConfigResponse(
                enabled=browser.enabled,
                max_per_cycle=browser.max_per_cycle,
                cooldown_seconds=browser.cooldown_seconds,
            ),
        )
    return SnapshotResponse(
        name=data.name,
        include_read=data.include_read,
        sort_by=data.sort_by,
        descending=data.descending,
        generated_at=data.generated_at,
        groups=[
            DashboardGroupResponse(
                name=group.name,
                items=[_dashboard_item_response(item) for item in group.items],
            )
            for group in data.groups
        ],
        total_items=data.total_items,
        summary=DashboardSummaryResponse(
            unread_items=data.summary.unread_items,
            read_items=data.summary.read_items,
            group_count=data.summary.group_count,
            repository_count=data.summary.repository_count,
            reason_count=data.summary.reason_count,
        ),
        dashboard_names=dashboard_names,
        poller=poller,
        notifications_config=notif,
    )
