# Corvix Test Plan

## Current State

- **197 tests passing** (`uv run pytest`, 2026-03-31)
- **Overall coverage: 94%** (from pytest-cov summary)
- **Phase 1 status:** complete
- **Phase 2 status:** complete
- **Phase 3 status:** in progress
- **e2e directory exists** but is still empty

### Progress Status (2026-03-31)

- [x] Phase 1.1 `ingestion.py` tests
- [x] Phase 1.2 `cli.py` tests
- [x] Phase 1.3 `config.py` validation tests
- [x] Phase 1.4 `domain.py` URL edge-case tests
- [x] Phase 1.5 `dashboarding.py` branch tests
- [x] Phase 1.6 `storage.py` `NotificationCache` error-path tests
- [x] Phase 1.7 `web/app.py` dismiss/config runtime tests
- [x] Phase 2.1 `PostgresStorage` integration tests
- [x] Phase 2.2 poll-to-render pipeline tests
- [x] Phase 2.3 web snapshot integration tests with populated data
- [x] Phase 2.4 CLI end-to-end integration tests expansion
- [x] Phase 3.1 Playwright setup
- [ ] Phase 3.2 Playwright e2e scenarios

### Coverage by Module

| Module | Stmts | Miss | Branch | Cover | Notes |
|---|---|---|---|---|---|
| `actions.py` | 51 | 0 | 20 | 99% | Near-complete |
| `cli.py` | 130 | 76 | 24 | **37%** | Most commands untested |
| `config.py` | 159 | 8 | 14 | 93% | Validation error paths missing |
| `dashboarding.py` | 91 | 2 | 28 | 97% | Two minor branches |
| `db.py` | 58 | 1 | 0 | 98% | Only `get_database_url` line |
| `domain.py` | 126 | 9 | 36 | 90% | `_derive_web_url` edge cases |
| `env.py` | 18 | 0 | 6 | 100% | Complete |
| `ingestion.py` | 54 | 35 | 10 | **30%** | Entirely untested (HTTP calls) |
| `presentation.py` | 40 | 0 | 8 | 98% | Near-complete |
| `rules.py` | 35 | 0 | 6 | 100% | Complete |
| `scoring.py` | 19 | 0 | 6 | 100% | Complete |
| `services.py` | 60 | 0 | 12 | 99% | Near-complete |
| `storage.py` | 87 | 35 | 20 | **58%** | `PostgresStorage` entirely untested |
| `web/app.py` | 88 | 18 | 10 | 81% | `dismiss_notification` flow, `run()` |

---

## Phase 1: Extend Unit Tests

Goal: raise overall coverage to ~95% by filling gaps in pure-logic and mockable modules.

### 1.1 `ingestion.py` (30% -> ~95%)

The `GitHubNotificationsClient` is currently 0% tested. All methods use `urllib.request` which can be mocked.

| # | Test | What it covers |
|---|---|---|
| 1 | `test_fetch_notifications_single_page` | Mock `_request_json` to return a list of valid payloads; assert `Notification` objects returned |
| 2 | `test_fetch_notifications_pagination` | Mock returns data on page 1, empty on page 2; assert loop terminates |
| 3 | `test_fetch_notifications_max_pages_limit` | Set `max_pages=1`, mock returns non-empty; assert only one page fetched |
| 4 | `test_fetch_page_non_list_raises` | Mock `_request_json` to return a dict; assert `ValueError` raised |
| 5 | `test_fetch_page_filters_non_dict_items` | Return `[{...}, "garbage"]`; assert only dict items become notifications |
| 6 | `test_mark_thread_read_calls_patch` | Mock `_request_no_content`; assert called with correct URL and `PATCH` method |
| 7 | `test_dismiss_thread_calls_delete` | Mock `_request_no_content`; assert called with correct URL and `DELETE` method |
| 8 | `test_build_url_with_query` | Assert URL construction with query params |
| 9 | `test_build_url_without_query` | Assert URL construction with empty query dict |
| 10 | `test_headers_contain_bearer_token` | Assert `Authorization: Bearer <token>` in headers |

