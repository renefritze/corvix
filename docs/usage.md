# Usage

```{toctree}
---
hidden: true
maxdepth: 1
---
examples/basic
```

## Configuration

Create a local config file first:

```bash
cp config/corvix.example.yaml config/corvix.yaml
```

Set your GitHub token (or provide `GITHUB_TOKEN_FILE`):

```bash
export GITHUB_TOKEN=ghp_your_token
```

## CLI

Run one poll cycle (dry-run actions by default):

```bash
uv run corvix --config config/corvix.yaml poll
```

Run the watch loop:

```bash
uv run corvix --config config/corvix.yaml watch
```

Render cached dashboards in the terminal:

```bash
uv run corvix --config config/corvix.yaml dashboard
```

Serve the web UI:

```bash
uv run corvix --config config/corvix.yaml serve --reload
```

Import JSON cache records into PostgreSQL:

```bash
uv run corvix --config config/corvix.yaml migrate-cache --user-id <uuid>
```

## Docker Compose (local end-to-end)

For local end-to-end testing, use Docker Compose:

```bash
docker compose up --build
```

This starts:

- `web` on `http://localhost:8000`
- `poller` running `corvix watch`
- `db` (PostgreSQL 16)

## Web API

- `GET /api/health`
- `GET /api/themes`
- `GET /api/dashboards`
- `GET /api/snapshot?dashboard=<name>`
- `POST /api/notifications/{thread_id}/dismiss`
