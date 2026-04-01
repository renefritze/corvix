"""Tests for GitHubNotificationsClient."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from corvix.config import PollingConfig
from corvix.ingestion import GitHubNotificationsClient


def _client() -> GitHubNotificationsClient:
    return GitHubNotificationsClient(token="test-token", api_base_url="https://api.example.com")


def _polling(max_pages: int = 5) -> PollingConfig:
    return PollingConfig(interval_seconds=300, per_page=50, max_pages=max_pages, all=False, participating=False)


def _notification_payload(thread_id: str = "1") -> dict[str, object]:
    return {
        "id": thread_id,
        "updated_at": "2024-01-15T12:30:00Z",
        "reason": "mention",
        "unread": True,
        "url": f"https://api.github.com/notifications/threads/{thread_id}",
        "subject": {
            "title": "Fix the bug",
            "type": "PullRequest",
            "url": "https://api.github.com/repos/org/repo/pulls/42",
        },
        "repository": {
            "full_name": "org/repo",
            "html_url": "https://github.com/org/repo",
        },
    }


def test_fetch_notifications_single_page() -> None:
    client = _client()
    payloads = [_notification_payload("1"), _notification_payload("2")]
    with patch.object(GitHubNotificationsClient, "_request_json", side_effect=[payloads, []]):
        notifications = client.fetch_notifications(_polling())
    assert len(notifications) == 2
    assert notifications[0].thread_id == "1"
    assert notifications[1].thread_id == "2"


def test_fetch_notifications_pagination() -> None:
    client = _client()
    page1 = [_notification_payload("1")]
    page2 = [_notification_payload("2")]
    with patch.object(GitHubNotificationsClient, "_request_json", side_effect=[page1, page2, []]):
        notifications = client.fetch_notifications(_polling(max_pages=5))
    assert len(notifications) == 2


def test_fetch_notifications_max_pages_limit() -> None:
    client = _client()
    with patch.object(
        GitHubNotificationsClient, "_request_json", return_value=[_notification_payload("1")]
    ) as mock_req:
        notifications = client.fetch_notifications(_polling(max_pages=1))
    assert len(notifications) == 1
    assert mock_req.call_count == 1


def test_fetch_page_non_list_raises() -> None:
    client = _client()
    with patch.object(GitHubNotificationsClient, "_request_json", return_value={"unexpected": "dict"}):
        with pytest.raises(ValueError, match="unexpected notifications payload"):
            client.fetch_notifications(_polling())


def test_fetch_page_filters_non_dict_items() -> None:
    client = _client()
    mixed: list[object] = [_notification_payload("1"), "garbage", 42]
    with patch.object(GitHubNotificationsClient, "_request_json", side_effect=[mixed, []]):
        notifications = client.fetch_notifications(_polling())
    assert len(notifications) == 1
    assert notifications[0].thread_id == "1"


def test_mark_thread_read_calls_patch() -> None:
    client = _client()
    with patch.object(GitHubNotificationsClient, "_request_no_content") as mock_req:
        client.mark_thread_read("456")
    mock_req.assert_called_once()
    url = mock_req.call_args[0][0]
    method = mock_req.call_args.kwargs["method"]
    assert "threads/456" in url
    assert method == "PATCH"


def test_dismiss_thread_calls_delete() -> None:
    client = _client()
    with patch.object(GitHubNotificationsClient, "_request_no_content") as mock_req:
        client.dismiss_thread("789")
    mock_req.assert_called_once()
    url = mock_req.call_args[0][0]
    method = mock_req.call_args.kwargs["method"]
    assert "threads/789" in url
    assert method == "DELETE"


def test_build_url_with_query() -> None:
    client = _client()
    url = client._build_url("/notifications", {"page": "1", "per_page": "50"})
    assert url.startswith("https://api.example.com/notifications?")
    assert "page=1" in url
    assert "per_page=50" in url


def test_build_url_without_query() -> None:
    client = _client()
    url = client._build_url("/notifications", {})
    assert url == "https://api.example.com/notifications"
    assert "?" not in url


def test_headers_contain_bearer_token() -> None:
    client = _client()
    headers = client._headers()
    assert headers["Authorization"] == "Bearer test-token"


def test_fetch_json_url_calls_request_json_with_timeout() -> None:
    client = _client()
    target_url = "https://api.example.com/repos/org/repo/issues/1"
    with patch.object(GitHubNotificationsClient, "_request_json", return_value={"ok": True}) as mock_req:
        payload = client.fetch_json_url(target_url, timeout_seconds=5.5)
    assert payload == {"ok": True}
    mock_req.assert_called_once_with(target_url, method="GET", timeout_seconds=5.5)


def test_fetch_json_url_rejects_non_api_host() -> None:
    client = _client()
    with pytest.raises(ValueError, match="base host"):
        client.fetch_json_url("https://evil.example.net/repos/org/repo/issues/1")