**File:** `tests/unit/test_ingestion.py`

### 1.2 `cli.py` (37% -> ~85%)

CLI commands are testable via `click.testing.CliRunner`. Most need a config file + mocked dependencies.

| # | Test | What it covers |
|---|---|---|
| 1 | `test_init_config_force_overwrites` | Run `init-config --force` over existing file; assert overwritten |
| 2 | `test_init_config_existing_no_force_fails` | Run `init-config` when file exists; assert exit code != 0 |
| 3 | `test_poll_command_dry_run` | Provide config + mock client via monkeypatch; assert output shows fetched/excluded counts |
| 4 | `test_poll_command_missing_config` | Run `poll` with nonexistent config; assert `ClickException` |
| 5 | `test_poll_command_missing_token` | Config exists but no `GITHUB_TOKEN`; assert error message |
| 6 | `test_watch_command_iterations` | Run `watch --iterations 1` with mocked client; assert summary output |
| 7 | `test_dashboard_command_renders` | Seed cache file, run `dashboard`; assert output |
| 8 | `test_dashboard_command_no_cache` | Run `dashboard` with empty cache; assert "No dashboards rendered" |
| 9 | `test_serve_command_sets_env_vars` | Mock `run_web`, invoke `serve`; assert env vars set |
| 10 | `test_migrate_cache_command_no_db_url` | Run `migrate-cache` without `DATABASE_URL`; assert error |
| 11 | `test_migrate_cache_command_empty_cache` | Run with empty cache; assert "nothing to migrate" |
| 12 | `test_load_app_config_invalid_yaml` | Write invalid YAML; assert `ClickException` |
| 13 | `test_resolve_token_file_variant` | Set `GITHUB_TOKEN_FILE` pointing to a file with token; assert resolved |
| 14 | `test_config_path_from_context_missing` | Context without config_path; assert error |

**File:** `tests/unit/test_cli.py` (new) or extend `tests/integration/test_cli.py`

### 1.3 `config.py` (93% -> ~99%)

Missing lines are validation error paths in `_ensure_map`, `_ensure_list`, `_to_str_list`.

| # | Test | What it covers |
|---|---|---|
| 1 | `test_load_config_non_dict_top_level` | YAML content is a bare string; assert `ValueError` |
| 2 | `test_ensure_map_raises_for_non_dict` | Pass a list where a map is expected; assert `ValueError` |
| 3 | `test_ensure_list_raises_for_non_list` | Pass a dict where a list is expected; assert `ValueError` |
| 4 | `test_to_str_list_raises_for_non_list` | Pass a string where list expected; assert `ValueError` |

**File:** `tests/unit/test_config.py` (append)

### 1.4 `domain.py` (90% -> ~98%)

Missing coverage in `_derive_web_url` and `_map_subject_api_url_to_web` edge cases.

| # | Test | What it covers |
|---|---|---|
| 1 | `test_derive_web_url_issue` | Subject URL is `/repos/org/repo/issues/7`; assert `issues/7` in web_url |
| 2 | `test_derive_web_url_commit` | Subject URL is `/repos/org/repo/commits/abc`; assert `commit/abc` |
| 3 | `test_derive_web_url_release_tag` | Subject URL is `/repos/org/repo/releases/tags/v1.0`; assert `releases/tag/v1.0` |
| 4 | `test_derive_web_url_no_subject_url` | `subject.url` is `None`; assert falls back to repo html_url |
| 5 | `test_derive_web_url_mismatched_repo` | Subject URL repo differs from notification repo; assert returns `None` (fallback) |
| 6 | `test_derive_web_url_short_path` | Subject URL has < 4 segments; assert returns `None` |
| 7 | `test_derive_web_url_unknown_resource` | Subject URL is `/repos/org/repo/unknown/123`; assert returns `None` |
| 8 | `test_derive_web_url_no_html_url_falls_back_to_github` | No `html_url` in repository; assert `https://github.com/org/repo` used |
| 9 | `test_from_dict_missing_updated_at_raises` | Record dict without `updated_at`; assert `ValueError` |

