# AGENTS.md

This file provides guidance to contributors and agents working with code in this repository.

## Commands

This project uses `uv` for dependency management (Python 3.13+).

```bash
uv sync                                              # install dependencies
uv run pytest                                        # run all tests
uv run pytest tests/test_services.py::test_foo       # run a single test
uv run ruff check .                                  # lint
uv run ruff format .                                 # format
uv run ty check src/corvix/                          # type check
make frontend-build                                  # build frontend assets
make gen-types                                       # regenerate OpenAPI + TS API types
npm --prefix frontend run test -- --run              # run native frontend tests
npm --prefix frontend run test:coverage              # frontend coverage (>=80%)

docker compose up                                    # full stack (web + poller + db)
docker compose up web                                # web only
docker compose logs -f web                           # tail service logs
docker compose down                                  # stop and remove containers
```

## Local testing

**Always use the Docker Compose setup for local end-to-end testing.** Do not run `corvix-web` or `corvix watch` directly on the host. Use:

```bash
docker compose up --build
```

This starts four services. `web` and `poller` share no filesystem state with each
other — all persistence is in PostgreSQL:

- `web` — Litestar dashboard on `http://localhost:8000`
- `poller` — `corvix watch`, polling GitHub and persisting to PostgreSQL
- `db` — PostgreSQL 16
- `migrate` — one-shot job that applies Alembic migrations before `web`/`poller` start

**Prerequisites** before `docker compose up`:

1. `config/corvix.yaml` must exist (copy from `config/corvix.example.yaml`)
2. `.env` must exist at the repository root containing one or more GitHub token
   environment variables. For a single account setup use `GITHUB_TOKEN`; for
   multiple accounts ensure each variable name matches the corresponding
   `token_env` entry in `config/corvix.yaml`.
   Example:

   ```bash
   GITHUB_TOKEN=ghp_...yourtoken...
   GITHUB_TOKEN_ACCOUNT2=ghp_...anothertoken...
   ```

3. `secrets/postgres_password.txt` and `secrets/database_url.txt` must exist

The Docker Compose setup loads `.env` into the containers so Corvix can resolve
each account token by its configured `token_env` name.

Frontend assets are generated during image build and are not committed to git. Rebuild images (`docker compose up --build`) after frontend changes.

The SPA in `frontend/` is **Svelte 5 (runes) + Vite + TypeScript + Tailwind CSS 4**, with light/dark theming (system preference default, toggle persisted in `localStorage["corvix.theme"]`). State lives in `.svelte.ts` store classes under `frontend/src/lib/` (instantiated in `App.svelte`/`Dashboard.svelte`, injected via `setContext` — see `lib/context.ts`); presentational `.svelte` components live under `frontend/src/components/`. `npm run build` runs `gen:types`, then `svelte-check` (the type gate, replacing `tsc --noEmit`), then `vite build` (library mode) which emits exactly `app.js` + `index.css` into `src/corvix/web/static/assets/`. Unit tests are Vitest + Testing Library Svelte with an ≥80% coverage gate; the executable parity spec is `tests/e2e/test_dashboard_ui.py`, whose DOM selectors (aria-labels, `data-testid`s, `data-label`s) are a hard contract — edit that test and the code in the same commit for any intentional change.

## Architecture

Corvix fetches GitHub notifications, scores and filters them via configurable rules, persists them to PostgreSQL, and presents them via CLI (Rich) or web UI (Litestar).

**Data flow**: `GitHub API → ingestion.py → scoring.py + rules.py → actions.py → storage.py → dashboarding.py → presentation.py / web/app.py`

### Core modules

