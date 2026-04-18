# corvix

[![image](https://github.com/renefritze/corvix/workflows/pytest/badge.svg)](https://github.com/renefritze/corvix/actions)

Github notifications dashboards

## Installation and Development

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management. To get started:

1. Install uv.

2. Install the package with development dependencies:

    ```bash
    uv sync
    ```

3. Run tests:

    ```bash
    uv run pytest
    ```

4. Run linting:

    ```bash
    uv run ruff check .
    ```

5. Build frontend assets (required before running tests locally):

    ```bash
    make frontend-build
    ```

6. Run native frontend tests:

    ```bash
    npm --prefix frontend run test -- --run
    ```

7. Check frontend coverage (enforced at >=80% lines/functions/branches/statements):

    ```bash
    npm --prefix frontend run test:coverage
    ```

## Frontend Build Contract

- Frontend source-of-truth lives in `frontend/` (`frontend/src/**`).
- Canonical build command: `make frontend-build` (runs `npm ci && npm run build` in `frontend/`).
- Build output is generated into `src/corvix/web/static/assets/`.
- Generated bundles are not committed to git.
- `src/corvix/web/static/index.html` is source-maintained and references `/assets/app.js` and `/assets/index.css`.
- Native frontend tests run with Vitest (`npm --prefix frontend run test -- --run`).
- Coverage is enforced at >=80% lines/functions/branches/statements (`npm --prefix frontend run test:coverage`).

## Features

- Local GitHub notification ingestion with configurable polling (`poll` and `watch`)
- Strict separation between ingestion (`corvix.ingestion`), automation/actions (`corvix.rules`, `corvix.actions`, `corvix.scoring`), and presentation (`corvix.presentation`, `corvix.web`)
- Multiple dashboards with configurable sorting and grouping (see [Dashboards](#dashboards))
- Global and per-repository rules for filtering and auto mark-read
- Optional enrichment pipeline with context-based rule matching (e.g., latest-comment suppressions)
- Custom scoring model for ranking notifications
- YAML configuration with example committed and local override ignored by git
- Multi-account GitHub support with one merged dashboard/feed
- Litestar website dashboard with periodic auto-refresh
- Docker Compose setup for `web`, `poller`, and `db`

## Multi-Account Config

Corvix can ingest notifications from multiple GitHub accounts and merge them into one dashboard.

```yaml
github:
  accounts:
    - id: work
      label: Work
      token_env: GITHUB_TOKEN_WORK
      api_base_url: https://api.github.com
    - id: personal
      label: Personal
      token_env: GITHUB_TOKEN_PERSONAL
      api_base_url: https://api.github.com
```

Set each token env var (or `<VAR>_FILE`):

```bash
export GITHUB_TOKEN_WORK=ghp_work_token
export GITHUB_TOKEN_PERSONAL=ghp_personal_token
```

Rows remain account-scoped internally, but the UI stays merged (no account-separated dashboards).

## Quickstart (Docker-only)

> Full details: [docs/quickstart.md](docs/quickstart.md)

1. Create local config from the committed example:

    ```bash
    cp config/corvix.example.yaml config/corvix.yaml
    ```

## Docker Compose

1. Copy config and Docker secret templates:

    ```bash
    cp config/corvix.example.yaml config/corvix.yaml
    cp secrets/github_token.txt.example secrets/github_token.txt
    cp secrets/postgres_password.txt.example secrets/postgres_password.txt
    cp secrets/database_url.txt.example secrets/database_url.txt
    ```

2. Edit secret files:

- `secrets/github_token.txt`: your GitHub PAT.
- `secrets/postgres_password.txt`: strong DB password.
- `secrets/database_url.txt`: full SQLAlchemy/PostgreSQL URL (must match DB credentials).

1. Start services:

    ```bash
    docker compose up --build
    ```

2. Open `http://localhost:8000`.

Notes:

- Local runtime/testing is Docker Compose only.
- Frontend assets are built as part of the Docker image build (`docker compose up --build`).
- Frontend source changes require rebuilding images (`docker compose up --build`) to refresh generated bundles.
- `poller` runs the notification watch loop and updates the shared `/data/notifications.json`.
- `db` uses `POSTGRES_PASSWORD_FILE`; `web` and `poller` use `GITHUB_TOKEN_FILE` and `DATABASE_URL_FILE`.

## Dashboards

Corvix ships with two built-in dashboards, selectable via the dropdown in the web UI.

**Overview** (default) — situational awareness

- Groups notifications by **reason** (mention, review requested, etc.)
- Sorts by **updated_at**, newest first
- Includes read items
- Shows up to 200 notifications, no reason filter
- Best for: seeing what's been happening across all your repos

**Triage** — action-oriented

- Groups notifications by **repository**
- Sorts by **score** (descending), so the highest-priority items surface first
- Unread only
- Shows up to 100 notifications, filtered to mention/review_requested/assign reasons
- Best for: deciding what to deal with right now

The first dashboard listed in your config is loaded by default. You can add, remove, or reorder dashboards under the `dashboards:` key in `config/corvix.yaml`.

## After generating your project

- setup branch protection+automerge in [github project settings](https://github.com/renefritze/corvix/settings/branches)
- request install for the codecov.io app in [github project settings](https://github.com/renefritze/corvix/settings/installations)
- configure codecov.io in [codecov.io settings](https://codecov.io/gh/renefritze/corvix/settings)
- add the `CODECOV_TOKEN` secret in [github project settings](https://github.com/renefritze/corvix/settings/secrets/actions)
