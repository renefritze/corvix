"""Tests for GitHubNotificationsClient request behavior."""

from __future__ import annotations

import io
from unittest.mock import patch
from urllib import error as url_error
from urllib import request

import pytest

from corvix.config import PollingConfig
from corvix.ingestion import GitHubNotificationsClient, _coerce_json_value, _http_error_detail, _retry_delay_seconds


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


def test_fetch_page_non_list_raises() -> None:
    client = _client()
    with patch.object(GitHubNotificationsClient, "_request_json", return_value={"unexpected": "dict"}):
        with pytest.raises(ValueError, match="unexpected notifications payload"):
            client.fetch_notifications(_polling())


def test_mark_thread_read_calls_patch() -> None:
    client = _client()
    with patch.object(GitHubNotificationsClient, "_request_no_content") as mock_req:
        client.mark_thread_read("456")
    assert "threads/456" in mock_req.call_args[0][0]


def test_dismiss_thread_retries_on_rate_limit() -> None:
    client = _client()
    err = url_error.HTTPError(
        url="https://api.example.com/notifications/threads/789",
        code=429,
        msg="Too Many Requests",
        hdrs={"Retry-After": "0"},
        fp=io.BytesIO(b'{"message":"secondary rate limit"}'),
    )
    with (
        patch.object(GitHubNotificationsClient, "_request_no_content", side_effect=[err, None]) as mock_req,
        patch("corvix.ingestion.time.sleep") as mock_sleep,
    ):
        client.dismiss_thread("789")
    assert mock_req.call_count == 2
    mock_sleep.assert_called_once()


def test_coerce_json_value_supports_nested_structures() -> None:
    value = _coerce_json_value({"items": [1, "two", {"ok": True}, None]})
    assert value == {"items": [1, "two", {"ok": True}, None]}


def test_coerce_json_value_rejects_non_string_dict_keys() -> None:
    with pytest.raises(ValueError, match="non-string key"):
        _coerce_json_value({1: "bad"})


def test_request_json_reads_and_decodes_payload() -> None:
    client = _client()

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    with patch.object(request, "urlopen", return_value=_Response()) as mock_urlopen:
        payload = client._request_json("https://api.example.com/notifications", method="GET", timeout_seconds=1.5)

    assert payload == {"ok": True}
    assert mock_urlopen.call_args.kwargs["timeout"] == pytest.approx(1.5)


def test_request_json_uses_client_default_timeout() -> None:
    client = GitHubNotificationsClient(
        token="test-token", api_base_url="https://api.example.com", request_timeout_seconds=2.5
    )

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    with patch.object(request, "urlopen", return_value=_Response()) as mock_urlopen:
        client._request_json("https://api.example.com/notifications", method="GET")

    assert mock_urlopen.call_args.kwargs["timeout"] == pytest.approx(2.5)


def test_request_no_content_uses_client_default_timeout() -> None:
    client = GitHubNotificationsClient(
        token="test-token", api_base_url="https://api.example.com", request_timeout_seconds=3.5
    )

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    with patch.object(request, "urlopen", return_value=_Response()) as mock_urlopen:
        client._request_no_content("https://api.example.com/notifications/threads/123", method="PATCH")

    assert mock_urlopen.call_args.kwargs["timeout"] == pytest.approx(3.5)


def test_http_error_detail_falls_back_for_non_json_payload() -> None:
    err = url_error.HTTPError(
        url="https://api.example.com/x",
        code=500,
        msg="boom",
        hdrs={},
        fp=io.BytesIO(b"not json"),
    )
    assert _http_error_detail(err) == "boom"


def test_retry_delay_seconds_uses_retry_after_header() -> None:
    err = url_error.HTTPError(
        url="https://api.example.com/x",
        code=429,
        msg="boom",
        hdrs={"Retry-After": "15"},
        fp=io.BytesIO(b"{}"),
    )
    assert _retry_delay_seconds(err, attempt=1) == pytest.approx(10.0)
