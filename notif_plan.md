# Notification Delivery Plan (Browser + Extensible Targets)

## Status

| Phase | Status |
|-------|--------|
| Phase 1 — Foundation + Browser Tab | **Complete** |
| Phase 2 — Web Push | Pending |
| Phase 3 — Additional Targets (webhook, Slack, …) | Pending |

### Phase 1 — What was implemented

#### Backend

- `src/corvix/notifications/` package:
  - `models.py` — `NotificationEvent`, `DeliveryResult`, `DispatchResult`
  - `detector.py` — `detect_new_unread_events()`: compares snapshots, emits events for brand-new or read→unread transitions; respects excluded/dismissed/min_score
  - `dispatcher.py` — `NotificationDispatcher`: fan-out with per-target error isolation
  - `dedupe.py` — `dedupe_events()` / `make_seen_set()` for idempotency helpers
  - `targets/base.py` — `NotificationTarget` protocol (runtime-checkable)
- `src/corvix/config.py` — `NotificationsConfig`, `BrowserTabTargetConfig`, `WebPushTargetConfig`, `NotificationsDetectConfig` dataclasses + YAML parser
- `src/corvix/services.py` — `run_poll_cycle()` now loads previous snapshot, detects events, and dispatches to `notification_targets` list; `PollingSummary` carries `dispatch: DispatchResult | None`
- `src/corvix/web/app.py` — `/api/snapshot` response includes `notifications_config` (enabled flag + browser_tab settings)
- `config/corvix.example.yaml` — `notifications:` section with all fields documented

#### Frontend

- `frontend/src/types.ts` — `BrowserTabNotificationsConfig`, `NotificationsConfig` types; `SnapshotPayload.notifications_config`
- `frontend/src/hooks/useBrowserNotifications.ts` — permission management, localStorage-backed seen-set, burst cap, cooldown, click-to-open
- `frontend/src/components/Toolbar.tsx` — `NotifButton` sub-component (off/on/denied/unsupported states)
- `frontend/src/app.tsx` — hook wired in, props forwarded to Toolbar
- `frontend/src/styles/app.css` — `.notif-btn`, `.notif-active`, `.notif-denied` styles

#### Tests

- `tests/unit/test_notifications.py` — 22 tests: detector (11), dispatcher (6), dedupe (5) — all pass

---

## Goals

1. Send notifications when **new GitHub notifications** arrive.
2. Support:
   - **A. In-app/browser-tab notifications** (tab open)
   - **B. True web push notifications** (tab closed/background)
3. Add a clean abstraction so we can later add non-browser targets/APIs (Slack, webhook, email, etc.) without rewiring poll logic.

---

## Current State (from repo)

- Backend poll pipeline runs in `run_poll_cycle()` and persists snapshots to cache:
  - `src/corvix/services.py`
  - `src/corvix/storage.py`
- Web UI polls `/api/snapshot` every 15s:
  - `frontend/src/hooks/useSnapshot.ts`
- No service worker, push subscription endpoints, or notification delivery abstraction exists today.

---

## Architecture Overview

## 1) Core Notification Event Abstraction (shared foundation)

Create a domain event and dispatcher layer in backend:

- New package: `src/corvix/notifications/`
  - `models.py`
    - `NotificationEvent` (canonical event payload for a newly-detected item)
    - fields: `event_id`, `thread_id`, `repository`, `reason`, `subject_title`, `web_url`, `updated_at`, `score`, `unread`
  - `detector.py`
    - `detect_new_unread_events(previous_records, current_records) -> list[NotificationEvent]`
  - `targets/base.py`
    - `NotificationTarget` protocol:
      - `name`
      - `is_enabled(config) -> bool`
      - `deliver(events, context) -> DeliveryResult`
  - `dispatcher.py`
    - `NotificationDispatcher` fan-out to enabled targets
    - per-target error isolation and structured results
  - `dedupe.py`
    - dedupe key helpers (event-level + target-level idempotency)

### Why this abstraction

- Polling and event detection happen once.
- Delivery channels become plugins/targets.
- Adding non-browser APIs is additive, not invasive.

---

## 2) Newness Detection Strategy (backend)

Implement detection in poll cycle by comparing previous snapshot and current results.

