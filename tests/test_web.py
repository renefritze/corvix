"""Tests for Corvix web API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files as resource_files
from pathlib import Path
from textwrap import dedent

import pytest

from corvix.domain import Notification, NotificationRecord
from corvix.storage import NotificationCache
from corvix.web.app import INDEX_HTML, THEMES, api_themes, health, index, snapshot


def test_health() -> None:
    assert health.fn() == {"status": "ok"}


def test_themes_endpoint() -> None:
    payload = api_themes.fn()
    assert "themes" in payload
    themes = payload["themes"]
    assert set(themes.keys()) == {"midnight", "graphite"}


def test_themes_have_required_vars() -> None:
    themes = api_themes.fn()["themes"]
    required_vars = {"bg", "surface", "surface_elevated", "ink", "muted", "accent", "line", "ok", "danger"}
    for name, preset in themes.items():
        assert set(preset.keys()) == required_vars, f"Theme '{name}' missing vars"


def test_themes_match_python_constant() -> None:
    assert api_themes.fn()["themes"] == THEMES


def test_index_html_is_html() -> None:
    response = index.fn()
    assert response.media_type == "text/html"


def test_index_html_contains_app_mount() -> None:
    """Vite SPA shell must have a root mount point for Preact."""
    assert 'id="app"' in INDEX_HTML


def test_index_html_references_static_assets() -> None:
    assert "/assets/app.js" in INDEX_HTML
    assert "/assets/index.css" in INDEX_HTML
    assert "/assets/" in INDEX_HTML
    assert 'color-scheme" content="dark"' in INDEX_HTML


def test_built_assets_exist() -> None:
    assets = resource_files("corvix.web").joinpath("static/assets")
    assert assets.joinpath("app.js").is_file()
    assert assets.joinpath("index.css").is_file()


def test_index_html_is_served() -> None:
    response = index.fn()
    assert response.content == INDEX_HTML
    assert "Corvix" in response.content


def test_snapshot_includes_summary_and_web_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_path = tmp_path / "notifications.json"
    config_path = tmp_path / "corvix.yaml"
    now = datetime.now(tz=UTC)

    NotificationCache(path=cache_path).save(
        [
            NotificationRecord(
                notification=Notification(
                    thread_id="1",
                    repository="org/repo",
                    reason="mention",
                    subject_title="Review this",
                    subject_type="PullRequest",
                    unread=True,
                    updated_at=now,
                    web_url="https://github.com/org/repo/pull/1",
                ),
                score=17.5,
                excluded=False,
            )
        ],
        generated_at=now,
    )
    config_path.write_text(
        dedent(
            f"""
            github:
              token_env: GITHUB_TOKEN
            state:
              cache_file: {cache_path}
            dashboards:
              - name: triage
                group_by: repository
                sort_by: score
                include_read: true
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CORVIX_CONFIG", str(config_path))

    payload = snapshot.fn()

    assert payload["summary"]["unread_items"] == 1
    assert payload["summary"]["repository_count"] == 1
    assert payload["groups"][0]["items"][0]["web_url"] == "https://github.com/org/repo/pull/1"
