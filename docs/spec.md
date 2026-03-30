# Corvix — Design Specification

> Living document. Sections 1–9 reflect the current `mvp` implementation. Sections 10–14 specify the planned re-architecture.

---

## 1. Purpose

Corvix fetches a user's GitHub notifications, scores and filters them with configurable rules, caches the results locally, and presents them through a terminal CLI or a web dashboard.

**Current state**: single-user, single-machine, JSON file cache.

**Target state**: multi-user server with PostgreSQL persistence, two-way notification management, theming, and browser push notifications.

---

## 2. Data Model

### 2.1 `Notification` (raw)

Normalized view of one GitHub notification thread. Constructed via `Notification.from_api_payload()`.

| Field | Type | Source |
|---|---|---|
| `thread_id` | `str` | `id` |
| `repository` | `str` | `repository.full_name` |
| `reason` | `str` | `reason` (e.g. `mention`, `review_requested`, `assign`, `author`) |
| `subject_title` | `str` | `subject.title` |
| `subject_type` | `str` | `subject.type` (e.g. `PullRequest`, `Issue`) |
| `unread` | `bool` | `unread` |
| `updated_at` | `datetime` (UTC) | `updated_at` (ISO 8601) |
| `thread_url` | `str \| None` | `url` |

### 2.2 `NotificationRecord` (processed)

Wraps a `Notification` with the output of scoring and rule evaluation. This is what gets persisted and rendered.

| Field | Type | Description |
|---|---|---|
| `notification` | `Notification` | Raw notification data |
| `score` | `float` | Computed priority score |
| `excluded` | `bool` | True if any matched rule has `exclude_from_dashboards: true` |
| `matched_rules` | `list[str]` | Names of rules that matched |
| `actions_taken` | `list[str]` | Actions executed (e.g. `mark_read`, `dry-run:mark_read`) |

**Planned addition** (section 11): `dismissed: bool` field.

### 2.3 Cache file schema

JSON file at the path configured in `state.cache_file`:

```json
{
  "generated_at": "<ISO 8601 UTC timestamp>",
  "notifications": [ <NotificationRecord.to_dict()>, ... ]
}
```

---

## 3. Configuration

YAML file, default path `corvix.yaml`. Generate a starter with `corvix init-config`.

### 3.1 `github`

```yaml
github:
  token_env: GITHUB_TOKEN        # env var holding the PAT
  api_base_url: https://api.github.com
```

### 3.2 `polling`

```yaml
polling:
  interval_seconds: 300          # watch loop sleep between cycles
  per_page: 50                   # GitHub API page size (max 50)
  max_pages: 5                   # page cap per cycle
  all: false                     # include already-read notifications
  participating: false           # only notifications the user is participating in
```

### 3.3 `state`

```yaml
state:
  cache_file: ~/.cache/corvix/notifications.json
```

### 3.4 `scoring`

```yaml
scoring:
  unread_bonus: 15.0             # flat bonus for unread
  age_decay_per_hour: 0.25       # subtracted per hour of age
  reason_weights:                # keyed by GitHub reason string
    mention: 50
    review_requested: 40
    assign: 30
    author: 10
  repository_weights:            # keyed by org/repo
    your-org/critical-repo: 25
  subject_type_weights:          # keyed by subject.type
    PullRequest: 10
  title_keyword_weights:         # substring match (case-insensitive)
    security: 20
    urgent: 15
```

### 3.5 `rules`

Rules are evaluated in order: global rules first, then per-repository rules for the notification's repo. All matching rules contribute — there is no short-circuit.

```yaml
rules:
  global:
    - name: mute-bot-noise
      match:
        title_regex: ".*\\[bot\\].*"
      actions:
        - type: mark_read
      exclude_from_dashboards: true
  per_repository:
    your-org/infra:
      - name: mute-chore-prs
        match:
          title_contains_any: ["chore", "deps"]
        actions:
          - type: mark_read
        exclude_from_dashboards: true
```

#### `MatchCriteria` fields

All fields are optional. Unset fields are treated as "match anything".

