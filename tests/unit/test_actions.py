"""Tests for action execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from corvix.actions import ActionExecutionContext, DismissGateway, MarkReadGateway, execute_actions
from corvix.config import RuleAction
from corvix.domain import Notification, NotificationRecord
from corvix.web.app import INDEX_HTML


def _make_notification(thread_id: str = "1", unread: bool = True) -> Notification:
    return Notification(
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="Test",
        subject_type="PullRequest",
        unread=unread,
        updated_at=datetime.now(tz=UTC) - timedelta(hours=1),
    )


def _make_record(notification: Notification, dismissed: bool = False) -> NotificationRecord:
    return NotificationRecord(notification=notification, score=10.0, excluded=False, dismissed=dismissed)


class FakeMarkRead:
    def __init__(self) -> None:
        self.marked: list[str] = []

    def mark_thread_read(self, thread_id: str) -> None:
        self.marked.append(thread_id)


class FakeDismiss:
    def __init__(self) -> None:
        self.dismissed: list[str] = []

    def dismiss_thread(self, thread_id: str) -> None:
        self.dismissed.append(thread_id)


class FakeFullClient(FakeMarkRead, FakeDismiss):
    def __init__(self) -> None:
        self.marked: list[str] = []
        self.dismissed: list[str] = []


class FailMarkRead:
    def mark_thread_read(self, thread_id: str) -> None:
        raise RuntimeError("API error")


class FailDismiss:
    def dismiss_thread(self, thread_id: str) -> None:
        raise RuntimeError("dismiss error")


# --- Protocol conformance ---


def test_fake_mark_read_implements_protocol() -> None:
    gw: MarkReadGateway = FakeMarkRead()  # type: ignore[assignment]
    gw.mark_thread_read("x")


def test_fake_dismiss_implements_protocol() -> None:
    gw: DismissGateway = FakeDismiss()  # type: ignore[assignment]
    gw.dismiss_thread("x")


# --- mark_read action ---


def test_mark_read_action_in_dry_run() -> None:
    notification = _make_notification()
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="mark_read")],
        context=ActionExecutionContext(gateway=FakeMarkRead(), apply_actions=False),
    )
    assert result.actions_taken == ["dry-run:mark_read"]
    assert notification.unread is True


def test_mark_read_action_applies() -> None:
    gw = FakeMarkRead()
    notification = _make_notification()
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="mark_read")],
        context=ActionExecutionContext(gateway=gw, apply_actions=True),
    )
    assert result.actions_taken == ["mark_read"]
    assert notification.unread is False
    assert gw.marked == ["1"]


def test_mark_read_skipped_if_already_read() -> None:
    gw = FakeMarkRead()
    result = execute_actions(
        notification=_make_notification(unread=False),
        actions=[RuleAction(action_type="mark_read")],
        context=ActionExecutionContext(gateway=gw, apply_actions=True),
    )
    assert result.actions_taken == []
    assert gw.marked == []


def test_mark_read_exception_records_error() -> None:
    result = execute_actions(
        notification=_make_notification(),
        actions=[RuleAction(action_type="mark_read")],
        context=ActionExecutionContext(
            gateway=FailMarkRead(),  # type: ignore[arg-type]
            apply_actions=True,
        ),
    )
    assert result.actions_taken == []
    assert any("mark_read failed" in err for err in result.errors)


# --- dismiss action ---


def test_dismiss_action_in_dry_run() -> None:
    client = FakeFullClient()
    notification = _make_notification()
    record = _make_record(notification)
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="dismiss")],
        context=ActionExecutionContext(
            gateway=client,
            apply_actions=False,
            dismiss_gateway=client,
            record=record,
        ),
    )
    assert result.actions_taken == ["dry-run:dismiss"]
    assert client.dismissed == []
    assert record.dismissed is False


def test_dismiss_action_applies() -> None:
    client = FakeFullClient()
    notification = _make_notification()
    record = _make_record(notification)
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="dismiss")],
        context=ActionExecutionContext(
            gateway=client,
            apply_actions=True,
            dismiss_gateway=client,
            record=record,
        ),
    )
    assert result.actions_taken == ["dismiss"]
    assert client.dismissed == ["1"]
    assert record.dismissed is True


def test_dismiss_skipped_if_already_dismissed() -> None:
    client = FakeFullClient()
    notification = _make_notification()
    record = _make_record(notification, dismissed=True)
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="dismiss")],
        context=ActionExecutionContext(
            gateway=client,
            apply_actions=True,
            dismiss_gateway=client,
            record=record,
        ),
    )
    assert result.actions_taken == []
    assert client.dismissed == []


def test_dismiss_without_gateway_records_error() -> None:
    result = execute_actions(
        notification=_make_notification(),
        actions=[RuleAction(action_type="dismiss")],
        context=ActionExecutionContext(gateway=FakeMarkRead(), apply_actions=True),
    )
    assert any("no dismiss_gateway" in err for err in result.errors)


def test_dismiss_exception_records_error() -> None:
    notification = _make_notification()
    record = _make_record(notification)
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="dismiss")],
        context=ActionExecutionContext(
            gateway=FakeMarkRead(),
            apply_actions=True,
            dismiss_gateway=FailDismiss(),  # type: ignore[arg-type]
            record=record,
        ),
    )
    assert result.actions_taken == []
    assert any("dismiss failed" in err for err in result.errors)


def test_unknown_action_records_error() -> None:
    result = execute_actions(
        notification=_make_notification(),
        actions=[RuleAction(action_type="unknown_action")],
        context=ActionExecutionContext(gateway=FakeMarkRead(), apply_actions=True),
    )
    assert any("Unsupported action" in err for err in result.errors)


def test_deduplicates_duplicate_actions() -> None:
    gw = FakeMarkRead()
    notification = _make_notification()
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="mark_read"), RuleAction(action_type="mark_read")],
        context=ActionExecutionContext(gateway=gw, apply_actions=True),
    )
    assert result.actions_taken == ["mark_read"]
    assert len(gw.marked) == 1


# --- SPA smoke tests ---


def test_index_html_is_spa_shell() -> None:
    """INDEX_HTML is now a compiled SPA shell; verify it mounts correctly."""
    assert '<div id="app">' in INDEX_HTML
    assert "Corvix" in INDEX_HTML