- **`domain.py`** — `Notification` (raw API data) and `NotificationRecord` (scored + rule-evaluated wrapper). The central data structures passed through all layers.
- **`config/`** — YAML-based configuration parsed into dataclasses, split across `config/app.py` (root `AppConfig`, `PollingConfig`, `StateConfig`, `DatabaseConfig`, `load_config`), `config/github.py` (`GitHubConfig`), `config/scoring.py` (`ScoringConfig`), `config/rules.py` (`RuleSet`), `config/dashboards.py` (`DashboardSpec`), and `config/notifications.py` (`NotificationsConfig`). `config/__init__.py` re-exports all of these so `from corvix.config import X` keeps working.
- **`ingestion.py`** — `GitHubNotificationsClient`: paginated GitHub API fetch, `mark_thread_read()`, and `dismiss_thread()`.
- **`scoring.py`** — Pure function `score_notification()`. Weights for unread bonus, reason, repo, subject type, title keywords, and age decay.
- **`rules.py`** — Pure function `evaluate_rules()`. Matches notifications against `MatchCriteria` (repo, reason, subject_type, title regex, unread, score, age). Rules can exclude from dashboards or trigger actions.
- **`actions.py`** — `execute_actions()` runs rule-specified actions (`mark_read`, `dismiss`). Uses `MarkReadGateway`/`DismissGateway` protocols for testability. Default mode is dry-run; pass `apply_actions=True` to actually modify GitHub state.
- **`storage.py`** — `StorageBackend` protocol and `PostgresStorage`, the PostgreSQL-backed persistence shared by the poller and web service.
- **`services.py`** — Orchestration: `run_poll_cycle()` wires fetch→enrichment→score→rules→actions→persist and optional notification dispatch; `run_watch_loop()` adds periodic scheduling; `render_cached_dashboards()` loads persisted records from storage and renders without polling.
- **`notifications/`** — Event detection and dispatch pipeline (`detector.py`, `dispatcher.py`, `models.py`, `targets/base.py`) for newly-unread notifications.
- **`pipeline/`** — Unified `PipelineEngine` plus provider protocols and the built-in providers under `pipeline/providers/` (`github_thread_subject`, `github_web_url` for field completion; `github_latest_comment`, `github_pr_state` for context enrichment).
- **`dashboarding.py`** — `build_dashboard_data()` filters, sorts, groups, and limits records per `DashboardSpec`. Used by both CLI and web.
- **`presentation.py`** — Rich-based terminal rendering of dashboard groups.
- **`web/app.py`** — Litestar app. Routes include `GET /`, `GET /dashboards/{dashboard_name}`, `GET /api/health`, `GET /api/themes`, `GET /api/dashboards`, `GET /api/snapshot`, `GET /api/events` (Server-Sent Events), and dismiss/mark-read POST endpoints. The UI subscribes to `/api/v1/events` and receives a pushed `snapshot` event only when the data changes; it falls back to 15s interval polling when SSE is unavailable. The server-side poll interval is configurable via `CORVIX_SSE_POLL_INTERVAL_SECONDS` (default 3s).
- **`web/schemas.py`** — Typed response dataclasses (`SnapshotResponse`, `RuleSnippetsResponse`, …) that are the single source of truth for the JSON API shapes. Route handlers are annotated to return them, so Litestar auto-generates an OpenAPI document. `scripts/export_openapi.py` renders that document to `frontend/openapi.json` (**committed**; drift-checked in CI). `openapi-typescript` then generates `frontend/src/api-types.gen.ts` from it during `npm run build` — that file is generated, not committed (gitignored like the JS/CSS bundles). `frontend/src/types.ts` re-exports those types. Run `make gen-types` after changing the schemas and commit the updated `openapi.json`. `tests/unit/test_api_contract.py` verifies both the OpenAPI sync and that live responses conform to the schemas.
- **`cli.py`** — Click CLI: `init-config`, `poll`, `watch`, `dashboard`, `serve`, `poller-health`.

### Docker Compose

Four services, defined in `docker-compose.yml`. Persistence is PostgreSQL-only —
there is no shared file or volume between `web` and `poller`:

- **`db`**: PostgreSQL 16, backed by the `corvix_db` volume
- **`migrate`**: one-shot job that runs `alembic upgrade head`; `web` and `poller` wait for it to complete
- **`poller`**: runs `corvix watch`, continuously polling GitHub and writing records to PostgreSQL
- **`web`**: serves the Litestar dashboard on port 8000, reading from PostgreSQL

### Configuration

Copy `config/corvix.example.yaml` to `config/corvix.yaml` (gitignored). Configure one or more GitHub accounts under `github.accounts`; each account reads its token from the configured `token_env` (or `token_env_FILE`). Run `corvix init-config` to generate a starter file.