| Field | Type | Semantics |
|---|---|---|
| `repository_in` | `list[str]` | Exact match against `repository` |
| `reason_in` | `list[str]` | Exact match against `reason` |
| `subject_type_in` | `list[str]` | Exact match against `subject_type` |
| `title_contains_any` | `list[str]` | Case-insensitive substring OR |
| `title_regex` | `str` | `re.search` against title |
| `unread` | `bool` | Exact match |
| `min_score` | `float` | Score must be ≥ this value |
| `max_age_hours` | `float` | Notification must be newer than this |

All active criteria must match (AND logic). `title_contains_any` is OR within itself.

#### `RuleAction` types

Currently only one action type is implemented:

| `type` | Behaviour |
|---|---|
| `mark_read` | Calls `PATCH /notifications/threads/{id}`. Skips if already read. No-op in dry-run mode (records `dry-run:mark_read` instead). |

### 3.6 `dashboards`

```yaml
dashboards:
  - name: triage
    group_by: repository          # repository | reason | subject_type | none
    sort_by: score                # score | updated_at | repository | reason | subject_type | title
    descending: true
    include_read: false
    max_items: 100
    match:                        # optional MatchCriteria sub-filter
      reason_in: ["mention", "review_requested"]
```

Excluded records are never shown in any dashboard regardless of `match`.

---

## 4. Pipeline

One poll cycle executes the following steps in sequence, per notification:

```text
fetch_notifications()
  └─ for each Notification:
       score  = score_notification(notification, scoring_config)
       eval   = evaluate_rules(notification, score, rule_set)
       result = execute_actions(notification, eval.actions, client, apply_actions)
       → NotificationRecord(notification, score, eval.excluded,
                            eval.matched_rules, result.actions_taken)
  └─ cache.save(records)
```

### 4.1 Scoring formula

```text
score = unread_bonus (if unread)
      + reason_weights[reason]
      + repository_weights[repository]
      + subject_type_weights[subject_type]
      + sum(weight for keyword in title_keyword_weights if keyword in title.lower())
      - age_hours * age_decay_per_hour
```

`age_hours` is computed relative to an injectable `now` (defaults to `datetime.now(UTC)`). The score can be negative.

### 4.2 Rule evaluation

`evaluate_rules()` iterates `global_rules + per_repository[notification.repository]`. For each rule whose `MatchCriteria` passes, it accumulates: matched rule name, its actions, and sets `excluded = True` if `exclude_from_dashboards` is set. All matching rules contribute; there is no early exit.

### 4.3 Action execution

`execute_actions()` deduplicates actions by type before executing. The only current action is `mark_read`, which:

- Is skipped if `notification.unread` is already `False`.
- In dry-run mode: records `dry-run:mark_read` but does not call the API.
- In apply mode: calls `client.mark_thread_read(thread_id)` and mutates `notification.unread = False`.

The `MarkReadGateway` protocol decouples `execute_actions` from `GitHubNotificationsClient` for testing.

---

## 5. Storage

`NotificationCache` reads and writes a single JSON file. The full snapshot (all polled records, including excluded ones) is replaced atomically on each save. There is no append or merge logic.

---

## 6. CLI

Entry point: `corvix` (`corvix.cli:main`). All subcommands accept `--config PATH` (default `corvix.yaml`).

| Command | Description |
|---|---|
| `init-config [PATH]` | Write starter YAML. `--force` to overwrite. |
| `poll` | One fetch → process → cache cycle. `--apply-actions` / `--dry-run` (default dry-run). Prints fetched/excluded/actions counts. |
| `watch` | Runs `poll` in a loop, sleeping `interval_seconds` between runs. `--iterations N` to cap. |
| `dashboard [--name NAME]` | Renders dashboards from cache using Rich tables. Does not poll. |
| `serve` | Starts Litestar web server. `--host`, `--port`, `--reload`. Sets env vars then delegates to `uvicorn`. |

---

## 7. Web API

Framework: Litestar. Served via uvicorn. Config loaded on every request from the path in `CORVIX_CONFIG` env var.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Single-page HTML dashboard app (embedded in source). |
| `GET` | `/api/health` | Returns `{"status": "ok"}`. |
| `GET` | `/api/dashboards` | Returns `{"dashboard_names": [...]}`. |
| `GET` | `/api/snapshot?dashboard=<name>` | Loads cache, runs `build_dashboard_data`, returns `DashboardData` as JSON plus `dashboard_names`. |

