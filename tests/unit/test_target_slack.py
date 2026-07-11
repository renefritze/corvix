"""Unit tests for the built-in Slack notification target."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from corvix.notifications.models import NotificationEvent
from corvix.notifications.targets.base import NotificationTarget
from corvix.notifications.targets.slack import SlackTarget

_WEBHOOK = "https://hooks.slack.com/services/fake"


def _event(
    thread_id: str = "1", *, account_id: str = "primary", web_url: str | None = "https://gh/pull/1"
) -> NotificationEvent:
    return NotificationEvent(
        event_id=f"{account_id}:{thread_id}",
        account_id=account_id,
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="Something important",
        subject_type="PullRequest",
        web_url=web_url,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        score=20.0,
        unread=True,
    )


def test_slack_target_satisfies_protocol() -> None:
    assert isinstance(SlackTarget(webhook_url=_WEBHOOK), NotificationTarget)


def test_delivers_each_event() -> None:
    target = SlackTarget(webhook_url=_WEBHOOK)
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = target.deliver([_event("1"), _event("2")])

    assert result.events_attempted == 2
    assert result.events_delivered == 2
    assert result.errors == []
    assert result.success is True
    assert mock_open.call_count == 2
    # Payload is JSON with a Slack "text" field carrying the subject + link.
    request = mock_open.call_args_list[0].args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert "Something important" in payload["text"]
    assert "org/repo" in payload["text"]
    assert "https://gh/pull/1" in payload["text"]


def test_disabled_target_is_noop() -> None:
    target = SlackTarget(webhook_url=_WEBHOOK, enabled=False)
    with patch("urllib.request.urlopen") as mock_open:
        result = target.deliver([_event()])

    assert result.events_delivered == 0
    assert result.errors == []
    mock_open.assert_not_called()


def test_http_error_recorded_not_raised() -> None:
    target = SlackTarget(webhook_url=_WEBHOOK)
    with patch("urllib.request.urlopen", side_effect=OSError("network down")):
        result = target.deliver([_event("1"), _event("2")])

    assert result.events_delivered == 0
    assert len(result.errors) == 2
    assert result.success is False


def test_partial_failure_counts_only_delivered() -> None:
    target = SlackTarget(webhook_url=_WEBHOOK)
    calls = {"n": 0}

    def _urlopen(*_args: object, **_kwargs: object) -> MagicMock:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("boom")
        ctx = MagicMock()
        ctx.__enter__ = lambda s: s
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    with patch("urllib.request.urlopen", side_effect=_urlopen):
        result = target.deliver([_event("1"), _event("2")])

    assert result.events_delivered == 1
    assert len(result.errors) == 1


def test_message_includes_non_primary_account() -> None:
    target = SlackTarget(webhook_url=_WEBHOOK)
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        target.deliver([_event("1", account_id="work")])

    payload = json.loads(mock_open.call_args.args[0].data.decode("utf-8"))
    assert "work" in payload["text"]
