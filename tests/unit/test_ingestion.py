"""Tests for GitHubNotificationsClient and URL enrichment."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import patch
from urllib import error as url_error
from urllib import request

import pytest

from corvix.config import PollingConfig
from corvix.domain import Notification
from corvix.ingestion import (
    GitHubNotificationsClient,
    _coerce_json_value,
    _http_error_detail,
    _retry_delay_seconds,
    resolve_web_urls,
)


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


def test_fetch_notifications_use_primary_account_defaults() -> None:
    client = _client()
    with patch.object(GitHubNotificationsClient, "_request_json", side_effect=[[_notification_payload("1")], []]):
        notifications = client.fetch_notifications(_polling())

    assert notifications[0].account_id == "primary"
    assert notifications[0].account_label == "Primary"


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
    with patch.object(GitHubNotificationsClient, "_request_no_content_with_backoff") as mock_req:
        client.dismiss_thread("789")
    mock_req.assert_called_once()
    url = mock_req.call_args[0][0]
    method = mock_req.call_args.kwargs["method"]
    assert "threads/789" in url
    assert method == "DELETE"


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


def test_dismiss_thread_surfaces_error_message() -> None:
    client = _client()
    err = url_error.HTTPError(
        url="https://api.example.com/notifications/threads/789",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=io.BytesIO(b'{"message":"You have exceeded a secondary rate limit."}'),
    )
    with (
        patch.object(GitHubNotificationsClient, "_request_no_content", side_effect=err),
        patch("corvix.ingestion.time.sleep"),
    ):
        with pytest.raises(RuntimeError, match="secondary rate limit"):
            client.dismiss_thread("789")


def test_dismiss_thread_non_retryable_error_does_not_retry() -> None:
    client = _client()
    err = url_error.HTTPError(
        url="https://api.example.com/notifications/threads/789",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b"{}"),
    )
    with (
        patch.object(GitHubNotificationsClient, "_request_no_content", side_effect=err) as mock_req,
        patch("corvix.ingestion.time.sleep") as mock_sleep,
    ):
        with pytest.raises(RuntimeError, match="status 404"):
            client.dismiss_thread("789")

    assert mock_req.call_count == 1
    mock_sleep.assert_not_called()


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


def test_coerce_json_value_supports_nested_structures() -> None:
    value = _coerce_json_value({"items": [1, "two", {"ok": True}, None]})

    assert value == {"items": [1, "two", {"ok": True}, None]}


def test_coerce_json_value_rejects_non_string_dict_keys() -> None:
    with pytest.raises(ValueError, match="non-string key"):
        _coerce_json_value({1: "bad"})


def test_coerce_json_value_rejects_unsupported_types() -> None:
    with pytest.raises(ValueError, match="Unsupported JSON value type"):
        _coerce_json_value({"items": {1, 2, 3}})


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
    assert mock_urlopen.call_args.kwargs["timeout"] == 1.5


def test_request_no_content_uses_empty_request_body() -> None:
    client = _client()

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    with patch.object(request, "urlopen", return_value=_Response()) as mock_urlopen:
        client._request_no_content("https://api.example.com/notifications/threads/1", method="PATCH")

    req = mock_urlopen.call_args.args[0]
    assert req.data == b""
    assert req.get_method() == "PATCH"


def test_http_error_detail_falls_back_for_non_json_payload() -> None:
    err = url_error.HTTPError(
        url="https://api.example.com/x",
        code=500,
        msg="boom",
        hdrs={},
        fp=io.BytesIO(b"not json"),
    )

    assert _http_error_detail(err) == "boom"


def test_http_error_detail_falls_back_when_message_is_missing() -> None:
    err = url_error.HTTPError(
        url="https://api.example.com/x",
        code=500,
        msg="boom",
        hdrs={},
        fp=io.BytesIO(b'{"documentation_url":"https://docs.example.com"}'),
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

    assert _retry_delay_seconds(err, attempt=1) == 10.0


def test_retry_delay_seconds_falls_back_for_invalid_retry_after() -> None:
    err = url_error.HTTPError(
        url="https://api.example.com/x",
        code=429,
        msg="boom",
        hdrs={"Retry-After": "soon"},
        fp=io.BytesIO(b"{}"),
    )

    assert _retry_delay_seconds(err, attempt=3) == 2.0


# --- resolve_web_urls ---


def _make_notification(
    subject_type: str = "PullRequest",
    subject_url: str | None = "https://api.github.com/repos/org/repo/pulls/42",
    web_url: str | None = "https://github.com/org/repo/pull/42",
) -> Notification:
    return Notification(
        thread_id="1",
        repository="org/repo",
        reason="mention",
        subject_title="Test",
        subject_type=subject_type,
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        subject_url=subject_url,
        web_url=web_url,
    )


class FakeEnricher:
    """Test double for WebUrlEnricher."""

    def __init__(self, url: str | None = "https://github.com/org/repo/actions/runs/1") -> None:
        self.calls: list[Notification] = []
        self._url = url

    def enrich_web_url(self, notification: Notification) -> str | None:
        self.calls.append(notification)
        return self._url


def test_resolve_web_urls_none_enricher_is_noop() -> None:
    n = _make_notification(subject_type="CheckSuite", web_url=None)
    resolve_web_urls([n], enricher=None)
    assert n.web_url is None


def test_resolve_web_urls_skips_already_resolved() -> None:
    enricher = FakeEnricher()
    n = _make_notification(subject_type="CheckSuite", web_url="https://existing.url")
    resolve_web_urls([n], enricher=enricher)
    assert enricher.calls == []
    assert n.web_url == "https://existing.url"


def test_resolve_web_urls_skips_non_enrichable_type() -> None:
    enricher = FakeEnricher()
    n = _make_notification(subject_type="PullRequest", web_url=None)
    resolve_web_urls([n], enricher=enricher)
    assert enricher.calls == []


def test_resolve_web_urls_skips_missing_subject_url() -> None:
    enricher = FakeEnricher()
    n = _make_notification(subject_type="CheckSuite", subject_url=None, web_url=None)
    resolve_web_urls([n], enricher=enricher)
    assert enricher.calls == []


def test_resolve_web_urls_enriches_check_suite() -> None:
    enricher = FakeEnricher(url="https://github.com/org/repo/actions/runs/777")
    n = _make_notification(
        subject_type="CheckSuite",
        subject_url="https://api.github.com/repos/org/repo/check-suites/555",
        web_url=None,
    )
    resolve_web_urls([n], enricher=enricher)
    assert len(enricher.calls) == 1
    assert n.web_url == "https://github.com/org/repo/actions/runs/777"


def test_resolve_web_urls_enriches_release() -> None:
    enricher = FakeEnricher(url="https://github.com/org/repo/releases/tag/v2.0.0")
    n = _make_notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/12345",
        web_url=None,
    )
    resolve_web_urls([n], enricher=enricher)
    assert len(enricher.calls) == 1
    assert n.web_url == "https://github.com/org/repo/releases/tag/v2.0.0"


# --- enrich_web_url on GitHubNotificationsClient ---


def test_enrich_check_suite_returns_html_url() -> None:
    client = _client()
    n = _make_notification(
        subject_type="CheckSuite",
        subject_url="https://api.github.com/repos/org/repo/check-suites/555",
        web_url=None,
    )
    api_response = {
        "total_count": 1,
        "check_runs": [
            {"html_url": "https://github.com/org/repo/actions/runs/777/job/888"},
        ],
    }
    with patch.object(GitHubNotificationsClient, "_request_json", return_value=api_response):
        result = client.enrich_web_url(n)
    assert result == "https://github.com/org/repo/actions/runs/777/job/888"


def test_enrich_check_suite_no_runs_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="CheckSuite",
        subject_url="https://api.github.com/repos/org/repo/check-suites/555",
        web_url=None,
    )
    with patch.object(GitHubNotificationsClient, "_request_json", return_value={"check_runs": []}):
        result = client.enrich_web_url(n)
    assert result is None


def test_enrich_check_suite_api_error_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="CheckSuite",
        subject_url="https://api.github.com/repos/org/repo/check-suites/555",
        web_url=None,
    )
    with patch.object(GitHubNotificationsClient, "_request_json", side_effect=OSError("timeout")):
        result = client.enrich_web_url(n)
    assert result is None


def test_enrich_non_check_suite_returns_none() -> None:
    client = _client()
    n = _make_notification(subject_type="Issue", web_url=None)
    result = client.enrich_web_url(n)
    assert result is None


def test_enrich_release_returns_html_url() -> None:
    client = _client()
    n = _make_notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/12345",
        web_url=None,
    )
    with patch.object(
        GitHubNotificationsClient,
        "_request_json",
        return_value={"html_url": "https://github.com/org/repo/releases/tag/v2.0.0"},
    ):
        result = client.enrich_web_url(n)
    assert result == "https://github.com/org/repo/releases/tag/v2.0.0"


def test_enrich_release_missing_html_url_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/12345",
        web_url=None,
    )
    with patch.object(GitHubNotificationsClient, "_request_json", return_value={"id": 12345}):
        result = client.enrich_web_url(n)
    assert result is None


def test_enrich_release_non_dict_api_response_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/12345",
        web_url=None,
    )
    with patch.object(GitHubNotificationsClient, "_request_json", return_value=[]):
        result = client.enrich_web_url(n)
    assert result is None


def test_enrich_release_api_error_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/12345",
        web_url=None,
    )
    with patch.object(GitHubNotificationsClient, "_request_json", side_effect=OSError("timeout")):
        result = client.enrich_web_url(n)
    assert result is None


def test_enrich_release_malformed_subject_url_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases",
        web_url=None,
    )
    result = client.enrich_web_url(n)
    assert result is None


def test_enrich_check_suite_malformed_subject_url_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="CheckSuite",
        subject_url="https://api.github.com/repos/org/repo",  # too short, no check-suites segment
        web_url=None,
    )
    result = client.enrich_web_url(n)
    assert result is None


def test_enrich_check_suite_non_dict_api_response_returns_none() -> None:
    client = _client()
    n = _make_notification(
        subject_type="CheckSuite",
        subject_url="https://api.github.com/repos/org/repo/check-suites/555",
        web_url=None,
    )
    with patch.object(GitHubNotificationsClient, "_request_json", return_value=[]):
        result = client.enrich_web_url(n)
    assert result is None


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