The SPA auto-refreshes every 15 seconds, populates a dashboard selector from `/api/snapshot`, and renders grouped tables. Columns 6, 8, 9 (Title, Rules, Actions) are hidden below 900 px.

### `/api/snapshot` response shape

```json
{
  "name": "<dashboard name>",
  "generated_at": "<ISO 8601 or null>",
  "total_items": 42,
  "groups": [
    {
      "name": "<group key>",
      "items": [
        {
          "thread_id": "...",
          "repository": "org/repo",
          "reason": "mention",
          "subject_type": "PullRequest",
          "subject_title": "...",
          "unread": true,
          "updated_at": "...",
          "score": 63.5,
          "matched_rules": [],
          "actions_taken": []
        }
      ]
    }
  ],
  "dashboard_names": ["triage", "overview"]
}
```

---

## 8. Deployment

### Docker Compose services

| Service | Image | Role |
|---|---|---|
| `db` | `postgres:16-alpine` | PostgreSQL — provisioned but not used by current code. |
| `poller` | local build | Runs `corvix watch --dry-run` continuously; writes to shared `corvix_state` volume. |
| `web` | local build | Runs `uvicorn corvix.web.app:app --reload`; reads from shared `corvix_state` volume. |

Shared volume `corvix_state` is mounted at `/data`. The poller writes `notifications.json` there; the web service reads it. Both services mount `./src` and `./config` for live reload during development.

### Environment variables

| Variable | Used by | Description |
|---|---|---|
| `GITHUB_TOKEN` | poller | GitHub PAT (or whichever env var is named in `token_env`). |
| `CORVIX_CONFIG` | both | Path to YAML config file inside the container. |
| `DATABASE_URL` | both | Set but unused by current code (future persistence). |
| `CORVIX_WEB_HOST` | web | Bind host for uvicorn (default `0.0.0.0`). |
| `CORVIX_WEB_PORT` | web | Bind port for uvicorn (default `8000`). |
| `CORVIX_WEB_RELOAD` | web | Enable uvicorn reload (`true`/`false`). |

---

## 9. Current gaps

- **PostgreSQL** is provisioned in Docker Compose but never used. All persistence is JSON on disk.
- **`tools.py`** is empty — reserved for future use.
- **Action types**: Only `mark_read` is implemented. `execute_actions` logs an error for unknown types but continues.
- **Concurrency**: The poller and web service share a file with no locking. Relies on filesystem atomicity of `write_text` at typical polling intervals.
- **No link resolution**: `thread_url` stores the GitHub API URL, not the human-readable web URL.

---

## Planned Architecture

## 10. Multi-user support

### 10.1 Motivation

The current design binds to a single `GITHUB_TOKEN` from the environment. Supporting multiple GitHub users requires per-user token storage, user-scoped data, and authentication on the web layer.

### 10.2 Database schema

Activate the existing PostgreSQL container. Use `alembic` for migrations (`src/corvix/migrations/`).

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY,
    github_login    TEXT UNIQUE NOT NULL,
    github_token    TEXT NOT NULL,   -- encrypted with Fernet, key derived from session_secret
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notification_records (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id),
    thread_id       TEXT NOT NULL,
    repository      TEXT NOT NULL,
    reason          TEXT NOT NULL,
    subject_title   TEXT NOT NULL,
    subject_type    TEXT NOT NULL,
    unread          BOOLEAN NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL,
    thread_url      TEXT,
    score           FLOAT NOT NULL,
    excluded        BOOLEAN NOT NULL DEFAULT false,
    matched_rules   TEXT[] DEFAULT '{}',
    actions_taken   TEXT[] DEFAULT '{}',
    dismissed       BOOLEAN NOT NULL DEFAULT false,
    snapshot_at     TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id, thread_id)
);

