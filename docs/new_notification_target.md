# Implementing a New Notification Target

This guide explains how to add a new delivery channel to Corvix's notification
system — for example Slack, a webhook, email, or SMS.

The system is designed so that adding a channel requires:

1. One new Python file implementing `NotificationTarget`.
2. A config dataclass + YAML parser addition (optional but recommended).
3. Wiring the target into `run_poll_cycle` call-sites.
4. Tests.

Nothing in the poll loop, storage, or detector needs to change.

---

## How the system works

```text
GitHub API
   │
   ▼
run_poll_cycle()          ← corvix/services.py
   │
   ├─ score + evaluate rules
   ├─ load previous snapshot
   ├─ save current snapshot
   │
   └─ detect_new_unread_events()   ← corvix/notifications/detector.py
          │
          ▼
      NotificationDispatcher.dispatch(events)   ← corvix/notifications/dispatcher.py
          │
          ├─ target_1.deliver(events)
          ├─ target_2.deliver(events)
          └─ target_N.deliver(events)   ← YOUR TARGET GOES HERE
```

Each `NotificationEvent` in the batch represents one newly-arrived unread
notification.  The dispatcher calls every registered target independently;
an exception in one target never blocks the others.

---

## The protocol

```python
# corvix/notifications/targets/base.py

@runtime_checkable
class NotificationTarget(Protocol):
    @property
    def name(self) -> str: ...

    def deliver(
        self,
        events: list[NotificationEvent],
    ) -> DeliveryResult: ...
```

`NotificationTarget` is a **structural protocol** (PEP 544).  You do not need
to import or inherit from it — any class with a matching `name` property and
`deliver` method satisfies it automatically.

---

## Step 1 — Create the target file

Place it in `src/corvix/notifications/targets/`:

```text
src/corvix/notifications/targets/
    base.py          ← protocol definition (do not edit)
    web_push.py      ← phase 2 placeholder
    slack.py         ← your new file
```

### Minimal working example (Slack incoming webhook)

```python
# src/corvix/notifications/targets/slack.py
"""Slack incoming-webhook notification target."""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass

from corvix.notifications.models import DeliveryResult, NotificationEvent

logger = logging.getLogger(__name__)


@dataclass
class SlackTarget:
    """Posts a Slack message for each new GitHub notification.

    Parameters
    ----------
    webhook_url:
        Slack incoming webhook URL.
    enabled:
        Set to False to silently skip delivery.
    """

    webhook_url: str
    enabled: bool = True

    @property
    def name(self) -> str:
        return "slack"

    def deliver(self, events: list[NotificationEvent]) -> DeliveryResult:
        if not self.enabled:
            return DeliveryResult(
                target=self.name,
                events_attempted=len(events),
                events_delivered=0,
            )

        errors: list[str] = []
        delivered = 0

        for event in events:
            text = (
                f"*{event.subject_title}*\n"
                f"Repo: `{event.repository}` · Reason: `{event.reason}`"
                + (f"\n<{event.web_url}|Open>") if event.web_url else ""
            )
            payload = json.dumps({"text": text}).encode()
            try:
                req = urllib.request.Request(
                    self.webhook_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5):
                    pass
                delivered += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Slack delivery failed for %s: %s", event.thread_id, exc)
                errors.append(f"{event.thread_id}: {exc}")

        return DeliveryResult(
            target=self.name,
            events_attempted=len(events),
            events_delivered=delivered,
            errors=errors,
        )
```

### Key rules for `deliver`

| Rule | Reason |
|------|--------|
| Always return `DeliveryResult` — even on total failure | Dispatcher accumulates results; a missing return breaks aggregation |
| Never raise from `deliver` | Dispatcher catches exceptions but logs them as unexpected; prefer returning errors in `DeliveryResult.errors` |
| Set `events_attempted = len(events)` | Required for accurate metrics in `DispatchResult.total_delivered` |
| Handle partial failure per-event | Increment `delivered` only for events that actually got through |

---

## Step 2 — Add config (recommended)

Add a dataclass to `src/corvix/config.py` next to the existing target configs:

```python
@dataclass(slots=True)
class SlackTargetConfig:
    """Config for the Slack notification target."""

    enabled: bool = False
    webhook_url_env: str = "CORVIX_SLACK_WEBHOOK_URL"
```

Add it to `NotificationsConfig`:

```python
@dataclass(slots=True)
class NotificationsConfig:
    enabled: bool = True
    detect: NotificationsDetectConfig = field(default_factory=NotificationsDetectConfig)
    browser_tab: BrowserTabTargetConfig = field(default_factory=BrowserTabTargetConfig)
    web_push: WebPushTargetConfig = field(default_factory=WebPushTargetConfig)
    slack: SlackTargetConfig = field(default_factory=SlackTargetConfig)   # ← add
```

Add a parser at the bottom of `config.py` inside `_parse_notifications`:

```python
slack_raw = _ensure_map(notif.get("slack", {}), "notifications.slack")
# ... inside the NotificationsConfig(...) constructor:
slack=SlackTargetConfig(
    enabled=bool(slack_raw.get("enabled", False)),
    webhook_url_env=str(slack_raw.get("webhook_url_env", "CORVIX_SLACK_WEBHOOK_URL")),
),
```

Add to `config/corvix.example.yaml`:

```yaml
notifications:
  slack:
    enabled: false
    webhook_url_env: CORVIX_SLACK_WEBHOOK_URL
```

---

## Step 3 — Wire the target into the poll loop

Targets are passed as a list to `run_poll_cycle` via the
`notification_targets` parameter.  The natural place to build that list is
wherever your entry point constructs the poll cycle — typically the CLI
command or the poller service.

### CLI example (`src/corvix/cli.py`)

```python
from corvix.notifications.targets.slack import SlackTarget
from corvix.env import get_env_value

def _build_targets(config: AppConfig) -> list:
    targets = []
    slack_cfg = config.notifications.slack
    if slack_cfg.enabled:
        webhook_url = get_env_value(slack_cfg.webhook_url_env)
        if webhook_url:
            targets.append(SlackTarget(webhook_url=webhook_url))
    return targets

# Inside the watch/poll command:
targets = _build_targets(config)
run_poll_cycle(
    config=config,
    client=client,
    cache=cache,
    apply_actions=apply_actions,
    notification_targets=targets,
)
```

`run_poll_cycle` only calls `NotificationDispatcher.dispatch` when
`config.notifications.enabled` is `True` **and** the `notification_targets`
list is non-empty, so a disabled or unconfigured target costs nothing.

---

## Step 4 — Write tests

Use the same pattern as `tests/unit/test_notifications.py`.  You only need to
test your target's `deliver` method in isolation.

```python
# tests/unit/test_target_slack.py
from unittest.mock import MagicMock, patch
from datetime import UTC, datetime

from corvix.notifications.models import NotificationEvent
from corvix.notifications.targets.slack import SlackTarget


def _event(thread_id: str = "1") -> NotificationEvent:
    return NotificationEvent(
        event_id=thread_id,
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="Something important",
        subject_type="PullRequest",
        web_url="https://github.com/org/repo/pull/1",
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        score=20.0,
        unread=True,
    )


def test_delivers_successfully():
    target = SlackTarget(webhook_url="https://hooks.slack.com/fake")
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        result = target.deliver([_event("1"), _event("2")])
    assert result.events_delivered == 2
    assert result.errors == []


def test_disabled_target_skips_delivery():
    target = SlackTarget(webhook_url="https://hooks.slack.com/fake", enabled=False)
    result = target.deliver([_event()])
    assert result.events_delivered == 0
    assert result.errors == []


def test_http_error_recorded_not_raised():
    target = SlackTarget(webhook_url="https://hooks.slack.com/fake")
    with patch("urllib.request.urlopen", side_effect=OSError("network down")):
        result = target.deliver([_event()])
    assert result.events_delivered == 0
    assert len(result.errors) == 1
    assert result.success is False
```

Run with:

```bash
uv run pytest tests/unit/test_target_slack.py -v
```

---

## Reference: `NotificationEvent` fields

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` | Same as `thread_id`. Stable deduplication key. |
| `thread_id` | `str` | GitHub notification thread ID. |
| `repository` | `str` | Full repo name, e.g. `"org/repo"`. |
| `reason` | `str` | GitHub notification reason: `mention`, `review_requested`, `assign`, etc. |
| `subject_title` | `str` | PR/Issue/commit title. |
| `subject_type` | `str` | `"PullRequest"`, `"Issue"`, `"Commit"`, etc. |
| `web_url` | `str \| None` | Direct link to the PR/Issue. May be `None` for some subject types. |
| `updated_at` | `datetime` | When the notification was last updated (timezone-aware UTC). |
| `score` | `float` | Corvix relevance score (higher = more important). |
| `unread` | `bool` | Always `True` for events produced by the detector. |

---

## Reference: `DeliveryResult` fields

| Field | Type | Description |
|-------|------|-------------|
| `target` | `str` | Must match `self.name`. |
| `events_attempted` | `int` | Always `len(events)`. |
| `events_delivered` | `int` | Count of events successfully sent. |
| `errors` | `list[str]` | Per-event error strings. Empty list = full success. |
| `success` (property) | `bool` | `True` when `errors` is empty. |

---

## Checklist

- [ ] `src/corvix/notifications/targets/<name>.py` created
- [ ] `name` property returns a short, unique string
- [ ] `deliver` always returns `DeliveryResult`, never raises
- [ ] Config dataclass added to `config.py` (if config-driven)
- [ ] `_parse_notifications` updated and YAML example updated
- [ ] Target constructed and passed to `run_poll_cycle` in entry point
- [ ] Unit tests cover: happy path, disabled state, partial/total failure
- [ ] `uv run pytest tests/unit/` passes
- [ ] `uv run ty check src/corvix/` passes