### Algorithm (default)

- Load previous records before save.
- Build set/map by `thread_id`.
- A record is "new for alerting" if:
  - exists in current
  - `unread == true`
  - and either:
    - `thread_id` not present previously, or
    - present previously but transitioned `read -> unread` (rare but valid)
- Optional suppression:
  - ignore excluded/dismissed records
  - optional minimum score threshold

### Integration point

- In `run_poll_cycle()`:
  1. fetch + score + rules + actions
  2. compute `events = detect_new_unread_events(previous, current)`
  3. persist snapshot
  4. dispatch events to configured targets

This keeps notification delivery tied to source-of-truth ingest and avoids UI-only false positives.

---

## 3) Target A — Browser Tab Notifications (open dashboard)

### UX scope

- Only works when dashboard tab is open.
- Fastest to deliver with lowest infra complexity.

### Frontend changes

- Add hook: `frontend/src/hooks/useBrowserNotifications.ts`
  - handles permission state
  - tracks seen `thread_id`s (in-memory + localStorage)
  - computes newly-arrived unread items from snapshot refreshes
  - emits `new Notification(...)` with dedupe + cooldown
- Wire into `frontend/src/app.tsx` after snapshot updates.
- Add controls in `frontend/src/components/Toolbar.tsx`:
  - enable/disable toggle
  - permission status + prompt button
- Add simple preferences storage:
  - keys like:
    - `corvix.notifications.browser.enabled`
    - `corvix.notifications.browser.lastSeen`

### Behavior defaults

- Permission requested only from explicit user action.
- Batch burst control: max N notifications per refresh cycle.
- Notification click opens `web_url` (or app fallback URL).

---

## 4) Target B — Web Push Notifications (tab closed/background)

### Backend requirements

- Push subscription APIs:
  - `POST /api/push/subscribe`
  - `POST /api/push/unsubscribe`
  - `GET /api/push/public-key`
- Store subscriptions in DB (Postgres preferred).
- New target implementation:
  - `src/corvix/notifications/targets/web_push.py`
  - Uses VAPID keys + Web Push library.
- Delivery fan-out:
  - one event can be sent to many subscriptions
  - remove/disable dead subscriptions on 404/410 from push service.

### Frontend requirements

- Add service worker:
  - `frontend/public/sw.js` (or project-equivalent static output path)
- Register SW in `frontend/src/main.tsx`.
- Add subscription manager hook:
  - `frontend/src/hooks/usePushSubscription.ts`
  - requests permission, subscribes via `PushManager`, posts subscription to backend.
- Handle `push` + `notificationclick` events in SW.

### Security/infra

- HTTPS required outside localhost.
- VAPID keypair in secrets/config.
- CSRF/auth policy for subscription endpoints (at minimum same-origin + token/cookie checks if auth exists).

---

## 5) Config Model Updates

