# Usage

Corvix is run with Docker Compose only for local runtime and end-to-end testing.

## Start the stack

Create config and secrets:

```bash
cp config/corvix.example.yaml config/corvix.yaml
cp secrets/github_token.txt.example secrets/github_token.txt
cp secrets/postgres_password.txt.example secrets/postgres_password.txt
cp secrets/database_url.txt.example secrets/database_url.txt
```

Fill in these files before starting services:

- `secrets/github_token.txt` - GitHub PAT with notifications access
- `secrets/postgres_password.txt` - PostgreSQL password
- `secrets/database_url.txt` - SQLAlchemy PostgreSQL URL matching the password

Start all services:

```bash
docker compose up --build
```

Open `http://localhost:8000`.

## Core configuration

Configure one or more GitHub accounts in `config/corvix.yaml`:

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

Single-account setups are valid by keeping a single account entry.

### Enrichment

Enable enrichment before rule evaluation:

```yaml
enrichment:
  enabled: true
  github_latest_comment:
    enabled: true
  github_pr_state:
    enabled: true
```

Example context-based suppression rule:

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

### Notifications dispatch

Notification event detection and delivery targets are configured under `notifications`:

```yaml
notifications:
  enabled: true
  detect:
    include_read: false
    min_score: 0.0
  browser_tab:
    enabled: true
    max_per_cycle: 5
    cooldown_seconds: 10
  web_push:
    enabled: false
    vapid_public_key_env: CORVIX_VAPID_PUBLIC_KEY
    vapid_private_key_env: CORVIX_VAPID_PRIVATE_KEY
    subject: ""
```

## Web API

- `GET /api/health`
- `GET /api/themes`
- `GET /api/dashboards`
- `GET /dashboards/{dashboard_name}`
- `GET /api/snapshot?dashboard=<name>`
- `GET /api/notifications/{account_id}/{thread_id}/rule-snippets?dashboard=<name>`
- `POST /api/notifications/{account_id}/{thread_id}/dismiss`
- `POST /api/notifications/{thread_id}/dismiss`
- `POST /api/notifications/{account_id}/{thread_id}/mark-read`
- `POST /api/notifications/{thread_id}/mark-read`
