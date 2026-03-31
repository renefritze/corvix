"""Unit tests for CLI command behavior and helper functions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from corvix import cli
from corvix.presentation import DashboardRenderResult
from corvix.services import PollingSummary


def _write_config(path: Path, cache_file: Path) -> None:
    path.write_text(
        f"""
github:
  token_env: GITHUB_TOKEN
state:
  cache_file: {cache_file}
dashboards:
  - name: triage
    group_by: repository
    sort_by: score
""".strip(),
        encoding="utf-8",
    )


def test_init_config_force_overwrites(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("placeholder: true\n", encoding="utf-8")

    result = runner.invoke(cli.main, ["init-config", str(config_path), "--force"])

    assert result.exit_code == 0
    content = config_path.read_text(encoding="utf-8")
    assert "github:" in content
    assert "placeholder" not in content


def test_init_config_existing_no_force_fails(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("github: {}\n", encoding="utf-8")

    result = runner.invoke(cli.main, ["init-config", str(config_path)])

    assert result.exit_code != 0
    assert "Use --force to overwrite" in result.output


def test_poll_command_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    def _fake_run_poll_cycle(**kwargs: object) -> PollingSummary:
        assert kwargs["apply_actions"] is False
        return PollingSummary(fetched=2, excluded=1, actions_taken=0, errors=[])

    monkeypatch.setattr(cli, "run_poll_cycle", _fake_run_poll_cycle)

    result = runner.invoke(cli.main, ["--config", str(config_path), "poll", "--dry-run"])

    assert result.exit_code == 0
    assert "Fetched: 2" in result.output
    assert "Excluded from dashboards: 1" in result.output
    assert "Actions executed: 0" in result.output


def test_poll_command_missing_config(tmp_path: Path) -> None:
    runner = CliRunner()
    missing = tmp_path / "does-not-exist.yaml"

    result = runner.invoke(cli.main, ["--config", str(missing), "poll"])

    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_poll_command_missing_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)

    result = runner.invoke(cli.main, ["--config", str(config_path), "poll"])

    assert result.exit_code != 0
    assert "required for polling GitHub notifications" in result.output


def test_watch_command_iterations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    monkeypatch.setattr(
        cli,
        "run_watch_loop",
        lambda **_: [PollingSummary(fetched=3, excluded=1, actions_taken=0, errors=[])],
    )

    result = runner.invoke(cli.main, ["--config", str(config_path), "watch", "--iterations", "1"])

    assert result.exit_code == 0
    assert "Run 1: fetched=3, excluded=1, actions=0" in result.output


def test_dashboard_command_renders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setattr(
        cli,
        "render_cached_dashboards",
        lambda **_: [DashboardRenderResult(dashboard_name="triage", rows=4)],
    )

    result = runner.invoke(cli.main, ["--config", str(config_path), "dashboard"])

    assert result.exit_code == 0
    assert "triage: 4 rows" in result.output


def test_dashboard_command_no_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setattr(cli, "render_cached_dashboards", lambda **_: [])

    result = runner.invoke(cli.main, ["--config", str(config_path), "dashboard"])

    assert result.exit_code == 0
    assert "No dashboards rendered." in result.output


def test_serve_command_sets_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    called = {"value": False}

    def _fake_run_web() -> None:
        called["value"] = True

    monkeypatch.setattr(cli, "run_web", _fake_run_web)

    result = runner.invoke(
        cli.main,
        ["--config", str(config_path), "serve", "--host", "127.0.0.1", "--port", "9001", "--reload"],
    )

    assert result.exit_code == 0
    assert called["value"] is True
    assert cli.environ["CORVIX_CONFIG"] == str(config_path)
    assert cli.environ["CORVIX_WEB_HOST"] == "127.0.0.1"
    assert cli.environ["CORVIX_WEB_PORT"] == "9001"
    assert cli.environ["CORVIX_WEB_RELOAD"] == "true"


def test_migrate_cache_command_no_db_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setattr(cli, "get_database_url", lambda *_: None)

    result = runner.invoke(cli.main, ["--config", str(config_path), "migrate-cache", "--user-id", "user-1"])

    assert result.exit_code != 0
    assert "Environment variable 'DATABASE_URL' is not set." in result.output


def test_migrate_cache_command_empty_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    _write_config(config_path, tmp_path / "notifications.json")
    monkeypatch.setattr(cli, "get_database_url", lambda *_: "postgresql://user:pass@localhost/db")
    monkeypatch.setattr(cli.NotificationCache, "load", lambda *_: (datetime.now(tz=UTC), []))

    result = runner.invoke(cli.main, ["--config", str(config_path), "migrate-cache", "--user-id", "user-1"])

    assert result.exit_code == 0
    assert "nothing to migrate" in result.output


def test_load_app_config_invalid_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("github: []\n", encoding="utf-8")

    with pytest.raises(click.ClickException, match="Invalid config"):
        cli._load_app_config(config_path)


def test_resolve_token_file_variant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    token_file = tmp_path / "token.txt"
    token_file.write_text("file-token\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(token_file))

    resolved = cli._resolve_token("GITHUB_TOKEN")

    assert resolved == "file-token"


def test_config_path_from_context_missing() -> None:
    ctx = click.Context(cli.main, obj={})
    with pytest.raises(click.ClickException, match="Missing config path"):
        cli._config_path_from_context(ctx)
