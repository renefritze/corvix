"""Tests for action execution including dismiss support."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib.resources import files as resource_files

from corvix.actions import DismissGateway, MarkReadGateway, execute_actions
from corvix.config import RuleAction
from corvix.domain import Notification, NotificationRecord


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
    """Implements both MarkReadGateway and DismissGateway."""

    def __init__(self) -> None:
        self.marked: list[str] = []
        self.dismissed: list[str] = []


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
        gateway=FakeMarkRead(),
        apply_actions=False,
    )
    assert result.actions_taken == ["dry-run:mark_read"]
    assert notification.unread is True  # not changed


def test_mark_read_action_applies() -> None:
    gw = FakeMarkRead()
    notification = _make_notification()
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="mark_read")],
        gateway=gw,
        apply_actions=True,
    )
    assert result.actions_taken == ["mark_read"]
    assert notification.unread is False
    assert gw.marked == ["1"]


def test_mark_read_skipped_if_already_read() -> None:
    gw = FakeMarkRead()
    notification = _make_notification(unread=False)
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="mark_read")],
        gateway=gw,
        apply_actions=True,
    )
    assert result.actions_taken == []
    assert gw.marked == []


# --- dismiss action ---


def test_dismiss_action_in_dry_run() -> None:
    client = FakeFullClient()
    notification = _make_notification()
    record = _make_record(notification)
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="dismiss")],
        gateway=client,
        apply_actions=False,
        record=record,
        dismiss_gateway=client,
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
        gateway=client,
        apply_actions=True,
        record=record,
        dismiss_gateway=client,
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
        gateway=client,
        apply_actions=True,
        record=record,
        dismiss_gateway=client,
    )
    assert result.actions_taken == []
    assert client.dismissed == []


def test_dismiss_without_gateway_records_error() -> None:
    notification = _make_notification()
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="dismiss")],
        gateway=FakeMarkRead(),
        apply_actions=True,
    )
    assert result.actions_taken == []
    assert any("no dismiss_gateway" in err for err in result.errors)


def test_unknown_action_records_error() -> None:
    result = execute_actions(
        notification=_make_notification(),
        actions=[RuleAction(action_type="unknown_action")],
        gateway=FakeMarkRead(),
        apply_actions=True,
    )
    assert any("Unsupported action" in err for err in result.errors)


def test_deduplicates_duplicate_actions() -> None:
    gw = FakeMarkRead()
    notification = _make_notification()
    result = execute_actions(
        notification=notification,
        actions=[RuleAction(action_type="mark_read"), RuleAction(action_type="mark_read")],
        gateway=gw,
        apply_actions=True,
    )
    assert result.actions_taken == ["mark_read"]
    assert len(gw.marked) == 1


# --- dismiss endpoint in SPA ---


def test_spa_contains_dismiss_button() -> None:
    built_js = resource_files("corvix.web").joinpath("static/assets/app.js").read_text(encoding="utf-8")
    assert "dismiss-btn" in built_js
    assert "Undo" in built_js
    assert "/api/notifications/" in built_js
