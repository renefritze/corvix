"""Dashboard query helpers shared across presentation layers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from corvix.config import DashboardSpec
from corvix.domain import NotificationRecord
from corvix.rules import matches_criteria


@dataclass(slots=True)
class DashboardItem:
    """JSON-friendly notification item for UI rendering."""

    thread_id: str
    repository: str
    reason: str
    subject_type: str
    subject_title: str
    unread: bool
    updated_at: str
    score: float
    web_url: str | None = None
    matched_rules: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)

    @classmethod
    def from_record(cls, record: NotificationRecord) -> DashboardItem:
        """Create a UI item from a stored notification record."""
        notification = record.notification
        return cls(
            thread_id=notification.thread_id,
            repository=notification.repository,
            reason=notification.reason,
            subject_type=notification.subject_type,
            subject_title=notification.subject_title,
            unread=notification.unread,
            updated_at=notification.updated_at.isoformat(),
            score=record.score,
            web_url=notification.web_url,
            matched_rules=record.matched_rules,
            actions_taken=record.actions_taken,
        )


@dataclass(slots=True)
class DashboardGroup:
    """A dashboard group such as repository or reason."""

    name: str
    items: list[DashboardItem]


@dataclass(slots=True)
class DashboardData:
    """Full dashboard payload for web and CLI presentation."""

    name: str
    generated_at: str | None
    groups: list[DashboardGroup]
    total_items: int
    summary: DashboardSummary


@dataclass(slots=True)
class DashboardSummary:
    """Snapshot metadata used by the dashboard shell."""

    unread_items: int
    read_items: int
    group_count: int
    repository_count: int
    reason_count: int


def build_dashboard_data(
    records: list[NotificationRecord],
    dashboard: DashboardSpec,
    generated_at: datetime | None = None,
    now: datetime | None = None,
) -> DashboardData:
    """Select, sort, group, and serialize records for a dashboard."""
    current_time = now if now is not None else datetime.now(tz=UTC)
    selected = [
        record for record in records if _included_by_dashboard(record=record, dashboard=dashboard, now=current_time)
    ]
    sorted_records = sorted(
        selected,
        key=lambda record: _sort_key(record=record, sort_by=dashboard.sort_by),
        reverse=dashboard.descending,
    )
    if dashboard.max_items > 0:
        sorted_records = sorted_records[: dashboard.max_items]
    grouped_records = _group_records(records=sorted_records, group_by=dashboard.group_by)
    groups = [
        DashboardGroup(
            name=group_name,
            items=[DashboardItem.from_record(record) for record in group_items],
        )
        for group_name, group_items in grouped_records.items()
    ]
    return DashboardData(
        name=dashboard.name,
        generated_at=generated_at.isoformat() if generated_at is not None else None,
        groups=groups,
        total_items=sum(len(group.items) for group in groups),
        summary=_build_summary(sorted_records=sorted_records, groups=groups),
    )


def _included_by_dashboard(
    record: NotificationRecord,
    dashboard: DashboardSpec,
    now: datetime,
) -> bool:
    if record.excluded:
        return False
    if record.dismissed:
        return False
    if not dashboard.include_read and not record.notification.unread:
        return False
    return matches_criteria(
        criteria=dashboard.match,
        notification=record.notification,
        score=record.score,
        now=now,
    )


def _sort_key(record: NotificationRecord, sort_by: str) -> object:
    notification = record.notification
    if sort_by == "updated_at":
        return notification.updated_at
    if sort_by == "repository":
        return notification.repository
    if sort_by == "reason":
        return notification.reason
    if sort_by == "subject_type":
        return notification.subject_type
    if sort_by == "title":
        return notification.subject_title
    return record.score


def _group_records(
    records: list[NotificationRecord],
    group_by: str,
) -> dict[str, list[NotificationRecord]]:
    if group_by in {"none", ""}:
        return {"all": records}
    grouped: dict[str, list[NotificationRecord]] = defaultdict(list)
    for record in records:
        if group_by == "repository":
            key = record.notification.repository
        elif group_by == "reason":
            key = record.notification.reason
        elif group_by == "subject_type":
            key = record.notification.subject_type
        else:
            key = "all"
        grouped[key].append(record)
    return dict(grouped)


def _build_summary(
    sorted_records: list[NotificationRecord],
    groups: list[DashboardGroup],
) -> DashboardSummary:
    unread_items = sum(1 for record in sorted_records if record.notification.unread)
    repositories = {record.notification.repository for record in sorted_records}
    reasons = {record.notification.reason for record in sorted_records}
    return DashboardSummary(
        unread_items=unread_items,
        read_items=len(sorted_records) - unread_items,
        group_count=len(groups),
        repository_count=len(repositories),
        reason_count=len(reasons),
    )
