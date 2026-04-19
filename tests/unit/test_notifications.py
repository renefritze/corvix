"""Unit tests for the notifications package (detector, dispatcher, dedupe)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from corvix.domain import Notification, NotificationRecord
from corvix.notifications.dedupe import dedupe_events, make_seen_set
from corvix.notifications.detector import detect_new_unread_events
from corvix.notifications.dispatcher import NotificationDispatcher
from corvix.notifications.models import DeliveryResult, NotificationEvent
from corvix.notifications.targets.base import NotificationTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


def _notification(
    thread_id: str = "1",
    unread: bool = True,
    repository: str = "org/repo",
    reason: str = "mention",
) -> Notification:
    return Notification(
        thread_id=thread_id,
        repository=repository,
        reason=reason,
        subject_title=f"Title {thread_id}",
        subject_type="PullRequest",
        unread=unread,
        updated_at=_NOW - timedelta(hours=1),
        web_url=f"https://github.com/org/repo/pull/{thread_id}",
    )


def _record(
    thread_id: str = "1",
    unread: bool = True,
    excluded: bool = False,
    dismissed: bool = False,
    score: float = 10.0,
) -> NotificationRecord:
    return NotificationRecord(
        notification=_notification(thread_id=thread_id, unread=unread),
        score=score,
        excluded=excluded,
        dismissed=dismissed,
    )


# ---------------------------------------------------------------------------
# detector tests
# ---------------------------------------------------------------------------


class TestDetectNewUnreadEvents:
    def test_brand_new_unread_notification_generates_event(self) -> None:
        current = [_record("1", unread=True)]
        events = detect_new_unread_events(previous=[], current=current)
        assert len(events) == 1
        assert events[0].thread_id == "1"

    def test_read_notification_does_not_generate_event(self) -> None:
        current = [_record("1", unread=False)]
        events = detect_new_unread_events(previous=[], current=current)
        assert events == []

    def test_already_seen_unread_does_not_generate_event(self) -> None:
        prev = [_record("1", unread=True)]
        current = [_record("1", unread=True)]
        events = detect_new_unread_events(previous=prev, current=current)
        assert events == []

    def test_read_to_unread_transition_generates_event(self) -> None:
        prev = [_record("1", unread=False)]
        current = [_record("1", unread=True)]
        events = detect_new_unread_events(previous=prev, current=current)
        assert len(events) == 1
        assert events[0].thread_id == "1"

    def test_excluded_record_does_not_generate_event(self) -> None:
        current = [_record("1", unread=True, excluded=True)]
        events = detect_new_unread_events(previous=[], current=current)
        assert events == []

    def test_dismissed_record_does_not_generate_event(self) -> None:
        current = [_record("1", unread=True, dismissed=True)]
        events = detect_new_unread_events(previous=[], current=current)
        assert events == []

    def test_min_score_filters_low_score_records(self) -> None:
        current = [_record("1", unread=True, score=2.0)]
        events = detect_new_unread_events(previous=[], current=current, min_score=5.0)
        assert events == []

    def test_min_score_passes_records_at_threshold(self) -> None:
        current = [_record("1", unread=True, score=5.0)]
        events = detect_new_unread_events(previous=[], current=current, min_score=5.0)
        assert len(events) == 1

    def test_include_read_false_skips_read_records(self) -> None:
        current = [_record("1", unread=False)]
        events = detect_new_unread_events(previous=[], current=current, include_read=False)
        assert events == []

    def test_include_read_true_emits_events_for_read_records(self) -> None:
        current = [_record("1", unread=False), _record("2", unread=True)]
        events = detect_new_unread_events(previous=[], current=current, include_read=True)
        assert len(events) == 2
        assert {e.thread_id for e in events} == {"1", "2"}

    def test_multiple_new_records_all_generate_events(self) -> None:
        current = [_record("1", unread=True), _record("2", unread=True), _record("3", unread=False)]
        events = detect_new_unread_events(previous=[], current=current)
        assert len(events) == 2
        thread_ids = {e.thread_id for e in events}
        assert thread_ids == {"1", "2"}

    def test_event_fields_populated_correctly(self) -> None:
        current = [_record("42", unread=True, score=7.5)]
        events = detect_new_unread_events(previous=[], current=current)
        e = events[0]
        assert e.event_id == "primary:42"
        assert e.account_id == "primary"
        assert e.thread_id == "42"
        assert e.repository == "org/repo"
        assert e.reason == "mention"
        assert e.score == pytest.approx(7.5)
        assert e.unread is True

    def test_empty_inputs_returns_empty(self) -> None:
        assert detect_new_unread_events(previous=[], current=[]) == []


# ---------------------------------------------------------------------------
# dispatcher tests
# ---------------------------------------------------------------------------


class RecordingTarget:
    """Test double that records received events."""

    def __init__(self, name: str = "recording") -> None:
        self._name = name
        self.received: list[NotificationEvent] = []

    @property
    def name(self) -> str:
        return self._name

    def deliver(self, events: list[NotificationEvent]) -> DeliveryResult:
        self.received.extend(events)
        return DeliveryResult(
            target=self._name,
            events_attempted=len(events),
            events_delivered=len(events),
        )


class FailingTarget:
    """Test double that always raises."""

    @property
    def name(self) -> str:
        return "failing"

    def deliver(self, events: list[NotificationEvent]) -> DeliveryResult:
        raise RuntimeError("delivery boom")


class ErrorReportingTarget:
    """Test double that returns errors inside DeliveryResult."""

    @property
    def name(self) -> str:
        return "error-reporting"

    def deliver(self, events: list[NotificationEvent]) -> DeliveryResult:
        return DeliveryResult(
            target=self.name,
            events_attempted=len(events),
            events_delivered=0,
            errors=["some downstream error"],
        )


def _make_event(thread_id: str = "1") -> NotificationEvent:
    return NotificationEvent(
        event_id=thread_id,
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="PR title",
        subject_type="PullRequest",
        web_url=None,
        updated_at=_NOW,
        score=10.0,
        unread=True,
    )


# Verify RecordingTarget satisfies the protocol.
_: NotificationTarget = RecordingTarget()


class TestNotificationDispatcher:
    def test_dispatches_events_to_single_target(self) -> None:
        target = RecordingTarget()
        dispatcher = NotificationDispatcher(targets=[target])
        events = [_make_event("1"), _make_event("2")]
        result = dispatcher.dispatch(events)
        assert len(target.received) == 2
        assert result.total_delivered == 2

    def test_empty_events_is_noop(self) -> None:
        target = RecordingTarget()
        dispatcher = NotificationDispatcher(targets=[target])
        result = dispatcher.dispatch([])
        assert target.received == []
        assert result.total_delivered == 0
        assert result.results == []

    def test_fan_out_to_multiple_targets(self) -> None:
        t1 = RecordingTarget("t1")
        t2 = RecordingTarget("t2")
        dispatcher = NotificationDispatcher(targets=[t1, t2])
        events = [_make_event("1")]
        dispatcher.dispatch(events)
        assert len(t1.received) == 1
        assert len(t2.received) == 1

    def test_failing_target_does_not_block_others(self) -> None:
        good = RecordingTarget("good")
        bad = FailingTarget()
        dispatcher = NotificationDispatcher(targets=[bad, good])
        events = [_make_event("1")]
        result = dispatcher.dispatch(events)
        assert len(good.received) == 1
        # The failing target's result should record the error.
        failing_result = next(r for r in result.results if r.target == "failing")
        assert len(failing_result.errors) == 1
        assert failing_result.events_delivered == 0

    def test_error_reporting_target_surfaced_in_result(self) -> None:
        target = ErrorReportingTarget()
        dispatcher = NotificationDispatcher(targets=[target])
        result = dispatcher.dispatch([_make_event("1")])
        assert result.total_errors == 1
        assert result.total_delivered == 0

    def test_dispatch_result_aggregates_across_targets(self) -> None:
        t1 = RecordingTarget("t1")
        t2 = ErrorReportingTarget()
        dispatcher = NotificationDispatcher(targets=[t1, t2])
        result = dispatcher.dispatch([_make_event("1")])
        assert result.total_delivered == 1
        assert result.total_errors == 1


# ---------------------------------------------------------------------------
# dedupe tests
# ---------------------------------------------------------------------------


class TestDedupeEvents:
    def test_all_new_events_pass_through(self) -> None:
        events = [_make_event("1"), _make_event("2")]
        fresh, new_seen = dedupe_events(events, seen=set())
        assert len(fresh) == 2
        assert new_seen == {"1", "2"}

    def test_already_seen_events_filtered(self) -> None:
        events = [_make_event("1"), _make_event("2")]
        fresh, new_seen = dedupe_events(events, seen={"1"})
        assert len(fresh) == 1
        assert fresh[0].event_id == "2"
        assert "1" in new_seen

    def test_seen_set_not_mutated(self) -> None:
        original_seen: set[str] = {"1"}
        events = [_make_event("2")]
        _, new_seen = dedupe_events(events, seen=original_seen)
        assert original_seen == {"1"}  # original unchanged
        assert new_seen == {"1", "2"}

    def test_make_seen_set_from_events(self) -> None:
        events = [_make_event("a"), _make_event("b")]
        seen = make_seen_set(events)
        assert seen == {"a", "b"}

    def test_empty_inputs(self) -> None:
        fresh, new_seen = dedupe_events([], seen=set())
        assert fresh == []
        assert new_seen == set()
