"""Action execution for matched rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from corvix.config import RuleAction
from corvix.domain import Notification


class MarkReadGateway(Protocol):
    """Gateway interface for marking notification threads as read."""

    def mark_thread_read(self, thread_id: str) -> None:
        """Mark a thread as read."""


@dataclass(slots=True)
class ActionExecutionResult:
    """Summary of actions taken on one notification."""

    actions_taken: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def execute_actions(
    notification: Notification,
    actions: list[RuleAction],
    gateway: MarkReadGateway,
    apply_actions: bool,
) -> ActionExecutionResult:
    """Execute configured actions against a notification."""
    result = ActionExecutionResult()
    seen_actions: set[str] = set()
    for action in actions:
        action_type = action.action_type.strip().lower()
        if not action_type or action_type in seen_actions:
            continue
        seen_actions.add(action_type)
        if action_type != "mark_read":
            result.errors.append(f"Unsupported action '{action.action_type}'.")
            continue
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
    return result
