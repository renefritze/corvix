"""Web API integration tests."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from pathlib import Path

import pytest
from litestar.testing import TestClient

from corvix.config import load_config
from corvix.web.app import INDEX_HTML, THEMES, app

GENERATED_AT = "2024-01-01T00:00:00Z"
EXPECTED_POPULATED_TOTAL_ITEMS = 3
EXPECTED_POPULATED_GROUPS = 2


def _raise_bad_env(_name: str) -> str:
    raise ValueError("bad env")


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


def _record_payload(
    *,
    thread_id: str,
    repository: str,
    reason: str,
    score: float,
    unread: bool = True,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "thread_id": thread_id,
        "repository": repository,
        "reason": reason,
        "subject_title": f"Title {thread_id}",
        "subject_type": "PullRequest",
        "unread": unread,
        "updated_at": GENERATED_AT,
        "thread_url": f"https://api.github.com/notifications/threads/{thread_id}",
        "web_url": f"https://github.com/{repository}/pull/{thread_id}",
        "score": score,
        "excluded": False,
        "matched_rules": [],
        "actions_taken": [],
        "dismissed": False,
        "context": context or {},
    }


@pytest.fixture()
def populated_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    cache_file = tmp_path / "notifications.json"
    cache_file.write_text(
        json.dumps(
            {
                "generated_at": GENERATED_AT,
                "notifications": [
                    _record_payload(thread_id="101", repository="org/repo-a", reason="mention", score=90.0),
                    _record_payload(thread_id="102", repository="org/repo-b", reason="subscribed", score=30.0),
                    _record_payload(thread_id="103", repository="org/repo-a", reason="mention", score=60.0),
                ],
            }
        ),
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


def test_index_html_references_versioned_assets(client: TestClient) -> None:
    response = client.get("/")
    assert "/assets/app.js?v=" in response.text
    assert "/assets/index.css?v=" in response.text
    assert "/assets/favicon.svg?v=" in response.text
    assert "__ASSET_VERSION__" not in response.text


def test_dashboard_path_serves_spa_shell(client: TestClient) -> None:
    response = client.get("/dashboards/triage")
    assert response.status_code == HTTPStatus.OK
    assert "text/html" in response.headers["content-type"]
    assert "Corvix" in response.text


def test_assets_are_served_with_long_lived_cache_control(client: TestClient) -> None:
    response = client.get("/assets/app.js")
    assert response.status_code == HTTPStatus.OK
    cache_control = response.headers.get("cache-control", "")
    assert "public" in cache_control
    assert "max-age=31536000" in cache_control
    assert "immutable" in cache_control


def test_assets_are_served_with_gzip_compression(client: TestClient) -> None:
    response = client.get("/assets/app.js", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("content-encoding") == "gzip"


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
    assert payload["include_read"] is False
    assert payload["sort_by"] == "score"
    assert payload["descending"] is True
    assert "groups" in payload
    assert "total_items" in payload
    assert "dashboard_names" in payload
    assert "triage" in payload["dashboard_names"]


def test_snapshot_selects_by_name(configured_client: TestClient) -> None:
    response = configured_client.get("/api/snapshot?dashboard=triage")
    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["name"] == "triage"
    assert payload["include_read"] is False


def test_snapshot_unknown_dashboard_returns_404(configured_client: TestClient) -> None:
    response = configured_client.get("/api/snapshot?dashboard=nonexistent")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_snapshot_no_config_returns_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORVIX_CONFIG", "/nonexistent/path/corvix.yaml")
    response = client.get("/api/snapshot")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_snapshot_with_notifications(populated_client: TestClient) -> None:
    response = populated_client.get("/api/snapshot?dashboard=overview")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["name"] == "overview"
    assert payload["include_read"] is True
    assert payload["total_items"] == EXPECTED_POPULATED_TOTAL_ITEMS
    assert len(payload["groups"]) == EXPECTED_POPULATED_GROUPS
    assert sum(len(group["items"]) for group in payload["groups"]) == EXPECTED_POPULATED_TOTAL_ITEMS


def test_snapshot_multiple_dashboards(populated_client: TestClient) -> None:
    response = populated_client.get("/api/dashboards")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["dashboard_names"] == ["overview", "triage"]


def test_snapshot_respects_dashboard_filters(populated_client: TestClient) -> None:
    response = populated_client.get("/api/snapshot?dashboard=triage")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["name"] == "triage"
    assert payload["include_read"] is True
    reasons = [item["reason"] for group in payload["groups"] for item in group["items"]]
    assert reasons
    assert set(reasons) == {"mention"}


def test_snapshot_sorting_order(populated_client: TestClient) -> None:
    response = populated_client.get("/api/snapshot?dashboard=overview")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    scores = [item["score"] for group in payload["groups"] for item in group["items"]]
    assert scores == sorted(scores, reverse=True)


def test_rule_snippets_endpoint_returns_dashboard_and_global_snippets(populated_client: TestClient) -> None:
    response = populated_client.get("/api/notifications/primary/101/rule-snippets?dashboard=overview")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["dashboard_name"] == "overview"
    assert 'repository_in: ["org/repo-a"]' in payload["dashboard_ignore_rule_snippet"]
    assert 'title_regex: "^Title 101$"' in payload["dashboard_ignore_rule_snippet"]
    assert "exclude_from_dashboards: true" in payload["global_exclude_rule_snippet"]
    assert payload["dashboard_ignore_rule_with_context_snippet"] is None
    assert payload["global_exclude_rule_with_context_snippet"] is None


def test_rule_snippets_endpoint_returns_context_variants(
    configured_client: TestClient,
) -> None:
    config_path = Path(os.environ["CORVIX_CONFIG"])
    cache_file = load_config(config_path).resolve_cache_file()
    cache_file.write_text(
        json.dumps(
            {
                "generated_at": GENERATED_AT,
                "notifications": [
                    _record_payload(
                        thread_id="ctx-1",
                        repository="org/repo-a",
                        reason="mention",
                        score=10.0,
                        context={
                            "github": {
                                "latest_comment": {"is_ci_only": True},
                                "pr_state": {"state": "open", "draft": False},
                            }
                        },
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    response = configured_client.get("/api/notifications/primary/ctx-1/rule-snippets?dashboard=triage")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["has_context"] is True
    assert "context:" in payload["dashboard_ignore_rule_with_context_snippet"]
    assert "github.latest_comment.is_ci_only" in payload["dashboard_ignore_rule_with_context_snippet"]
    assert "context:" in payload["global_exclude_rule_with_context_snippet"]


def test_rule_snippets_endpoint_unknown_thread_returns_404(populated_client: TestClient) -> None:
    response = populated_client.get("/api/notifications/primary/missing/rule-snippets?dashboard=overview")

    assert response.status_code == HTTPStatus.NOT_FOUND


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
    monkeypatch.setattr("corvix.web.app.get_env_value", _raise_bad_env)

    response = configured_client.post("/api/notifications/123/dismiss")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_mark_read_without_token_returns_500(
    configured_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    response = configured_client.post("/api/notifications/123/mark-read")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_mark_read_success(configured_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr(
        "corvix.web.app.GitHubNotificationsClient.mark_thread_read",
        lambda _self, thread_id: calls.append(thread_id),
    )

    response = configured_client.post("/api/notifications/abc123/mark-read")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert calls == ["abc123"]


def test_mark_read_updates_cache_unread_state(configured_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = Path(os.environ["CORVIX_CONFIG"])
    cache_file = load_config(config_path).resolve_cache_file()
    cache_file.write_text(
        json.dumps(
            {
                "generated_at": GENERATED_AT,
                "notifications": [_record_payload(thread_id="1", repository="org/repo-a", reason="mention", score=1.0)],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setattr("corvix.web.app.GitHubNotificationsClient.mark_thread_read", lambda *_args: None)

    response = configured_client.post("/api/notifications/1/mark-read")
    assert response.status_code == HTTPStatus.NO_CONTENT

    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    notifications = payload["notifications"]
    assert len(notifications) == 1
    assert notifications[0]["thread_id"] == "1"
    assert notifications[0]["unread"] is False


def test_mark_read_github_error_returns_502(configured_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("corvix.web.app.GitHubNotificationsClient.mark_thread_read", _raise)

    response = configured_client.post("/api/notifications/123/mark-read")

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert "Failed to mark thread" in response.text
    assert "boom" not in response.text


def test_mark_read_token_env_error_returns_500(
    configured_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("corvix.web.app.get_env_value", _raise_bad_env)

    response = configured_client.post("/api/notifications/123/mark-read")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_load_runtime_config_invalid_yaml(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text("github: [\n", encoding="utf-8")
    monkeypatch.setenv("CORVIX_CONFIG", str(bad_config))

    response = client.get("/api/dashboards")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
