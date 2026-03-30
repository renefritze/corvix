"""Action execution for matched rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from corvix.config import RuleAction
from corvix.domain import Notification, NotificationRecord


class MarkReadGateway(Protocol):
    """Gateway interface for marking notification threads as read."""

    def mark_thread_read(self, thread_id: str) -> None:
        """Mark a thread as read."""


class DismissGateway(Protocol):
    """Gateway interface for dismissing (deleting) notification threads."""

    def dismiss_thread(self, thread_id: str) -> None:
        """Dismiss a thread from the inbox permanently."""


@dataclass(slots=True)
class ActionExecutionResult:
    """Summary of actions taken on one notification."""

    actions_taken: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def execute_actions(  # noqa: PLR0912, PLR0913
    notification: Notification,
    actions: list[RuleAction],
    gateway: MarkReadGateway,
    apply_actions: bool,
    record: NotificationRecord | None = None,
    dismiss_gateway: DismissGateway | None = None,
) -> ActionExecutionResult:
    """Execute configured actions against a notification.

    Args:
        notification: The notification to act on.
        actions: The list of rule actions to execute.
        gateway: Must implement MarkReadGateway (mark_thread_read).
        apply_actions: If False, actions are recorded as dry-run only.
        record: The associated NotificationRecord (for dismiss state tracking).
        dismiss_gateway: Must implement DismissGateway; required for dismiss actions.
            Typically the same client as gateway if it supports dismiss_thread.
    """
    result = ActionExecutionResult()
    seen_actions: set[str] = set()
    for action in actions:
        action_type = action.action_type.strip().lower()
        if not action_type or action_type in seen_actions:
            continue
        seen_actions.add(action_type)

        if action_type == "mark_read":
            if not notification.unread:
                continue
            if not apply_actions:
                result.actions_taken.append("dry-run:mark_read")
                continue
            try:
                gateway.mark_thread_read(notification.thread_id)
                notification.unread = False
                result.actions_taken.append("mark_read")
            except Exception as error:
                result.errors.append(f"mark_read failed for {notification.thread_id}: {error}")

        elif action_type == "dismiss":
            if record is not None and record.dismissed:
                continue
            if not apply_actions:
                result.actions_taken.append("dry-run:dismiss")
                continue
            if dismiss_gateway is None:
                result.errors.append(f"dismiss action for {notification.thread_id}: no dismiss_gateway provided.")
                continue
            try:
                dismiss_gateway.dismiss_thread(notification.thread_id)
                if record is not None:
                    record.dismissed = True
                result.actions_taken.append("dismiss")
            except Exception as error:
                result.errors.append(f"dismiss failed for {notification.thread_id}: {error}")

        else:
            result.errors.append(f"Unsupported action '{action.action_type}'.")

    return result
