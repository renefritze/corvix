"""Web API integration tests."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path

import pytest
from litestar.testing import TestClient

from corvix.web.app import INDEX_HTML, THEMES, app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def configured_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with a real config + empty cache injected via env var."""
    cache_file = tmp_path / "notifications.json"
    cache_file.write_text(
        json.dumps({"generated_at": "2024-01-01T00:00:00Z", "notifications": []}),
        encoding="utf-8",
    )
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        f"""
github:
  token_env: GITHUB_TOKEN
state:
  cache_file: {cache_file}
dashboards:
  - name: triage
    group_by: repository
    sort_by: score
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("CORVIX_CONFIG", str(config_file))
    return TestClient(app)


# --- /api/health ---


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


# --- /api/themes ---


def test_themes_endpoint(client: TestClient) -> None:
    response = client.get("/api/themes")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert "themes" in payload
    themes = payload["themes"]
    assert set(themes.keys()) == set(THEMES.keys())


def test_themes_have_required_vars(client: TestClient) -> None:
    themes = client.get("/api/themes").json()["themes"]
    required_vars = {"bg", "surface", "surface_elevated", "ink", "muted", "accent", "line", "ok", "danger"}
    for name, preset in themes.items():
        assert set(preset.keys()) == required_vars, f"Theme '{name}' missing vars"


def test_themes_match_python_constant(client: TestClient) -> None:
    assert client.get("/api/themes").json()["themes"] == THEMES


def test_themes_have_midnight_and_graphite() -> None:
    assert "midnight" in THEMES
    assert "graphite" in THEMES


# --- / index ---


def test_index_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert "text/html" in response.headers["content-type"]
    assert "Corvix" in response.text


def test_index_html_is_spa_shell() -> None:
    assert '<div id="app">' in INDEX_HTML
    assert "Corvix" in INDEX_HTML


# --- /api/dashboards ---


def test_dashboards_endpoint(configured_client: TestClient) -> None:
    response = configured_client.get("/api/dashboards")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert "dashboard_names" in payload
    assert "triage" in payload["dashboard_names"]


def test_dashboards_no_config_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORVIX_CONFIG", "/nonexistent/path/corvix.yaml")
    response = client.get("/api/dashboards")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# --- /api/snapshot ---


def test_snapshot_returns_dashboard_data(configured_client: TestClient) -> None:
    response = configured_client.get("/api/snapshot")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["name"] == "triage"
    assert "groups" in payload
    assert "total_items" in payload
    assert "dashboard_names" in payload
    assert "triage" in payload["dashboard_names"]


def test_snapshot_selects_by_name(configured_client: TestClient) -> None:
    response = configured_client.get("/api/snapshot?dashboard=triage")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "triage"


def test_snapshot_unknown_dashboard_returns_404(configured_client: TestClient) -> None:
    response = configured_client.get("/api/snapshot?dashboard=nonexistent")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_snapshot_no_config_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORVIX_CONFIG", "/nonexistent/path/corvix.yaml")
    response = client.get("/api/snapshot")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# --- /api/notifications/{thread_id}/dismiss ---


def test_dismiss_without_token_returns_500(
    configured_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    response = configured_client.post("/api/notifications/123/dismiss")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_dismiss_success(configured_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr(
        "corvix.web.app.GitHubNotificationsClient.dismiss_thread",
        lambda _self, thread_id: calls.append(thread_id),
    )

    response = configured_client.post("/api/notifications/abc123/dismiss")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert calls == ["abc123"]


def test_dismiss_github_error_returns_502(configured_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("corvix.web.app.GitHubNotificationsClient.dismiss_thread", _raise)

    response = configured_client.post("/api/notifications/123/dismiss")

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert "Failed to dismiss thread" in response.text


def test_dismiss_token_env_error_returns_500(
    configured_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("corvix.web.app.get_env_value", lambda _name: (_ for _ in ()).throw(ValueError("bad env")))

    response = configured_client.post("/api/notifications/123/dismiss")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_load_runtime_config_invalid_yaml(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text("github: [\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(bad_config))

    response = client.get("/api/dashboards")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