CREATE TABLE user_preferences (
    user_id         UUID PRIMARY KEY REFERENCES users(id),
    theme           TEXT NOT NULL DEFAULT 'default',
    browser_notify  BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE push_subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id),
    endpoint        TEXT NOT NULL,
    p256dh_key      TEXT NOT NULL,
    auth_key        TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, endpoint)
);
```

Use `INSERT ... ON CONFLICT (user_id, thread_id) DO UPDATE` so each poll cycle upserts rather than replacing. This preserves the `dismissed` flag across poll cycles — the critical difference from the current full-snapshot-replace approach.

### 10.3 Storage abstraction

Introduce a `StorageBackend` protocol in `storage.py`:

```python
class StorageBackend(Protocol):
    def save_records(self, user_id: str, records: list[NotificationRecord], generated_at: datetime) -> None: ...
    def load_records(self, user_id: str) -> tuple[datetime | None, list[NotificationRecord]]: ...
    def dismiss_record(self, user_id: str, thread_id: str) -> None: ...
    def get_dismissed_thread_ids(self, user_id: str) -> list[str]: ...
```

`NotificationCache` continues to work for single-user CLI mode. A new `PostgresStorage` class implements the same protocol for multi-user mode. `services.py` accepts `StorageBackend` instead of `NotificationCache`.

### 10.4 New config sections

```yaml
auth:
  mode: single_user              # single_user | multi_user
  session_secret: "..."          # required in multi_user mode, signs session cookies

database:
  url_env: DATABASE_URL          # env var holding the PostgreSQL connection string