**File:** `tests/unit/test_domain.py` (append)

### 1.5 `dashboarding.py` (97% -> 100%)

| # | Test | What it covers |
|---|---|---|
| 1 | `test_sort_by_title` | Sort records by title; assert correct ordering (line 142/145) |
| 2 | `test_group_by_unknown_key` | `group_by="invalid"`; assert all records land in "all" group (line 163) |

**File:** `tests/unit/test_dashboarding.py` (append)

### 1.6 `storage.py` - `NotificationCache` error paths (58% -> ~70% without Postgres)

| # | Test | What it covers |
|---|---|---|
| 1 | `test_load_invalid_format_not_dict` | Write `"hello"` to cache file; assert `ValueError` |
| 2 | `test_load_invalid_notifications_not_list` | Write `{"notifications": "bad"}`; assert `ValueError` |
| 3 | `test_load_generated_at_non_string_is_none` | Write `{"generated_at": 123, "notifications": []}`; assert `generated_at` is `None` |

**File:** `tests/unit/test_storage_cache.py` (append)

### 1.7 `web/app.py` (81% -> ~90%)

| # | Test | What it covers |
|---|---|---|
| 1 | `test_dismiss_success` | Mock `GitHubNotificationsClient.dismiss_thread` + token env; assert 204 |
| 2 | `test_dismiss_github_error_returns_502` | Mock `dismiss_thread` to raise; assert 502 |
| 3 | `test_dismiss_token_env_error_returns_500` | Token env var resolution raises `ValueError`; assert 500 |
| 4 | `test_load_runtime_config_invalid_yaml` | Config file contains invalid YAML; assert 500 |

**File:** `tests/integration/test_web_api.py` (append)

---

## Phase 2: Integration Tests

Goal: test cross-module flows with real (but local/mocked) dependencies.

### 2.1 `PostgresStorage` integration (`storage.py` 58% -> ~95%)

Requires a PostgreSQL instance. Use `pytest-postgresql` or `testcontainers-python` to spin up a temporary database.

**Prerequisites:**

- Add `testcontainers[postgres]` or `pytest-postgresql` to dev dependencies
- Create a fixture that starts a PostgreSQL container, runs Alembic migrations, yields a connection string

| # | Test | What it covers |
|---|---|---|
| 1 | `test_save_and_load_records` | Insert records, load them back; assert round-trip fidelity |
| 2 | `test_save_records_upsert_preserves_dismissed` | Insert record, dismiss it, re-save; assert `dismissed=True` preserved |
| 3 | `test_load_records_empty_returns_none_and_empty` | Load from empty table; assert `(None, [])` |
| 4 | `test_dismiss_record_updates_flag` | Save records, dismiss one; assert only target is dismissed |
| 5 | `test_get_dismissed_thread_ids` | Save mix of dismissed/active; assert correct IDs returned |
| 6 | `test_records_scoped_to_user` | Save records for two users; load for one; assert isolation |
| 7 | `test_ordering_by_snapshot_then_score` | Insert records with varying timestamps/scores; assert load order |

**File:** `tests/integration/test_storage_postgres.py`

**Mark:** `@pytest.mark.integration` (skip in CI without DB by default)

### 2.2 Full poll-to-render pipeline

| # | Test | What it covers |
|---|---|---|
| 1 | `test_poll_persist_render_round_trip` | FakeClient -> `run_poll_cycle` -> `NotificationCache` -> `render_cached_dashboards` -> verify output text contains expected notification titles |
| 2 | `test_poll_with_all_rule_types` | Config with global rules, per-repo rules, scoring, multiple dashboards; assert records correctly scored, excluded, rendered |
| 3 | `test_poll_dismiss_then_render_excludes` | Poll, dismiss a thread via cache, render; assert dismissed notification absent |

**File:** `tests/integration/test_pipeline.py`

