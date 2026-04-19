# Quickstart

## Prerequisites

- A GitHub Personal Access Token (PAT) with `notifications` scope
- Docker and Docker Compose

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
- See [Dashboards](https://github.com/renefritze/corvix#dashboards) for the built-in dashboard descriptions
- Use `docker compose logs -f web` and `docker compose logs -f poller` when troubleshooting
