"""Action execution for matched rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from corvix.config import RuleAction
from corvix.domain import Notification, NotificationRecord

if TYPE_CHECKING:
    pass


@runtime_checkable
class MarkReadGateway(Protocol):
    """Gateway interface for marking notification threads as read."""

    def mark_thread_read(self, thread_id: str) -> None:
        """Mark a thread as read."""


@runtime_checkable
class DismissGateway(Protocol):
    """Gateway interface for dismissing (deleting) notification threads."""

    def dismiss_thread(self, thread_id: str) -> None:
        """Dismiss a thread from the inbox permanently."""


@dataclass(slots=True)
class ActionExecutionResult:
    """Summary of actions taken on one notification."""

    actions_taken: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ActionExecutionContext:
    """Bundles all execution dependencies for :func:`execute_actions`.

    Attributes:
        gateway: Must implement :class:`MarkReadGateway`.
        apply_actions: If ``False`` actions are recorded as dry-run only.
        dismiss_gateway: Must implement :class:`DismissGateway`; required for dismiss actions.
        record: The associated :class:`~corvix.domain.NotificationRecord` used for dismiss state tracking.
    """

    gateway: MarkReadGateway
    apply_actions: bool = False
    dismiss_gateway: DismissGateway | None = None
    record: NotificationRecord | None = None


# ---------------------------------------------------------------------------
# Internal action handlers (Strategy Pattern)
# ---------------------------------------------------------------------------


class _ActionHandler(Protocol):
    """Strategy interface for a single action type."""

    def execute(
        self,
        notification: Notification,
        result: ActionExecutionResult,
    ) -> None:
        """Execute the action, mutating *result* in place."""


class _MarkReadHandler:
    """Handles the ``mark_read`` action."""

    def __init__(self, gateway: MarkReadGateway, apply_actions: bool) -> None:
        self._gateway = gateway
        self._apply_actions = apply_actions

    def execute(self, notification: Notification, result: ActionExecutionResult) -> None:
        if not notification.unread:
            return
        if not self._apply_actions:
            result.actions_taken.append("dry-run:mark_read")
            return
        try:
            self._gateway.mark_thread_read(notification.thread_id)
            notification.unread = False
            result.actions_taken.append("mark_read")
        except Exception as error:
            result.errors.append(f"mark_read failed for {notification.thread_id}: {error}")


class _DismissHandler:
    """Handles the ``dismiss`` action."""

    def __init__(
        self,
        gateway: DismissGateway | None,
        apply_actions: bool,
        record: NotificationRecord | None,
    ) -> None:
        self._gateway = gateway
        self._apply_actions = apply_actions
        self._record = record

    def execute(self, notification: Notification, result: ActionExecutionResult) -> None:
        if self._record is not None and self._record.dismissed:
            return
        if not self._apply_actions:
            result.actions_taken.append("dry-run:dismiss")
            return
        if self._gateway is None:
            result.errors.append(f"dismiss action for {notification.thread_id}: no dismiss_gateway provided.")
            return
        try:
            self._gateway.dismiss_thread(notification.thread_id)
            if self._record is not None:
                self._record.dismissed = True
            result.actions_taken.append("dismiss")
        except Exception as error:
            result.errors.append(f"dismiss failed for {notification.thread_id}: {error}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute_actions(
    notification: Notification,
    actions: list[RuleAction],
    context: ActionExecutionContext,
) -> ActionExecutionResult:
    """Execute configured actions against a notification.

    Args:
        notification: The notification to act on.
        actions: The list of rule actions to execute.
        context: Execution context carrying gateways and flags.
    """
    handlers: dict[str, _MarkReadHandler | _DismissHandler] = {
        "mark_read": _MarkReadHandler(context.gateway, context.apply_actions),
        "dismiss": _DismissHandler(context.dismiss_gateway, context.apply_actions, context.record),
    }

    result = ActionExecutionResult()
    seen_actions: set[str] = set()
    for action in actions:
        action_type = action.action_type.strip().lower()
        if not action_type or action_type in seen_actions:
            continue
        seen_actions.add(action_type)

        handler = handlers.get(action_type)
        if handler is None:
            result.errors.append(f"Unsupported action '{action.action_type}'.")
            continue

        handler.execute(notification, result)

    return result
