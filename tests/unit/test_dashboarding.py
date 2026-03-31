"""Dashboard query helper tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from corvix.config import DashboardSpec, MatchCriteria
from corvix.dashboarding import DashboardItem, build_dashboard_data
from corvix.domain import Notification, NotificationRecord

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_record(
    *,
    thread_id: str,
    repository: str = "org/a",
    reason: str = "mention",
    subject_title: str = "Fix bug",
    subject_type: str = "PullRequest",
    unread: bool = True,
    score: float = 10.0,
    updated_at: datetime | None = None,
    excluded: bool = False,
    dismissed: bool = False,
) -> NotificationRecord:
    return NotificationRecord(
        notification=Notification(
            thread_id=thread_id,
            repository=repository,
            reason=reason,
            subject_title=subject_title,
            subject_type=subject_type,
            unread=unread,
            updated_at=updated_at or NOW,
        ),
        score=score,
        excluded=excluded,
        dismissed=dismissed,
    )


# --- basic filtering ---


def test_build_dashboard_data_filters_and_groups() -> None:
    records = [
        _make_record(thread_id="1", repository="org/a", reason="mention", score=42.0),
        _make_record(thread_id="2", repository="org/b", reason="subscribed", unread=False, score=5.0),
    ]
    dashboard = DashboardSpec(
        name="triage",
        group_by="repository",
        sort_by="score",
        descending=True,
        include_read=False,
        match=MatchCriteria(reason_in=["mention"]),
    )

    data = build_dashboard_data(records=records, dashboard=dashboard, generated_at=NOW)

    assert data.name == "triage"
    assert data.total_items == 1
    assert len(data.groups) == 1
    assert data.groups[0].name == "org/a"
    assert data.groups[0].items[0].thread_id == "1"


def test_excluded_records_filtered_out() -> None:
    records = [
        _make_record(thread_id="1", excluded=False),
        _make_record(thread_id="2", excluded=True),
    ]
    data = build_dashboard_data(records=records, dashboard=DashboardSpec(name="d", include_read=True), generated_at=NOW)
    assert data.total_items == 1
    assert data.groups[0].items[0].thread_id == "1"


def test_dismissed_records_filtered_out() -> None:
    records = [
        _make_record(thread_id="1", dismissed=False),
        _make_record(thread_id="2", dismissed=True),
    ]
    data = build_dashboard_data(records=records, dashboard=DashboardSpec(name="d", include_read=True), generated_at=NOW)
    assert data.total_items == 1
    assert data.groups[0].items[0].thread_id == "1"


def test_read_records_excluded_when_include_read_false() -> None:
    records = [
        _make_record(thread_id="1", unread=True),
        _make_record(thread_id="2", unread=False),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", include_read=False),
        generated_at=NOW,
    )
    assert data.total_items == 1
    assert data.groups[0].items[0].thread_id == "1"


def test_read_records_included_when_include_read_true() -> None:
    records = [
        _make_record(thread_id="1", unread=True),
        _make_record(thread_id="2", unread=False),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", include_read=True),
        generated_at=NOW,
    )
    assert data.total_items == 2


# --- sorting ---


def test_sort_by_score_descending() -> None:
    records = [_make_record(thread_id="low", score=5.0), _make_record(thread_id="high", score=50.0)]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", sort_by="score", descending=True, include_read=True),
        generated_at=NOW,
    )
    assert data.groups[0].items[0].thread_id == "high"


def test_sort_by_score_ascending() -> None:
    records = [_make_record(thread_id="low", score=5.0), _make_record(thread_id="high", score=50.0)]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", sort_by="score", descending=False, include_read=True),
        generated_at=NOW,
    )
    assert data.groups[0].items[0].thread_id == "low"


def test_sort_by_updated_at() -> None:
    records = [
        _make_record(thread_id="old", updated_at=NOW - timedelta(hours=2)),
        _make_record(thread_id="new", updated_at=NOW),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", sort_by="updated_at", descending=True, include_read=True),
        generated_at=NOW,
    )
    assert data.groups[0].items[0].thread_id == "new"


def test_sort_by_repository() -> None:
    records = [
        _make_record(thread_id="b", repository="org/b"),
        _make_record(thread_id="a", repository="org/a"),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", sort_by="repository", descending=False, include_read=True),
        generated_at=NOW,
    )
    assert data.groups[0].items[0].thread_id == "a"


def test_sort_by_reason() -> None:
    records = [
        _make_record(thread_id="sub", reason="subscribed"),
        _make_record(thread_id="men", reason="mention"),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", sort_by="reason", descending=False, include_read=True),
        generated_at=NOW,
    )
    assert data.groups[0].items[0].thread_id == "men"


def test_sort_by_title() -> None:
    records = [
        _make_record(thread_id="z", subject_title="z-title"),
        _make_record(thread_id="a", subject_title="a-title"),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", sort_by="title", descending=False, include_read=True),
        generated_at=NOW,
    )
    assert data.groups[0].items[0].thread_id == "a"


# --- max_items truncation ---


def test_max_items_truncation() -> None:
    records = [_make_record(thread_id=str(i), score=float(i)) for i in range(10)]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", max_items=3, include_read=True),
        generated_at=NOW,
    )
    assert data.total_items == 3


def test_max_items_zero_means_no_limit() -> None:
    records = [_make_record(thread_id=str(i)) for i in range(5)]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", max_items=0, include_read=True),
        generated_at=NOW,
    )
    assert data.total_items == 5


# --- grouping ---


def test_group_by_none_produces_single_all_group() -> None:
    records = [_make_record(thread_id="1", repository="org/a"), _make_record(thread_id="2", repository="org/b")]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", group_by="none", include_read=True),
        generated_at=NOW,
    )
    assert len(data.groups) == 1
    assert data.groups[0].name == "all"
    assert data.total_items == 2


def test_group_by_reason() -> None:
    records = [
        _make_record(thread_id="1", reason="mention"),
        _make_record(thread_id="2", reason="subscribed"),
        _make_record(thread_id="3", reason="mention"),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", group_by="reason", include_read=True),
        generated_at=NOW,
    )
    group_names = {g.name for g in data.groups}
    assert "mention" in group_names
    assert "subscribed" in group_names
    assert data.total_items == 3


def test_group_by_subject_type() -> None:
    records = [
        _make_record(thread_id="1", subject_type="PullRequest"),
        _make_record(thread_id="2", subject_type="Issue"),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", group_by="subject_type", include_read=True),
        generated_at=NOW,
    )
    group_names = {g.name for g in data.groups}
    assert "PullRequest" in group_names
    assert "Issue" in group_names


def test_group_by_unknown_key_falls_back_to_all() -> None:
    records = [_make_record(thread_id="1"), _make_record(thread_id="2")]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", group_by="invalid", include_read=True),
        generated_at=NOW,
    )
    assert len(data.groups) == 1
    assert data.groups[0].name == "all"
    assert data.total_items == 2


# --- summary ---


def test_summary_unread_count() -> None:
    records = [
        _make_record(thread_id="1", unread=True),
        _make_record(thread_id="2", unread=False),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", include_read=True),
        generated_at=NOW,
    )
    assert data.summary.unread_items == 1
    assert data.summary.read_items == 1


def test_summary_repository_count() -> None:
    records = [
        _make_record(thread_id="1", repository="org/a"),
        _make_record(thread_id="2", repository="org/b"),
        _make_record(thread_id="3", repository="org/a"),
    ]
    data = build_dashboard_data(
        records=records,
        dashboard=DashboardSpec(name="d", include_read=True),
        generated_at=NOW,
    )
    assert data.summary.repository_count == 2


# --- DashboardItem.from_record ---


def test_dashboard_item_from_record() -> None:
    record = _make_record(thread_id="42", score=99.5)
    item = DashboardItem.from_record(record)
    assert item.thread_id == "42"
    assert item.score == 99.5
    assert item.repository == "org/a"
