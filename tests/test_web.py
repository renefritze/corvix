"""Tests for Corvix web API endpoints."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from litestar.testing import TestClient

from corvix.web.app import INDEX_HTML, THEMES, app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_themes_endpoint(client: TestClient) -> None:
    response = client.get("/api/themes")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert "themes" in payload
    themes = payload["themes"]
    assert set(themes.keys()) == {"default", "dark", "solarized"}


def test_themes_have_required_vars(client: TestClient) -> None:
    response = client.get("/api/themes")
    themes = response.json()["themes"]
    required_vars = {"bg", "ink", "surface", "accent", "line", "ok", "muted"}
    for name, preset in themes.items():
        assert set(preset.keys()) == required_vars, f"Theme '{name}' missing vars"


def test_themes_match_python_constant(client: TestClient) -> None:
    response = client.get("/api/themes")
    assert response.json()["themes"] == THEMES


def test_themes_default_matches_css_root() -> None:
    """Default theme values must match the CSS :root variables in INDEX_HTML."""
    default = THEMES["default"]
    assert default["bg"] in INDEX_HTML
    assert default["accent"] in INDEX_HTML


def test_index_contains_theme_selector() -> None:
    assert 'id="theme"' in INDEX_HTML
    assert "applyTheme" in INDEX_HTML
    assert "localStorage" in INDEX_HTML


def test_index_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert "text/html" in response.headers["content-type"]
    assert "Corvix" in response.text
