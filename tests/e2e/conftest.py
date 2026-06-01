"""Playwright end-to-end fixtures."""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from collections.abc import Generator
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet

from corvix.domain import NotificationRecord, PollerStatus, format_timestamp
from corvix.storage import PostgresStorage
from tests.e2e.playwright_types import PageLike

HEALTH_TIMEOUT_SECONDS = 15.0
HEALTH_POLL_INTERVAL_SECONDS = 0.2
HTTP_OK = 200
FIXED_TIMESTAMP = "2024-01-01T00:00:00Z"

_RECORD_DICTS: list[dict[str, object]] = [
    {
        "thread_id": "101",
        "repository": "org/repo-a",
        "reason": "mention",
        "subject_title": "Review API changes",
        "subject_type": "PullRequest",
        "unread": True,
        "updated_at": FIXED_TIMESTAMP,
        "thread_url": "https://api.github.com/notifications/threads/101",
        "web_url": "https://github.com/org/repo-a/pull/101",
        "score": 90.0,
        "excluded": False,
        "matched_rules": [],
        "actions_taken": [],
        "dismissed": False,
    },
    {
        "thread_id": "102",
        "repository": "org/repo-b",
        "reason": "subscribed",
        "subject_title": "Dependency update",
        "subject_type": "PullRequest",
        "unread": True,
        "updated_at": FIXED_TIMESTAMP,
        "thread_url": "https://api.github.com/notifications/threads/102",
        "web_url": "https://github.com/org/repo-b/pull/102",
        "score": 20.0,
        "excluded": False,
        "matched_rules": [],
        "actions_taken": [],
        "dismissed": False,
    },
    {
        "thread_id": "103",
        "repository": "org/repo-a",
        "reason": "mention",
        "subject_title": "Triage flaky integration test",
        "subject_type": "Issue",
        "unread": False,
        "updated_at": FIXED_TIMESTAMP,
        "thread_url": "https://api.github.com/notifications/threads/103",
        "web_url": "https://github.com/org/repo-a/issues/103",
        "score": 45.0,
        "excluded": False,
        "matched_rules": [],
        "actions_taken": [],
        "dismissed": False,
    },
]


def _migrate_and_seed(sqlalchemy_url: str, psycopg_url: str) -> None:
    """Apply migrations and seed the single-user notification records."""
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    previous_url = os.environ.get("DATABASE_URL")
    previous_key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    try:
        command.upgrade(Config(str(alembic_ini)), "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        if previous_key is None:
            os.environ.pop("TOKEN_ENCRYPTION_KEY", None)
        else:
            os.environ["TOKEN_ENCRYPTION_KEY"] = previous_key

    records = [NotificationRecord.from_dict(item) for item in _RECORD_DICTS]
    now = datetime.now(tz=UTC)
    with PostgresStorage(connection_string=psycopg_url) as storage:
        storage.save_records(records, now)
        storage.save_status(
            PollerStatus(status="ok", last_poll_time=format_timestamp(now), last_error=None, last_error_time=None),
        )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, object]) -> dict[str, object]:
    """Pin locale and timezone so visual output is deterministic across environments."""
    return {
        **browser_context_args,
        "locale": "en-US",
        "timezone_id": "UTC",
    }


class _MockGitHubHandler(BaseHTTPRequestHandler):
    def _handle_thread_mutation(self) -> None:
        if self.path.startswith("/notifications/threads/"):
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_PATCH(self) -> None:
        self._handle_thread_mutation()

    def do_DELETE(self) -> None:
        self._handle_thread_mutation()

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def mock_github_api() -> Generator[str]:
    port = _find_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _MockGitHubHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout_seconds: float = HEALTH_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout_seconds
    health_url = f"{base_url}/api/v1/health"
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=1.0) as response:  # nosec B310  # NOSONAR python:S5144 - URL is always http://127.0.0.1:<port>/api/health (local test server)
                if response.status == HTTP_OK:
                    return
        except URLError:
            pass
        time.sleep(HEALTH_POLL_INTERVAL_SECONDS)
    msg = f"Corvix server did not become healthy at {health_url}."
    raise RuntimeError(msg)


@pytest.fixture()
def corvix_server(tmp_path_factory: pytest.TempPathFactory, mock_github_api: str) -> Generator[str]:
    # Function scope avoids cross-test state leakage (dismissed rows persisted in the
    # database) and keeps CI behavior deterministic regardless of test order.
    pytest.importorskip("playwright")
    testcontainers = pytest.importorskip("testcontainers.postgres")

    base_dir = tmp_path_factory.mktemp("corvix-e2e")
    config_file = base_dir / "corvix.yaml"
    config_file.write_text(
        f"""
github:
  token_env: GITHUB_TOKEN
  api_base_url: {mock_github_api}
dashboards:
  - name: overview
    group_by: repository
    sort_by: score
    include_read: true
  - name: triage
    group_by: reason
    sort_by: score
    include_read: true
    match:
      reason_in: ["mention"]
  - name: empty
    group_by: repository
    sort_by: score
    include_read: true
    match:
      reason_in: ["nonexistent-reason"]
""".strip(),
        encoding="utf-8",
    )

    container = testcontainers.PostgresContainer("postgres:16-alpine")
    try:
        container.start()
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"Could not start Postgres test container: {error}")
    try:
        raw_url = container.get_connection_url()
        sqlalchemy_url = raw_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        psycopg_url = raw_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        _migrate_and_seed(sqlalchemy_url, psycopg_url)

        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env["CORVIX_CONFIG"] = str(config_file)
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        env["GITHUB_TOKEN"] = "dummy-e2e-token"
        env["DATABASE_URL"] = psycopg_url
        env.pop("DATABASE_URL_FILE", None)
        process = subprocess.Popen(
            [
                "uv",
                "run",
                "python",
                "-m",
                "uvicorn",
                "corvix.web.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_for_health(base_url)
            yield base_url
        finally:
            # A still-open Server-Sent Events connection can stall uvicorn's
            # graceful shutdown, so force-kill if it does not exit promptly.
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    finally:
        container.stop()


@pytest.fixture()
def app_page(page: PageLike, corvix_server: str) -> PageLike:
    page.goto(corvix_server)
    page.wait_for_selector("#app")
    return page


@pytest.fixture(autouse=True)
def cleanup_routes(page: PageLike) -> Generator[None]:
    """Ensure all routed handlers are removed between tests."""
    yield
    page.unroute_all(behavior="ignoreErrors")
