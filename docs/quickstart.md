# Quickstart

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for package management
- A GitHub Personal Access Token (PAT) with `notifications` scope

## Local setup

1. Clone the repository and install dependencies:

    ```bash
    git clone https://github.com/renefritze/corvix.git
    cd corvix
    uv sync
    ```

2. Create your local config from the committed example:

    ```bash
    cp config/corvix.example.yaml config/corvix.yaml
    ```

3. Set your GitHub token:

    ```bash
    export GITHUB_TOKEN=ghp_your_token
    ```

4. Run one poll cycle to fetch notifications:

    ```bash
    uv run corvix --config config/corvix.yaml poll
    ```

5. Open the web dashboard:

    ```bash
    uv run corvix --config config/corvix.yaml serve --reload
    ```

    Then visit `http://localhost:8000`.

## Docker Compose setup

1. Copy config and secret templates:

    ```bash
    cp config/corvix.example.yaml config/corvix.yaml
    cp secrets/github_token.txt.example secrets/github_token.txt
    cp secrets/postgres_password.txt.example secrets/postgres_password.txt
    cp secrets/database_url.txt.example secrets/database_url.txt
    ```

2. Fill in the secret files:

   - `secrets/github_token.txt` — your GitHub PAT
   - `secrets/postgres_password.txt` — a strong database password
   - `secrets/database_url.txt` — full SQLAlchemy PostgreSQL URL (must match the password above)

3. Start all services:

    ```bash
    docker compose up --build
    ```

4. Open `http://localhost:8000`.

## Next steps

- Tune rules and scoring in `config/corvix.yaml`
- See [Dashboards](../README.md#dashboards) for the built-in dashboard descriptions
- Run `uv run corvix --help` to explore all CLI commands
