"""Environment helper tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from corvix.env import get_env_value


def test_get_env_value_prefers_direct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_SECRET", "direct-value")
    assert get_env_value("TEST_SECRET") == "direct-value"


def test_get_env_value_reads_file_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.setenv("TEST_SECRET_FILE", str(secret_file))
    assert get_env_value("TEST_SECRET") == "from-file"


def test_get_env_value_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_SECRET", raising=False)
    monkeypatch.delenv("TEST_SECRET_FILE", raising=False)
    assert get_env_value("TEST_SECRET") is None


def test_get_env_value_rejects_both_env_and_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.setenv("TEST_SECRET", "direct-value")
    monkeypatch.setenv("TEST_SECRET_FILE", str(secret_file))
    with pytest.raises(ValueError, match="Both 'TEST_SECRET' and 'TEST_SECRET_FILE' are set"):
        get_env_value("TEST_SECRET")


def test_get_env_value_reports_unreadable_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_SECRET_FILE", "/does/not/exist/secret.txt")
    with pytest.raises(ValueError, match="Failed to read secret file from 'TEST_SECRET_FILE'"):
        get_env_value("TEST_SECRET")
