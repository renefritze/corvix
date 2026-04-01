"""Service orchestration integration tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from rich.console import Console

from corvix.config import (
    AppConfig,
    DashboardSpec,
    MatchCriteria,
    PollingConfig,
    Rule,
    RuleAction,
    RuleSet,
    ScoringConfig,
    StateConfig,
)
from corvix.domain import Notification
from corvix.services import PollCycleInput, _select_dashboards, render_cached_dashboards, run_poll_cycle, run_watch_loop
from corvix.storage import NotificationCache

EXPECTED_FETCHED = 2
EXPECTED_EXCLUDED = 1
EXPECTED_COMPLEX_FETCHED = 3
EXPECTED_WATCH_ITERATIONS = 2


class FakeClient:
    def __init__(self, notifications: list[Notification]) -> None:
        self._notifications = notifications
        self.marked_thread_ids: list[str] = []

    def fetch_notifications(self, _polling: PollingConfig) -> list[Notification]:
        return deepcopy(self._notifications)

    def mark_thread_read(self, thread_id: str) -> None:
        self.marked_thread_ids.append(thread_id)


def _build_config(cache_path: Path) -> AppConfig:
    return AppConfig(
        polling=PollingConfig(max_pages=1, per_page=10, interval_seconds=0),
        state=StateConfig(cache_file=cache_path),
        scoring=ScoringConfig(reason_weights={"mention": 20}, unread_bonus=10, age_decay_per_hour=0),
        rules=RuleSet(
            global_rules=[
                Rule(
                    name="mute-bots",
                    match=MatchCriteria(title_contains_any=["bot"]),
                    actions=[RuleAction(action_type="mark_read")],
                    exclude_from_dashboards=True,
                ),
            ],
        ),
        dashboards=[
            DashboardSpec(name="triage", group_by="repository", sort_by="score", include_read=True),
        ],
    )


def _build_notifications(now: datetime) -> list[Notification]:
    return [
        Notification(
            thread_id="1",
            repository="org/repo",
            reason="mention",
            subject_title="Please review",
            subject_type="PullRequest",
            unread=True,
            updated_at=now - timedelta(hours=1),
            thread_url="https://api.github.com/notifications/threads/1",
        ),
        Notification(
            thread_id="2",
            repository="org/repo",
            reason="subscribed",
            subject_title="dependabot bot update",
            subject_type="PullRequest",
            unread=True,
            updated_at=now - timedelta(hours=2),
            thread_url="https://api.github.com/notifications/threads/2",
        ),
    ]


def test_poll_cycle_applies_actions_and_persists_cache(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    cache_path = tmp_path / "notifications.json"
    config = _build_config(cache_path=cache_path)
    client = FakeClient(_build_notifications(now))
    cache = NotificationCache(path=cache_path)

    summary = run_poll_cycle(
        PollCycleInput(
            config=config,
            client=client,
            cache=cache,
            apply_actions=True,
            now=now,
        )
    )

    assert summary.fetched == EXPECTED_FETCHED
    assert summary.excluded == EXPECTED_EXCLUDED
    assert summary.actions_taken == 1
    assert client.marked_thread_ids == ["2"]

    generated_at, records = cache.load()
    assert generated_at is not None
    assert len(records) == EXPECTED_FETCHED
    assert len([record for record in records if record.excluded]) == EXPECTED_EXCLUDED
    assert records[1].actions_taken == ["mark_read"]


def test_dashboard_renders_from_cached_records(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    cache_path = tmp_path / "notifications.json"
    config = _build_config(cache_path=cache_path)
    client = FakeClient(_build_notifications(now))
    cache = NotificationCache(path=cache_path)

    run_poll_cycle(
        PollCycleInput(
            config=config,
            client=client,
            cache=cache,
            apply_actions=False,
            now=now,
        )
    )

    console = Console(record=True)
    results = render_cached_dashboards(
        config=config,
        cache=cache,
        console=console,
        dashboard_name="triage",
    )

    assert len(results) == 1
    assert results[0].dashboard_name == "triage"
    assert results[0].rows == 1


def test_poll_with_global_and_repository_rules(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    cache_path = tmp_path / "notifications.json"
    config = AppConfig(
        polling=PollingConfig(max_pages=1, per_page=10, interval_seconds=0),
        state=StateConfig(cache_file=cache_path),
        scoring=ScoringConfig(
            unread_bonus=5,
            age_decay_per_hour=0,
            reason_weights={"mention": 40},
            repository_weights={"org/critical": 20},
            title_keyword_weights={"urgent": 10},
        ),
        rules=RuleSet(
            global_rules=[
                Rule(
                    name="mute-bots",
                    match=MatchCriteria(title_contains_any=["bot"]),
                    actions=[RuleAction(action_type="mark_read")],
                    exclude_from_dashboards=True,
                )
            ],
            per_repository={
                "org/critical": [
                    Rule(
                        name="critical-chore",
                        match=MatchCriteria(title_contains_any=["chore"]),
                        actions=[RuleAction(action_type="mark_read")],
                    )
                ]
            },
        ),
        dashboards=[
            DashboardSpec(name="overview", group_by="repository", sort_by="score", include_read=True),
            DashboardSpec(name="triage", group_by="reason", sort_by="score", include_read=True),
        ],
    )
    client = FakeClient(
        [
            Notification(
                thread_id="1",
                repository="org/critical",
                reason="mention",
                subject_title="Urgent fix needed",
                subject_type="PullRequest",
                unread=True,
                updated_at=now - timedelta(hours=1),
                thread_url="https://api.github.com/notifications/threads/1",
            ),
            Notification(
                thread_id="2",
                repository="org/critical",
                reason="subscribed",
                subject_title="chore bot update",
                subject_type="PullRequest",
                unread=True,
                updated_at=now - timedelta(hours=1),
                thread_url="https://api.github.com/notifications/threads/2",
            ),
            Notification(
                thread_id="3",
                repository="org/other",
                reason="subscribed",
                subject_title="normal update",
                subject_type="PullRequest",
                unread=True,
                updated_at=now - timedelta(hours=1),
                thread_url="https://api.github.com/notifications/threads/3",
            ),
        ]
    )
    cache = NotificationCache(path=cache_path)

    summary = run_poll_cycle(
        PollCycleInput(
            config=config,
            client=client,
            cache=cache,
            apply_actions=True,
            now=now,
        )
    )
    _, records = cache.load()
    by_id = {record.notification.thread_id: record for record in records}

    assert summary.fetched == EXPECTED_COMPLEX_FETCHED
    assert summary.excluded == 1
    assert summary.actions_taken == 1
    assert client.marked_thread_ids == ["2"]
    assert by_id["1"].score > by_id["3"].score
    assert by_id["2"].matched_rules == ["mute-bots", "critical-chore"]
    assert by_id["2"].excluded is True


def test_poll_then_dismiss_then_render_excludes_notification(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    cache_path = tmp_path / "notifications.json"
    config = _build_config(cache_path=cache_path)
    client = FakeClient(_build_notifications(now))
    cache = NotificationCache(path=cache_path)

    run_poll_cycle(
        PollCycleInput(
            config=config,
            client=client,
            cache=cache,
            apply_actions=False,
            now=now,
        )
    )
    cache.dismiss_record(user_id="", thread_id="1")

    console = Console(record=True)
    results = render_cached_dashboards(
        config=config,
        cache=cache,
        console=console,
        dashboard_name="triage",
    )
    rendered_text = console.export_text()

    assert len(results) == 1
    assert results[0].rows == 0
    assert "Please review" not in rendered_text


def test_watch_loop_runs_n_iterations(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    cache_path = tmp_path / "notifications.json"
    config = _build_config(cache_path=cache_path)
    client = FakeClient(_build_notifications(now))
    cache = NotificationCache(path=cache_path)

    summaries = run_watch_loop(
        config=config,
        client=client,
        cache=cache,
        apply_actions=False,
        iterations=2,
    )

    assert len(summaries) == EXPECTED_WATCH_ITERATIONS
    assert all(s.fetched == EXPECTED_FETCHED for s in summaries)


# --- _select_dashboards ---


def test_select_dashboards_returns_all_when_none(tmp_path: Path) -> None:
    config = _build_config(tmp_path / "cache.json")
    selected = _select_dashboards(config, None)
    assert len(selected) == 1
    assert selected[0].name == "triage"


def test_select_dashboards_returns_named(tmp_path: Path) -> None:
    config = _build_config(tmp_path / "cache.json")
    selected = _select_dashboards(config, "triage")
    assert len(selected) == 1
    assert selected[0].name == "triage"


def test_select_dashboards_raises_for_missing(tmp_path: Path) -> None:
    config = _build_config(tmp_path / "cache.json")
    with pytest.raises(ValueError, match="not found"):
        _select_dashboards(config, "nonexistent")


def test_select_dashboards_default_when_no_config_dashboards(tmp_path: Path) -> None:
    config = _build_config(tmp_path / "cache.json")
    config.dashboards.clear()
    selected = _select_dashboards(config, None)
    assert len(selected) == 1
    assert selected[0].name == "default"
