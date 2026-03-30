"""Dashboard query helper tests."""

from __future__ import annotations

from datetime import UTC, datetime

from corvix.config import DashboardSpec, MatchCriteria
from corvix.dashboarding import build_dashboard_data
from corvix.domain import Notification, NotificationRecord


def test_build_dashboard_data_filters_and_groups() -> None:
    now = datetime.now(tz=UTC)
    records = [
        NotificationRecord(
            notification=Notification(
                thread_id="1",
                repository="org/a",
                reason="mention",
                subject_title="review please",
                subject_type="PullRequest",
                unread=True,
                updated_at=now,
                web_url="https://github.com/org/a/pull/1",
            ),
            score=42.0,
            excluded=False,
        ),
        NotificationRecord(
            notification=Notification(
                thread_id="2",
                repository="org/b",
                reason="subscribed",
                subject_title="noise",
                subject_type="Issue",
                unread=False,
                updated_at=now,
            ),
            score=5.0,
            excluded=False,
        ),
    ]
    dashboard = DashboardSpec(
        name="triage",
        group_by="repository",
        sort_by="score",
        descending=True,
        include_read=False,
        match=MatchCriteria(reason_in=["mention"]),
    )

    data = build_dashboard_data(records=records, dashboard=dashboard, generated_at=now)

    assert data.name == "triage"
    assert data.total_items == 1
    assert len(data.groups) == 1
    assert data.groups[0].name == "org/a"
    assert data.groups[0].items[0].thread_id == "1"
    assert data.groups[0].items[0].web_url == "https://github.com/org/a/pull/1"
    assert data.summary.unread_items == 1
    assert data.summary.read_items == 0
    assert data.summary.group_count == 1
    assert data.summary.repository_count == 1
    assert data.summary.reason_count == 1


def test_build_dashboard_data_excludes_dismissed_records() -> None:
    now = datetime.now(tz=UTC)
    dashboard = DashboardSpec(name="triage", group_by="repository", sort_by="score", descending=True, include_read=True)
    records = [
        NotificationRecord(
            notification=Notification(
                thread_id="1",
                repository="org/a",
                reason="mention",
                subject_title="keep me",
                subject_type="PullRequest",
                unread=True,
                updated_at=now,
            ),
            score=42.0,
            excluded=False,
        ),
        NotificationRecord(
            notification=Notification(
                thread_id="2",
                repository="org/a",
                reason="mention",
                subject_title="dismissed",
                subject_type="Issue",
                unread=True,
                updated_at=now,
            ),
            score=40.0,
            excluded=False,
            dismissed=True,
        ),
    ]

    data = build_dashboard_data(records=records, dashboard=dashboard, generated_at=now)

    assert data.total_items == 1
    assert [item.thread_id for item in data.groups[0].items] == ["1"]
