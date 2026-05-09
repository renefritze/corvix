"""Direct tests for private helpers in corvix.web.app."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from litestar.exceptions import HTTPException

from corvix.config import AppConfig, GitHubAccountConfig, GitHubConfig
from corvix.domain import Notification, NotificationRecord
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

    monkeypatch.setattr(web_app, "_STATIC_ROOT", missing_root)

    assert web_app._asset_version_token() == "dev"


def test_default_account_id_raises_when_no_accounts_are_configured() -> None:
    with pytest.raises(HTTPException, match="No GitHub accounts configured"):
        web_app._default_account_id(AppConfig())


def test_yaml_scalar_uses_plain_string_conversion_for_numbers() -> None:
    assert web_app._yaml_scalar(42) == "42"


def test_context_path_value_returns_false_when_path_hits_non_mapping() -> None:
    found, value = web_app._context_path_value(context={"github": []}, path="github.pr_state.state")

    assert found is False
    assert value is None


def test_context_path_value_returns_true_for_explicit_none_values() -> None:
    found, value = web_app._context_path_value(
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

    monkeypatch.setattr(web_app, "load_config", _raise_bad_config)

    with pytest.raises(HTTPException, match="Invalid config"):
        web_app._load_runtime_config()


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

    assert web_app._rule_name_for_record(record) == "ignore-rule-rule-rule"


def test_require_account_returns_matching_account() -> None:
    config = AppConfig(
        github=GitHubConfig(accounts=[GitHubAccountConfig(id="primary", label="Primary", token_env="GITHUB_TOKEN")])
    )

    account = web_app._require_account(config=config, account_id="primary")

    assert account.id == "primary"
