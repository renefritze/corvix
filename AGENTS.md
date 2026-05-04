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

This starts three services sharing a `corvix_state` volume:

- `web` — Litestar dashboard on `http://localhost:8000`
- `poller` — `corvix watch` updating the JSON cache
- `db` — PostgreSQL 16

**Prerequisites** before `docker compose up`:

1. `config/corvix.yaml` must exist (copy from `config/corvix.example.yaml`)
2. `secrets/github_token.txt` must contain a GitHub personal access token
3. `secrets/postgres_password.txt` and `secrets/database_url.txt` must exist

If you have multiple GitHub tokens, instead create a `.env` file at the repository root
containing one or more token environment variables (do not commit this file). Example:

```bash
GITHUB_TOKEN_ACCOUNT1=ghp_...yourtoken...
GITHUB_TOKEN_ACCOUNT2=ghp_...anothertoken...
```

Ensure the `token_env` entries in your `config/corvix.yaml` match these variable names
(for example `GITHUB_TOKEN_ACCOUNT1`). The Docker Compose setup will load `.env` into
the containers so Corvix can resolve each account's token by name.

Frontend assets are generated during image build and are not committed to git. Rebuild images (`docker compose up --build`) after frontend changes.

## Architecture

Corvix fetches GitHub notifications, scores and filters them via configurable rules, caches them locally as JSON, and presents them via CLI (Rich) or web UI (Litestar).

**Data flow**: `GitHub API → ingestion.py → scoring.py + rules.py → actions.py → storage.py → dashboarding.py → presentation.py / web/app.py`

### Core modules

- **`domain.py`** — `Notification` (raw API data) and `NotificationRecord` (scored + rule-evaluated wrapper). The central data structures passed through all layers.
- **`config.py`** — YAML-based configuration parsed into dataclasses. `AppConfig` is the root; it holds `GitHubConfig`, `PollingConfig`, `ScoringConfig`, `RuleSet`, `DashboardSpec[]`, `StateConfig`, and `NotificationsConfig`.
- **`ingestion.py`** — `GitHubNotificationsClient`: paginated GitHub API fetch, `mark_thread_read()`, and `dismiss_thread()`.
- **`scoring.py`** — Pure function `score_notification()`. Weights for unread bonus, reason, repo, subject type, title keywords, and age decay.
- **`rules.py`** — Pure function `evaluate_rules()`. Matches notifications against `MatchCriteria` (repo, reason, subject_type, title regex, unread, score, age). Rules can exclude from dashboards or trigger actions.
- **`actions.py`** — `execute_actions()` runs rule-specified actions (`mark_read`, `dismiss`). Uses `MarkReadGateway`/`DismissGateway` protocols for testability. Default mode is dry-run; pass `apply_actions=True` to actually modify GitHub state.
- **`storage.py`** — `NotificationCache`: reads/writes `list[NotificationRecord]` as JSON to `~/.cache/corvix/notifications.json`.
- **`services.py`** — Orchestration: `run_poll_cycle()` wires fetch→enrichment→score→rules→actions→persist and optional notification dispatch; `run_watch_loop()` adds periodic scheduling; `render_cached_dashboards()` loads cache and renders without polling.
- **`notifications/`** — Event detection and dispatch pipeline (`detector.py`, `dispatcher.py`, `models.py`, `targets/base.py`) for newly-unread notifications.
- **`enrichment/`** — Enrichment engine and providers (`github_latest_comment`, `github_pr_state`) for context-aware rule matching.
- **`dashboarding.py`** — `build_dashboard_data()` filters, sorts, groups, and limits records per `DashboardSpec`. Used by both CLI and web.
- **`presentation.py`** — Rich-based terminal rendering of dashboard groups.
- **`web/app.py`** — Litestar app. Routes include `GET /`, `GET /dashboards/{dashboard_name}`, `GET /api/health`, `GET /api/themes`, `GET /api/dashboards`, `GET /api/snapshot`, and dismiss/mark-read POST endpoints. UI auto-refreshes every 15s.
- **`cli.py`** — Click CLI: `init-config`, `poll`, `watch`, `dashboard`, `serve`, `migrate-cache`.

### Docker Compose

Three services share a `corvix_state` volume (`/data/notifications.json`):

- **`poller`**: runs `corvix watch`, continuously updating the JSON cache
- **`web`**: serves the Litestar dashboard on port 8000, reading from the shared cache
- **`db`**: PostgreSQL 16 (provisioned for future use; current persistence is JSON-only)

### Configuration

Copy `config/corvix.example.yaml` to `config/corvix.yaml` (gitignored). Configure one or more GitHub accounts under `github.accounts`; each account reads its token from the configured `token_env` (or `token_env_FILE`). Run `corvix init-config` to generate a starter file.
