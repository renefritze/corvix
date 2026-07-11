"""Direct tests for private helpers in the corvix.web.* modules."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from litestar.exceptions import HTTPException

from corvix.config import AppConfig, GitHubAccountConfig, GitHubConfig
from corvix.domain import Notification, NotificationRecord
from corvix.web import actions, assets, rule_snippets, runtime_config
from corvix.web import app as web_app


def _record(
    *, repository: str = "org/repo", reason: str = "mention", subject_type: str = "PullRequest"
) -> NotificationRecord:
    notification = Notification(
        thread_id="1",
        repository=repository,
        reason=reason,
        subject_title="Test title",
        subject_type=subject_type,
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    return NotificationRecord(notification=notification, score=1.0, excluded=False, context={})


def test_asset_version_token_returns_dev_when_assets_are_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_root = tmp_path / "missing-static"
    missing_root.mkdir()

    monkeypatch.setattr(assets, "_STATIC_ROOT", missing_root)

    assert assets._asset_version_token() == "dev"


def test_yaml_scalar_uses_plain_string_conversion_for_numbers() -> None:
    assert rule_snippets._yaml_scalar(42) == "42"


def test_context_path_value_returns_false_when_path_hits_non_mapping() -> None:
    found, value = rule_snippets._context_path_value(context={"github": []}, path="github.pr_state.state")

    assert found is False
    assert value is None


def test_context_path_value_returns_true_for_explicit_none_values() -> None:
    found, value = rule_snippets._context_path_value(
        context={"github": {"pr_state": {"state": None}}}, path="github.pr_state.state"
    )

    assert found is True
    assert value is None


def test_load_runtime_config_raises_for_invalid_config_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("github: {}\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(config_path))

    def _raise_bad_config(_path: Path) -> None:
        raise ValueError("bad config")

    monkeypatch.setattr(runtime_config, "load_config", _raise_bad_config)

    with pytest.raises(HTTPException, match="Invalid config"):
        runtime_config._load_runtime_config()


def test_run_uses_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setenv("CORVIX_WEB_HOST", "127.0.0.1")
    monkeypatch.setenv("CORVIX_WEB_PORT", "9001")
    monkeypatch.setenv("CORVIX_WEB_RELOAD", "yes")
    monkeypatch.setattr(web_app.uvicorn, "run", lambda *args, **kwargs: calls.append({"args": args, "kwargs": kwargs}))

    web_app.run()

    assert len(calls) == 1
    assert calls[0]["args"] == ("corvix.web.app:app",)
    assert calls[0]["kwargs"] == {
        "host": "127.0.0.1",
        "port": 9001,
        "reload": True,
        "reload_dirs": ["src"],
    }


def test_rule_name_for_record_uses_rule_fallback_for_empty_slug_parts() -> None:
    record = _record(repository="!!!", reason="***", subject_type="???")

    assert rule_snippets._rule_name_for_record(record) == "ignore-rule-rule-rule"


def test_require_account_returns_matching_account() -> None:
    config = AppConfig(
        github=GitHubConfig(accounts=[GitHubAccountConfig(id="primary", label="Primary", token_env="GITHUB_TOKEN")])
    )

    account = actions._require_account(config=config, account_id="primary")

    assert account.id == "primary"


# ---------------------------------------------------------------------------
# _load_runtime_config — mtime-based caching
# ---------------------------------------------------------------------------


def test_load_runtime_config_is_cached_on_second_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call with the same path+mtime returns the identical object."""
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("github:\n  token_env: GITHUB_TOKEN\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(config_path))

    first = runtime_config._load_runtime_config()
    second = runtime_config._load_runtime_config()

    assert first is second


def test_load_runtime_config_reloads_when_file_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Config is re-parsed when the file is overwritten (mtime advances)."""
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("github:\n  token_env: GITHUB_TOKEN\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(config_path))

    first = runtime_config._load_runtime_config()

    # Overwrite — filesystem granularity may be 1 s, so nudge the mtime explicitly.
    config_path.write_text("github:\n  token_env: ANOTHER_TOKEN\n", encoding="utf-8")
    new_mtime = config_path.stat().st_mtime + 1.0
    os.utime(config_path, (new_mtime, new_mtime))

    second = runtime_config._load_runtime_config()

    assert first is not second
    assert second.github.accounts[0].token_env == "ANOTHER_TOKEN"


def test_clear_config_cache_forces_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """After _clear_config_cache(), the next call re-parses from disk."""
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("github:\n  token_env: GITHUB_TOKEN\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(config_path))

    first = runtime_config._load_runtime_config()
    runtime_config._clear_config_cache()
    second = runtime_config._load_runtime_config()

    # Different object — it was re-parsed after the cache was cleared.
    assert first is not second


def test_load_runtime_config_raises_for_missing_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORVIX_CONFIG", "/nonexistent/corvix.yaml")

    with pytest.raises(HTTPException, match="does not exist"):
        runtime_config._load_runtime_config()


def test_load_runtime_config_cache_not_poisoned_after_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed load must not populate the cache; the next call retries."""
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text("github: {}\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(config_path))

    parse_calls: list[Path] = []

    def _bad_load(path: Path) -> AppConfig:
        parse_calls.append(path)
        raise ValueError("bad config")

    monkeypatch.setattr(runtime_config, "load_config", _bad_load)

    with pytest.raises(HTTPException):
        runtime_config._load_runtime_config()

    # Cache must not have been populated.
    assert runtime_config._config_cache.config is None

    with pytest.raises(HTTPException):
        runtime_config._load_runtime_config()

    # load_config was called both times, not skipped on the second call.
    assert len(parse_calls) == 2
