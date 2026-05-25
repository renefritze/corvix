# Security

## Reporting a Vulnerability

Please do not file public GitHub issues for security vulnerabilities. Instead,
use [GitHub's private security advisory](https://github.com/renefritze/corvix/security/advisories/new)
feature to report vulnerabilities confidentially.

We aim to respond within 72 hours and will coordinate a fix and disclosure
timeline with you.

---

## Security Hardening (2026-05 — CWE-918 / SSRF / path-injection)

These fixes address all alerts raised by the GitHub code-scanning suite
(CodeQL + Sonar) and were originally tracked in PRs #79 and #81.

### `src/corvix/ingestion.py`

| Issue | Fix |
|---|---|
| **Path-traversal via `thread_id`** (CWE-918) | Added `_validate_thread_id()` which rejects any value that is not a positive decimal integer before the ID is embedded in a URL path. `mark_thread_read()` and `dismiss_thread()` both call this guard first. |
| **SSRF via `fetch_json_url`** (Sonar S5144) | Replaced `_validate_api_host()` (hostname-only check) with `_sanitize_api_url()`, which *reconstructs* the request URL using the trusted `scheme + netloc` from `self.api_base_url` and passes only the `path + query` from the caller's input through. This eliminates scheme-injection and host-manipulation SSRF vectors. |
| **Bandit B310 `urlopen` calls** | Annotated with `# nosec B310` and justification comments to document that each call site receives only URLs produced by `_build_url` (trusted config) or sanitised by `_sanitize_api_url`. |

### `src/corvix/hydration/providers/github_web_url.py`

| Issue | Fix |
|---|---|
| **`check_suite_id` path injection** | `_resolve_check_suite_from_subject_url` validates `check_suite_id` with `re.fullmatch(r"[1-9]\d*", …)` before embedding the value in a URL. |
| **SSRF via `subject_url` host** | `_resolve_check_suite_from_subject_url` now builds the check-runs URL from `client.api_base_url` (trusted config) rather than from `parsed.scheme / parsed.netloc` of the external `subject_url`. |
| **SSRF via `repo_base` host** | `_resolve_check_suite` uses `client.api_base_url.rstrip("/")` instead of calling `_build_actions_api_base(repo_base)`, ensuring no external data can influence the API host in `runs_url`. |
| **`_build_actions_api_base` scheme injection** | The function now uses a literal `"https://"` prefix rather than `parsed.scheme` from the external `repo_base` URL. |

### `src/corvix/pipeline/base.py`

Added `api_base_url: str` to the `JsonFetchClient` protocol so all providers
can construct upstream API URLs from trusted configuration rather than from
data received in API responses.

### `src/corvix/cli.py` and `src/corvix/web/app.py`

Annotated intentional `0.0.0.0` bind-all defaults with `# nosec B104` and
explanatory comments (these defaults are correct for container deployments).

### `tests/e2e/conftest.py`

Annotated the health-check `urlopen` call with `# nosec B310` — the URL is
always `http://127.0.0.1:<port>/api/health` (loopback only).

### Security regression tests added

`tests/unit/test_ingestion.py` covers:

- `test_validate_thread_id_accepts_positive_integers` / `_rejects_non_numeric`
- `test_mark_thread_read_rejects_path_traversal`
- `test_dismiss_thread_rejects_path_traversal`
- `test_sanitize_api_url_accepts_matching_host`
- `test_sanitize_api_url_replaces_scheme_with_trusted`
- `test_sanitize_api_url_rejects_mismatched_host`
- `test_sanitize_api_url_preserves_path_and_query`
- `test_fetch_json_url_uses_sanitized_url`
- `test_fetch_json_url_rejects_wrong_host`