### 2.3 Web API with populated data

| # | Test | What it covers |
|---|---|---|
| 1 | `test_snapshot_with_notifications` | Seed cache with notifications; assert `/api/snapshot` returns groups with items |
| 2 | `test_snapshot_multiple_dashboards` | Config with two dashboards; assert both appear in `dashboard_names`, each selectable |
| 3 | `test_snapshot_respects_dashboard_filters` | Dashboard with `reason_in` filter; assert only matching notifications returned |
| 4 | `test_snapshot_sorting_order` | Dashboard sorted by score descending; assert items arrive in correct order |

**File:** `tests/integration/test_web_api.py` (append)

### 2.4 CLI commands end-to-end

| # | Test | What it covers |
|---|---|---|
| 1 | `test_poll_dry_run_with_mocked_github` | Monkeypatch `GitHubNotificationsClient`; invoke `poll --dry-run`; assert no actions taken |
| 2 | `test_watch_with_iterations` | Monkeypatch client; invoke `watch --iterations 2`; assert two run summaries in output |
| 3 | `test_dashboard_renders_cached_data` | Pre-seed cache; invoke `dashboard`; assert table output |
| 4 | `test_dashboard_named_filter` | Invoke `dashboard --name triage`; assert only that dashboard rendered |
| 5 | `test_init_config_then_poll_fails_without_token` | Run `init-config` then `poll`; assert token error |

**File:** `tests/integration/test_cli.py` (extend)

---

## Phase 3: End-to-End Browser Tests (Playwright)

Goal: test the full web application as a user would interact with it in a browser.

### 3.1 Setup

**Dependencies to add:**

```text
pytest-playwright
```

**Add to `pyproject.toml`:**

```toml
[project.optional-dependencies]
e2e = ["pytest-playwright"]
```

**Install browsers (one-time):**

```bash
uv run playwright install chromium
```

**Fixture strategy (`tests/e2e/conftest.py`):**

1. Create a temporary config + cache directory per test session
2. Seed the cache with realistic notification data (10-20 records across 3+ repos)
3. Start the Litestar app in a subprocess on a random available port
4. Provide a `page` fixture (from `pytest-playwright`) pointed at `http://localhost:{port}`
5. Tear down the server after the session

```python
@pytest.fixture(scope="session")
def corvix_server(tmp_path_factory):
    """Start a Corvix web server with seeded data."""
    # 1. Write config YAML to tmp dir
    # 2. Seed cache JSON with test notifications
    # 3. Set CORVIX_CONFIG env var
    # 4. Start uvicorn in subprocess
    # 5. Wait for /api/health to respond
    # 6. Yield base URL
    # 7. Terminate subprocess

@pytest.fixture()
def app_page(page, corvix_server):
    """Navigate to the app and wait for initial load."""
    page.goto(corvix_server)
    page.wait_for_selector("#app")
    return page
```

### 3.2 Test Cases

All tests marked with `@pytest.mark.e2e`.

#### Page Load & SPA Shell

| # | Test | Steps |
|---|---|---|
| 1 | `test_page_loads_and_renders_title` | Navigate to `/`; assert page title contains "Corvix"; assert `#app` is not empty |
| 2 | `test_page_loads_css_and_js` | Assert no console errors; assert stylesheet loaded (check computed style on body) |
| 3 | `test_loading_skeleton_shown_then_replaced` | Navigate; assert loading skeleton visible initially; wait for data; assert skeleton gone |

#### Dashboard Display

| # | Test | Steps |
|---|---|---|
| 4 | `test_notifications_table_renders` | Wait for table; assert rows present matching seeded data count |
| 5 | `test_notification_row_shows_key_fields` | Find a row; assert it contains repository, reason, title, score |
| 6 | `test_dashboard_selector_lists_configured_dashboards` | Open dashboard dropdown; assert both "overview" and "triage" (or configured names) are listed |
| 7 | `test_switching_dashboard_updates_data` | Select a different dashboard from dropdown; assert table data changes (different count or grouping) |
| 8 | `test_empty_dashboard_shows_empty_state` | Switch to a dashboard with filters that match no records; assert empty state component shown |

