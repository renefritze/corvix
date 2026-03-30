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

## Features

- Local GitHub notification ingestion with configurable polling (`poll` and `watch`)
- Strict separation between ingestion (`corvix.ingestion`), automation/actions (`corvix.rules`, `corvix.actions`, `corvix.scoring`), and presentation (`corvix.presentation`, `corvix.web`)
- Multiple dashboards with configurable sorting and grouping
- Global and per-repository rules for filtering and auto mark-read
- Custom scoring model for ranking notifications
- YAML configuration with example committed and local override ignored by git
- Litestar website dashboard with periodic auto-refresh
- Docker Compose setup for `web`, `poller`, and `db`

## Quickstart

1. Create local config from the committed example:

    ```bash
    cp config/corvix.example.yaml config/corvix.yaml
    ```

2. Set your GitHub token:

    ```bash
    export GITHUB_TOKEN=ghp_your_token
    ```

3. Run one poll cycle (dry-run actions by default):

    ```bash
    uv run corvix --config config/corvix.yaml poll
    ```

4. Render terminal dashboards from local cache:

    ```bash
    uv run corvix --config config/corvix.yaml dashboard
    ```

5. Run website dashboard locally (with auto-reload enabled):

    ```bash
    uv run corvix --config config/corvix.yaml serve --reload
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

3. Start services:

    ```bash
    docker compose up --build
    ```

4. Open `http://localhost:8000`.

Notes:

- `web` runs Litestar via `uvicorn --reload` and watches `/app/src` for code changes.
- `poller` runs the notification watch loop and updates the shared `/data/notifications.json`.
- `db` uses `POSTGRES_PASSWORD_FILE`; `web` and `poller` use `GITHUB_TOKEN_FILE` and `DATABASE_URL_FILE`.

## After generating your project

- setup branch protection+automerge in [github project settings](https://github.com/renefritze/corvix/settings/branches)
- request install for the codecov.io app in [github project settings](https://github.com/renefritze/corvix/settings/installations)
- configure codecov.io in [codecov.io settings](https://codecov.io/gh/renefritze/corvix/settings)
- add the `CODECOV_TOKEN` secret in [github project settings](https://github.com/renefritze/corvix/settings/secrets/actions)
