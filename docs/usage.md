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

Configure one or more GitHub accounts under `github.accounts`:

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

Set token env vars (or `*_FILE` variants) for each configured account:

```bash
export GITHUB_TOKEN_WORK=ghp_work_token
export GITHUB_TOKEN_PERSONAL=ghp_personal_token
```

Single-account setups are still valid by configuring one account (for example `id: primary`). Corvix merges notifications from all configured accounts into one dashboard/feed.

Legacy top-level fallback keys remain accepted for compatibility:

```bash
export GITHUB_TOKEN=ghp_your_token
```

Enable comment enrichment if you want context-based suppression rules:

```yaml
enrichment:
  enabled: true
  github_latest_comment:
    enabled: true
```

Example context-based rule:

```yaml
rules:
  global:
    - name: mute-codecov-comments
      match:
        reason_in: ["comment"]
        context:
          - path: github.latest_comment.author.login
            op: equals
            value: codecov[bot]
      actions:
        - type: mark_read
      exclude_from_dashboards: true
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
uv run corvix --config config/corvix.yaml migrate-cache --user-id YOUR_UUID
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
- `GET /dashboards/<name>`
- `GET /api/snapshot?dashboard=<name>`
- `POST /api/notifications/{account_id}/{thread_id}/dismiss`
- `POST /api/notifications/{account_id}/{thread_id}/mark-read`

Compatibility routes for default account are also available:

- `POST /api/notifications/{thread_id}/dismiss`
- `POST /api/notifications/{thread_id}/mark-read`