#### Grouping & Sorting

| # | Test | Steps |
|---|---|---|
| 9 | `test_groups_displayed_with_headers` | If dashboard has `group_by: repository`; assert group headers visible with repo names |
| 10 | `test_sort_order_matches_config` | Dashboard sorted by score descending; extract scores from rows; assert descending order |

#### Filtering (Client-Side)

| # | Test | Steps |
|---|---|---|
| 11 | `test_filter_bar_filters_by_text` | Type a search query into the filter bar; assert only matching rows visible |
| 12 | `test_filter_clears_when_input_emptied` | Type then clear filter; assert all rows visible again |

#### Dismiss Notification

| # | Test | Steps |
|---|---|---|
| 13 | `test_dismiss_removes_row` | Click dismiss button on a row; assert row disappears from table |
| 14 | `test_dismiss_shows_undo_toast` | Dismiss a notification; assert undo toast/snackbar appears |
| 15 | `test_dismiss_persists_on_reload` | Dismiss, reload page; assert dismissed notification still gone |

#### Theme Switching

| # | Test | Steps |
|---|---|---|
| 16 | `test_theme_switch_changes_colors` | Open theme selector; switch to "graphite"; assert CSS variables updated (e.g., `--bg` changes) |
| 17 | `test_theme_persists_across_reload` | Switch theme, reload; assert theme still applied |

#### Keyboard Shortcuts

| # | Test | Steps |
|---|---|---|
| 18 | `test_keyboard_navigation` | Press arrow keys; assert row selection moves |
| 19 | `test_keyboard_dismiss` | Select a row, press dismiss key; assert row removed |

#### Responsiveness

| # | Test | Steps |
|---|---|---|
| 20 | `test_mobile_viewport` | Set viewport to 375x667; assert page renders without horizontal scroll; assert table adapts |

#### API Error Handling

| # | Test | Steps |
|---|---|---|
| 21 | `test_server_error_shows_error_state` | Stop the backend or corrupt config; navigate; assert error message displayed to user |

**File:** `tests/e2e/test_dashboard_ui.py`

---

## Phase 4: CI Configuration

### 4.1 Pytest Markers

Already defined in `pyproject.toml`:

```toml
markers = [
    "integration: marks tests that require external services",
    "e2e: marks end-to-end browser tests using Playwright",
]
```

### 4.2 Recommended CI Matrix

```bash
# Fast (every push):
uv run pytest -m "not integration and not e2e"

# Integration (every push, needs Docker):
uv run pytest -m "integration"

# E2E (merge queue / nightly):
uv run playwright install chromium
uv run pytest -m "e2e" --headed  # or headless in CI
```

### 4.3 Coverage Targets

| Layer | Current | Target |
|---|---|---|
| Unit | 82% | 95%+ |
| Integration | (included above) | 90%+ |
| E2E | 0% | Not measured by line coverage; measured by scenario coverage |
| **Overall** | **80%** | **92%+** |

---

## Implementation Order

1. **Phase 1.1** - `test_ingestion.py` (biggest coverage gap, pure mocking)
2. **Phase 1.4** - `test_domain.py` additions (URL derivation edge cases)
3. **Phase 1.3** - `test_config.py` additions (validation errors)
4. **Phase 1.6** - `test_storage_cache.py` additions (error paths)
5. **Phase 1.5** - `test_dashboarding.py` additions (two branches)
6. **Phase 1.2** - `test_cli.py` new unit tests (largest effort, most new code)
7. **Phase 1.7** - `test_web_api.py` dismiss flow
8. **Phase 2.1** - PostgreSQL integration tests (requires testcontainers setup)
9. **Phase 2.2-2.4** - Remaining integration tests
10. **Phase 3.1** - Playwright setup (conftest, fixtures, dependencies)
11. **Phase 3.2** - E2E test cases (iterative, start with page load + table rendering)
