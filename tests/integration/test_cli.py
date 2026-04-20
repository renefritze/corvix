"""CLI command integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

import corvix
from corvix import cli
from corvix.domain import Notification, NotificationRecord
from corvix.storage import NotificationCache


def test_version() -> None:
    assert corvix.__version__


def test_import() -> None:
    import corvix  # noqa: F401, PLC0415


def test_command_line_interface() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "init-config" in result.output
    assert "poll" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help" in help_result.output
    assert "Show this message and exit." in help_result.output


def test_init_config_command(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    result = runner.invoke(cli.main, ["init-config", str(config_path)])
    assert result.exit_code == 0
    assert config_path.exists()
    assert "github:" in config_path.read_text(encoding="utf-8")


def _write_config(path: Path, cache_file: Path, include_overview: bool = False) -> None:
    dashboards = """
dashboards:
  - name: triage
    group_by: repository
    sort_by: score
"""
    if include_overview:
        dashboards = """
dashboards:
  - name: overview
    group_by: repository
    sort_by: score
  - name: triage
    group_by: reason
    sort_by: score
"""
    path.write_text(
        f"""
github:
  token_env: GITHUB_TOKEN
polling:
  interval_seconds: 0
  per_page: 10
  max_pages: 1
state:
  cache_file: {cache_file}
{dashboards}
""".strip(),
        encoding="utf-8",
    )


def _record(thread_id: str) -> NotificationRecord:
    return NotificationRecord(
        notification=Notification(
            thread_id=thread_id,
            repository="org/repo",
            reason="mention",
            subject_title=f"Title {thread_id}",
            subject_type="PullRequest",
            unread=True,
            updated_at=datetime.now(tz=UTC),
            thread_url=f"https://api.github.com/notifications/threads/{thread_id}",
            web_url=f"https://github.com/org/repo/pull/{thread_id}",
        ),
        score=42.0,
        excluded=False,
    )


def test_poll_dry_run_with_mocked_github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    cache_path = tmp_path / "notifications.json"
    _write_config(config_path, cache_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            # Stub accepts production constructor kwargs used by CLI wiring.
            pass

        def fetch_notifications(self, _polling: object) -> list[Notification]:
            return []

        def mark_thread_read(self, _thread_id: str) -> None:
            return

        def dismiss_thread(self, _thread_id: str) -> None:
            return

    monkeypatch.setattr(cli, "GitHubNotificationsClient", FakeClient)

    result = runner.invoke(cli.main, ["--config", str(config_path), "poll", "--dry-run"])

    assert result.exit_code == 0
    assert "Fetched: 0" in result.output
    assert "Actions executed: 0" in result.output
    assert cache_path.exists()


def test_watch_with_iterations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            # Stub accepts production constructor kwargs used by CLI wiring.
            pass

        def fetch_notifications(self, _polling: object) -> list[Notification]:
            return []

        def mark_thread_read(self, _thread_id: str) -> None:
            return

        def dismiss_thread(self, _thread_id: str) -> None:
            return

    monkeypatch.setattr(cli, "GitHubNotificationsClient", FakeClient)

    result = runner.invoke(cli.main, ["--config", str(config_path), "watch", "--iterations", "2"])

    assert result.exit_code == 0
    assert "Run 1: fetched=0, excluded=0, actions=0" in result.output
    assert "Run 2: fetched=0, excluded=0, actions=0" in result.output


def test_dashboard_renders_cached_data(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    cache_path = tmp_path / "notifications.json"
    _write_config(config_path, cache_path)
    NotificationCache(path=cache_path).save([_record("100")], generated_at=datetime.now(tz=UTC))

    result = runner.invoke(cli.main, ["--config", str(config_path), "dashboard"])

    assert result.exit_code == 0
    assert "triage: 1 rows" in result.output


def test_dashboard_named_filter(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    cache_path = tmp_path / "notifications.json"
    _write_config(config_path, cache_path, include_overview=True)
    NotificationCache(path=cache_path).save([_record("100")], generated_at=datetime.now(tz=UTC))

    result = runner.invoke(cli.main, ["--config", str(config_path), "dashboard", "--name", "triage"])

    assert result.exit_code == 0
    assert "triage: 1 rows" in result.output
    assert "overview:" not in result.output


def test_init_config_then_poll_fails_without_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    init = runner.invoke(cli.main, ["init-config", str(config_path)])
    assert init.exit_code == 0
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)

    result = runner.invoke(cli.main, ["--config", str(config_path), "poll"])

    assert result.exit_code != 0
    assert "required for polling GitHub notifications" in result.output