Extend config with a `notifications` section (in `config.py` and example YAML`):

```yaml
notifications:
  enabled: true
  detect:
    include_read: false
    min_score: 0
  targets:
    browser_tab:
      enabled: true
      max_per_cycle: 5
      cooldown_seconds: 10
    web_push:
      enabled: false
      vapid_public_key_env: CORVIX_VAPID_PUBLIC_KEY
      vapid_private_key_env: CORVIX_VAPID_PRIVATE_KEY
      subject: "mailto:ops@example.com"
```

This preserves separation between event detection and target delivery.

---

## 6) Data Model / Persistence for Push (Postgres)

Add tables (migration):

- `push_subscriptions`
  - `id`
  - `user_id` (nullable if single-user mode)
  - `endpoint` (unique)
  - `p256dh`
  - `auth`
  - `user_agent`
  - `created_at`
  - `last_seen_at`
  - `disabled_at`

Optional (recommended for idempotency/observability):

- `notification_deliveries`
  - `event_id`
  - `target`
  - `subscription_id` (nullable)
  - `status` (sent/failed/skipped)
  - `error`
  - timestamps

---

## 7) Non-Browser Extensibility Plan

After abstraction lands, add new channels by implementing `NotificationTarget` only.

Examples:

- `targets/webhook.py` (POST JSON payload to configured URLs)
- `targets/slack.py` (chat.postMessage or webhook)
- `targets/email.py` (SMTP/transactional API)

Common capabilities in dispatcher:

- retries with backoff (channel-specific)
- per-target rate limiting
- template rendering from shared event payload

No changes needed in poll orchestration beyond target registration/config.

---

## 8) Rollout Plan (phased)

### Phase 1 — Foundation + Browser Tab (recommended first)

1. Add notification event models/detector/dispatcher.
2. Integrate detection + dispatch call into poll cycle.
3. Implement browser-tab frontend notification hook + toolbar controls.
4. Add config flags and default-off/on behavior per preference.

Deliverable: open-tab desktop notifications work reliably.

### Phase 2 — Web Push

1. Add VAPID config + key handling.
2. Add subscription endpoints + DB persistence.
3. Add service worker + frontend subscribe flow.
4. Implement web_push target + dead subscription cleanup.

Deliverable: notifications arrive with tab closed.

### Phase 3 — Additional Targets

1. Implement webhook target first (lowest complexity).
2. Add at-least-once/idempotency tracking table.
3. Add Slack/email as needed.

---

## 9) Testing Strategy

### Unit tests

- detector edge cases:
  - brand-new unread
  - read->unread transition
  - excluded/dismissed behavior
- dispatcher:
  - multi-target fan-out
  - one target failure does not block others
- config parsing/validation for notifications block

### Integration tests

- `run_poll_cycle()` emits expected event count on changed snapshot.
- push subscription endpoint CRUD + validation.
- web push target failure handling (404/410 disables subscription).

### Frontend tests

- browser notification hook:
  - permission denied/default/granted flows
  - dedupe and cooldown behavior
- service worker push event handling (if test harness supports)

### Manual E2E

- Docker compose stack up.
- Trigger synthetic new GH notification.
- Verify:
  - tab-open notification appears
  - push notification appears after tab closes (phase 2)

---

## 10) Operational Considerations

- Avoid notification spam:
  - per-cycle cap
  - cooldown
  - optional reason filters (`mention`, `review_requested`)
- Add metrics/logging:
  - events detected per poll
  - deliveries attempted/sent/failed per target
- Add admin visibility endpoint (optional):
  - last dispatch summary and recent errors

---

## Suggested File-Level Implementation Map

### Backend files

- `src/corvix/services.py` — detect + dispatch integration
- `src/corvix/config.py` — + notifications config dataclasses
- `src/corvix/notifications/__init__.py` — new package
- `src/corvix/notifications/models.py` — `NotificationEvent`, `DeliveryResult`
- `src/corvix/notifications/detector.py` — `detect_new_unread_events()`
- `src/corvix/notifications/dispatcher.py` — `NotificationDispatcher`
- `src/corvix/notifications/dedupe.py` — dedupe key helpers
- `src/corvix/notifications/targets/__init__.py`
- `src/corvix/notifications/targets/base.py` — `NotificationTarget` protocol
- `src/corvix/notifications/targets/web_push.py` — phase 2
- `src/corvix/notifications/targets/webhook.py` — phase 3
- `src/corvix/web/app.py` — + push subscription endpoints (phase 2)
- DB migration files for push subscription tables (phase 2)

### Frontend files

- `frontend/src/hooks/useBrowserNotifications.ts` — new (phase 1)
- `frontend/src/hooks/usePushSubscription.ts` — new (phase 2)
- `frontend/src/components/Toolbar.tsx` — notification controls
- `frontend/src/app.tsx` — hook wiring
- `frontend/src/main.tsx` — SW registration (phase 2)
- `frontend/public/sw.js` — new (phase 2)

---

## Acceptance Criteria

### Phase 1

- With dashboard open and permission granted, new unread notifications produce desktop notifications exactly once per thread (subject to cooldown/cap).
- No duplicate spam across refresh cycles.
- Feature can be toggled off from UI.

### Phase 2

- With subscription active and tab closed, new unread notifications are delivered via web push.
- Invalid subscriptions are automatically disabled.
- Delivery errors are logged and surfaced in metrics/summary.

### Phase 3

- At least one non-browser target can be added by implementing only `NotificationTarget` + config, with no changes to poll orchestration.
