"""Playwright end-to-end fixtures."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from collections.abc import Generator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from tests.e2e.playwright_types import PageLike

HEALTH_TIMEOUT_SECONDS = 15.0
HEALTH_POLL_INTERVAL_SECONDS = 0.2
HTTP_OK = 200


class _MockGitHubHandler(BaseHTTPRequestHandler):
    def do_PATCH(self) -> None:
        if self.path.startswith("/notifications/threads/"):
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_DELETE(self) -> None:
        if self.path.startswith("/notifications/threads/"):
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

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
    health_url = f"{base_url}/api/health"
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=1.0) as response:
                if response.status == HTTP_OK:
                    return
        except URLError:
            pass
        time.sleep(HEALTH_POLL_INTERVAL_SECONDS)
    msg = f"Corvix server did not become healthy at {health_url}."
    raise RuntimeError(msg)


@pytest.fixture(scope="session")
def corvix_server(tmp_path_factory: pytest.TempPathFactory, mock_github_api: str) -> Generator[str]:
    pytest.importorskip("playwright")

    base_dir = tmp_path_factory.mktemp("corvix-e2e")
    cache_file = base_dir / "notifications.json"
    config_file = base_dir / "corvix.yaml"
    cache_file.write_text(
        json.dumps(
            {
                "generated_at": "2024-01-01T00:00:00Z",
                "notifications": [
                    {
                        "thread_id": "101",
                        "repository": "org/repo-a",
                        "reason": "mention",
                        "subject_title": "Review API changes",
                        "subject_type": "PullRequest",
                        "unread": True,
                        "updated_at": "2024-01-01T00:00:00Z",
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
                        "updated_at": "2024-01-01T00:00:00Z",
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
                        "updated_at": "2024-01-01T00:00:00Z",
                        "thread_url": "https://api.github.com/notifications/threads/103",
                        "web_url": "https://github.com/org/repo-a/issues/103",
                        "score": 45.0,
                        "excluded": False,
                        "matched_rules": [],
                        "actions_taken": [],
                        "dismissed": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    config_file.write_text(
        f"""
github:
  token_env: GITHUB_TOKEN
  api_base_url: {mock_github_api}
state:
  cache_file: {cache_file}
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

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["CORVIX_CONFIG"] = str(config_file)
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    env["GITHUB_TOKEN"] = "dummy-e2e-token"
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
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture()
def app_page(page: PageLike, corvix_server: str) -> PageLike:
    page.goto(corvix_server)
    page.wait_for_selector("#app")
    return page