```

When `auth.mode` is `single_user` or absent, the system behaves as today: one token from env, JSON cache. When `multi_user`, tokens come from the `users` table and PostgreSQL is required.

**Separation of concerns**: the YAML config remains the *system* config (scoring weights, rules, dashboards). Per-user state (token, preferences, subscriptions) lives in the database.

### 10.5 Per-user polling

`services.py` gains `run_poll_cycle_for_user(config, client, storage, user_id, apply_actions)`. The watch loop iterates all registered users, instantiating a `GitHubNotificationsClient` per user with their decrypted token.

**Scalability note**: sequential polling is O(N users) per cycle. Acceptable for tens of users. For larger deployments, fan out to a task queue (`arq` + Redis). Not in initial scope.

### 10.6 Web authentication

Session-based auth using Litestar's session middleware with signed cookies.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | No | Create account with `github_login` + token. Validates token against `GET /user`. |
| `POST` | `/api/auth/login` | No | Validate token, create session. |
| `DELETE` | `/api/auth/logout` | Yes | Clear session. |

All existing `/api/*` endpoints become user-scoped: the session injects `user_id` into request state.

**Future enhancement**: GitHub OAuth App flow (redirect → authorize → callback). More complex but better UX. Not in initial scope — manual token entry is sufficient for multi-user MVP.

### 10.7 Token security

GitHub PATs stored in PostgreSQL must be encrypted at rest. Use `cryptography.fernet.Fernet` with a key derived from `auth.session_secret` via PBKDF2. Tokens are decrypted only at poll time and for on-demand API calls (dismiss). Never returned in API responses.

### 10.8 Migration path

Non-breaking, incremental:

1. Add `StorageBackend` protocol. Make `NotificationCache` conform.
2. Add `PostgresStorage`.
3. When `database.url_env` is set, use Postgres. Otherwise, fall back to JSON.
4. New CLI command `corvix migrate-cache` reads the JSON file and inserts records into PostgreSQL for the configured user.
5. Docker Compose already provisions PostgreSQL and passes `DATABASE_URL` — only the app needs to start using it.

### 10.9 Config re-reading

Currently `_load_runtime_config()` reads YAML from disk on every web request. In multi-user mode, cache the parsed `AppConfig` in Litestar application state on startup, reloaded via a file watcher or SIGHUP.

---

## 11. Two-way dismiss

### 11.1 GitHub API mapping

| Corvix action | GitHub API call | Effect |
|---|---|---|
| `mark_read` (existing) | `PATCH /notifications/threads/{id}` | Thread moves from unread to read |
| `dismiss` (new) | `DELETE /notifications/threads/{id}` | Thread is removed from the inbox entirely ("Done" in GitHub UI) |

`DELETE` is permanent — the notification cannot be un-dismissed on GitHub. The thread will not reappear in future poll results unless there is new activity on it.

### 11.2 Domain changes

Add `dismissed: bool = False` to `NotificationRecord`. Update `to_dict()` and `from_dict()` accordingly.

### 11.3 Ingestion changes

Add to `GitHubNotificationsClient`:

```python
def dismiss_thread(self, thread_id: str) -> None:
    url = self._build_url(f"/notifications/threads/{thread_id}", {})
    self._request_no_content(url, method="DELETE")
```

### 11.4 Action execution

Add a `DismissGateway` protocol alongside `MarkReadGateway`. Extend `execute_actions` to handle `action_type == "dismiss"`:

- Skip if already dismissed.
- In dry-run mode: record `dry-run:dismiss`.
- In apply mode: call `gateway.dismiss_thread(thread_id)`, set `dismissed = True`.

New rule action type:

```yaml
actions:
  - type: dismiss
```

### 11.5 Web endpoint

```text
POST /api/notifications/{thread_id}/dismiss
```

Requires auth. Resolves the user, calls `client.dismiss_thread(thread_id)`, marks `dismissed = True` in storage, returns `204`.

### 11.6 SPA changes

Add a dismiss button (e.g. `×`) per notification row. On click, `POST` to the dismiss endpoint. On success, remove the row from the DOM. Since `DELETE` on GitHub is permanent, show a brief undo grace period (delay the API call by ~3 seconds, show "Undo" toast) before committing.

---

## 12. Theming

### 12.1 Approach

The current SPA already uses CSS custom properties (`--bg`, `--ink`, `--surface`, `--accent`, `--line`, `--ok`, `--muted`). Theming is a JS-only operation: apply a preset by setting these variables on `document.documentElement.style`.

### 12.2 Theme presets

Defined as a JS object in the SPA:

```javascript
const THEMES = {
  default:    { bg: "#f2efe8", ink: "#181818", surface: "#fffdf8", accent: "#a13d2d", line: "#d7cdbf", ok: "#1e7a4f", muted: "#5f5a50" },
  dark:       { bg: "#1a1a2e", ink: "#e0e0e0", surface: "#16213e", accent: "#e94560", line: "#333355", ok: "#4ecca3", muted: "#8888aa" },
  solarized:  { bg: "#fdf6e3", ink: "#657b83", surface: "#eee8d5", accent: "#cb4b16", line: "#93a1a1", ok: "#859900", muted: "#93a1a1" },
};
```

### 12.3 Persistence

- **Single-user / no auth**: store selected theme name in `localStorage`.
- **Multi-user**: store in `user_preferences.theme` via `PUT /api/preferences/theme`. The SPA loads the preference on init.

### 12.4 API

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/themes` | No | Returns `{ themes: { name: { var: value, ... }, ... } }` |
| `PUT` | `/api/preferences/theme` | Yes | Body: `{ "theme": "dark" }`. Persists to DB. |

### 12.5 SPA theme picker

Add a theme dropdown next to the existing dashboard selector in the header. On change, apply the CSS variables immediately and persist the choice.

### 12.6 Why not separate CSS files

The SPA is an embedded string. CSS custom properties make theming a runtime JS operation with zero extra HTTP requests. This avoids the need to extract static assets or add a build step.

**Future consideration**: as more UI features land (dismiss buttons, push permission UI, login form), the embedded string will become unwieldy. Consider extracting to `src/corvix/web/static/` with Litestar's static file serving. This is not blocked by theming itself.

---

## 13. Browser notifications

### 13.1 Architecture

Three components:

1. **Service Worker** — registered by the SPA, receives push events, shows system notifications.
2. **Push subscription** — browser generates a subscription (endpoint + keys), SPA sends it to the server.
3. **Server-side push** — the poller detects new high-priority notifications and pushes to all of the user's subscriptions.

### 13.2 VAPID keys

Web Push requires a VAPID key pair. Generate once, store persistently:

```yaml
browser_notifications:
  enabled: true
  vapid_private_key_env: VAPID_PRIVATE_KEY
  vapid_public_key_env: VAPID_PUBLIC_KEY
```

Generate with `pywebpush` or `openssl`. The public key is served to the SPA; the private key is used server-side to sign push messages.

### 13.3 Service Worker

Served at `GET /sw.js` (new Litestar route, same embedded-string pattern):

```javascript
self.addEventListener('push', (event) => {
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icon.png',
      data: { url: data.url }
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url));
});
```

### 13.4 SPA subscription flow

On page load, if `browser_notify` is enabled for the user:

1. `navigator.serviceWorker.register('/sw.js')`
2. `Notification.requestPermission()`
3. `registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: <VAPID public key> })`
4. `POST /api/push/subscribe` with the subscription JSON.

### 13.5 Push trigger conditions

Configurable in YAML:

```yaml
browser_notifications:
  enabled: true
  min_score: 40.0                # only push notifications scoring above this
  reasons: ["mention", "review_requested"]  # only push for these reasons
  cooldown_minutes: 5            # suppress re-push for the same thread_id within this window
```

After each poll cycle, the poller compares new/updated records against the trigger conditions. For qualifying notifications, it sends a push to all of the user's subscriptions via `pywebpush`.

### 13.6 API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/push/vapid-key` | No | Returns the public VAPID key for the SPA. |
| `POST` | `/api/push/subscribe` | Yes | Save push subscription to DB. |
| `DELETE` | `/api/push/subscribe` | Yes | Remove push subscription. |

### 13.7 New module: `push.py`

Handles push delivery:

```python
def send_push(subscription_info: dict, payload: dict, vapid_private_key: str, vapid_claims: dict) -> None: ...
def notify_user(user_id: str, records: list[NotificationRecord], config: BrowserNotificationConfig) -> None: ...
```

Called from `run_poll_cycle_for_user` after records are saved.

### 13.8 Constraints

- Web Push requires HTTPS in production (service workers only register on secure origins or `localhost`).
- VAPID keys must be persistent across restarts.
- Subscription endpoints can expire or become invalid; `send_push` must handle 410 Gone by removing the subscription from the DB.

---

## 14. Implementation plan

### Dependency graph

```text
Phase A: Theming ──────────────────────────────── (independent)

Phase B: Database layer ─────┬─── Phase C: Two-way dismiss
                             │
                             ├─── Phase D: Multi-user auth
                             │
                             └─── Phase E: Browser notifications
                                    (also depends on Phase D)
```

### Recommended sequence

| Step | Phase | Status | Scope | Dependencies |
|---|---|---|---|---|
| 1 | A | ✅ Done | Theming: CSS variable presets, theme picker in SPA, `localStorage` persistence | None |
| 2 | B | ✅ Done | Database: schema, alembic, `StorageBackend` protocol, `PostgresStorage`, `migrate-cache` CLI command | None |
| 3 | C | ✅ Done | Two-way dismiss: `dismiss_thread()` API method, `dismiss` action type, `POST /api/notifications/{id}/dismiss`, SPA dismiss button | Step 2 (for `dismissed` column) |
| 4 | D | Pending | Multi-user auth: session middleware, register/login/logout endpoints, per-user polling, token encryption | Step 2 |
| 5 | A+ | Pending | Theming DB persistence: `PUT /api/preferences/theme`, load from `user_preferences` table | Steps 1 + 4 |
| 6 | E | Pending | Browser notifications: service worker, VAPID, push subscriptions, trigger logic in poller | Steps 2 + 4 |

Steps 1 and 2 can be done in parallel. Step 3 can be built and tested in single-user mode before step 4 lands.

### New dependencies

| Package | Purpose | Phase |
|---|---|---|
| `asyncpg` | Async PostgreSQL client for Litestar handlers | B |
| `psycopg[binary]` | Sync PostgreSQL client for CLI commands | B |
| `alembic` | Schema migrations | B |
| `cryptography` | Fernet encryption for stored tokens | D |
| `pywebpush` | Web Push delivery | E |

### Key risks

1. **Token storage**: encrypted PATs in PostgreSQL is a significant security responsibility. Compromise of `session_secret` + DB access exposes all tokens.
2. **SPA complexity**: the embedded HTML string approach will strain under theming controls, dismiss buttons, push permission UI, and login forms. Extract to `src/corvix/web/static/` early (during Phase A or B) to avoid compounding tech debt.
3. **Dismiss permanence**: `DELETE /notifications/threads/{id}` cannot be undone. Must implement a client-side undo grace period to prevent accidental dismissals.
4. **HTTPS requirement**: browser notifications require HTTPS in production. Local dev works on `localhost`, but any networked deployment needs TLS termination.
5. **Polling scalability**: sequential per-user polling is O(N). Fine for tens of users. Task queue needed beyond that.
