"""GitHub notifications ingestion client."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib import error as url_error
from urllib import parse, request
from urllib.parse import urlparse

from corvix.config import PollingConfig
from corvix.domain import Notification
from corvix.types import JsonObject, JsonValue

logger = logging.getLogger(__name__)

_ENRICHABLE_SUBJECT_TYPES: frozenset[str] = frozenset({"CheckSuite", "Release"})
_CHECK_SUITE_PATH_SEGMENTS = 5
_RELEASE_PATH_SEGMENTS = 5


def _as_json_object(value: JsonValue) -> JsonObject | None:
    """Return value as a JSON object when it is a dict."""
    if not isinstance(value, dict):
        return None
    return value


def _coerce_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_coerce_json_value(item) for item in value]
    if isinstance(value, dict):
        output: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                msg = "JSON object contains a non-string key."
                raise ValueError(msg)
            output[key] = _coerce_json_value(item)
        return output
    msg = "Unsupported JSON value type."
    raise ValueError(msg)


@runtime_checkable
class WebUrlEnricher(Protocol):
    """Resolve web URLs for notifications where the fast path returned None."""

    def enrich_web_url(self, notification: Notification) -> str | None:
        """Return a browser URL for the notification, or None if unresolvable."""
        ...


def resolve_web_urls(
    notifications: list[Notification],
    enricher: WebUrlEnricher | None = None,
) -> None:
    """Enrich web_url in-place for notifications where the fast path returned None."""
    if enricher is None:
        return
    for notification in notifications:
        if (
            notification.web_url is None
            and notification.subject_url is not None
            and notification.subject_type in _ENRICHABLE_SUBJECT_TYPES
        ):
            notification.web_url = enricher.enrich_web_url(notification)


@dataclass(slots=True)
class GitHubNotificationsClient:
    """Client for GitHub notifications API."""

    token: str
    api_base_url: str = "https://api.github.com"

    def fetch_notifications(self, polling: PollingConfig) -> list[Notification]:
        """Fetch notifications with pagination."""
        notifications: list[Notification] = []
        page = 1
        while page <= polling.max_pages:
            raw = self._fetch_page(polling=polling, page=page)
            if not raw:
                break
            notifications.extend(Notification.from_api_payload(payload) for payload in raw)
            page += 1
        return notifications

    def _fetch_page(self, polling: PollingConfig, page: int) -> list[JsonObject]:
        query = {
            "all": str(polling.all).lower(),
            "participating": str(polling.participating).lower(),
            "per_page": str(polling.per_page),
            "page": str(page),
        }
        url = self._build_url("/notifications", query)
        payload = self._request_json(url, method="GET")
        if not isinstance(payload, list):
            msg = "GitHub API returned unexpected notifications payload."
            raise ValueError(msg)
        output: list[JsonObject] = []
        for item in payload:
            item_object = _as_json_object(item)
            if item_object is not None:
                output.append(item_object)
        return output

    def mark_thread_read(self, thread_id: str) -> None:
        """Mark a notification thread as read."""
        url = self._build_url(f"/notifications/threads/{thread_id}", {})
        self._request_no_content(url, method="PATCH")

    def dismiss_thread(self, thread_id: str) -> None:
        """Dismiss a notification thread (removes it from inbox permanently)."""
        url = self._build_url(f"/notifications/threads/{thread_id}", {})
        self._request_no_content_with_backoff(url, method="DELETE")

    def enrich_web_url(self, notification: Notification) -> str | None:
        """Resolve a browser URL via API for notification types the fast path cannot handle."""
        if notification.subject_type == "CheckSuite" and notification.subject_url:
            return self._resolve_check_suite(notification.subject_url, notification.repository)
        if notification.subject_type == "Release" and notification.subject_url:
            return self._resolve_release(notification.subject_url)
        return None

    def _resolve_check_suite(self, subject_url: str, repository: str) -> str | None:
        parsed = urlparse(subject_url)
        segments = [s for s in parsed.path.split("/") if s]
        # Expected: ["repos", owner, repo, "check-suites", id]
        if len(segments) < _CHECK_SUITE_PATH_SEGMENTS or segments[3] != "check-suites":
            return None
        check_suite_id = segments[4]
        api_path = f"/repos/{repository}/check-suites/{check_suite_id}/check-runs"
        url = self._build_url(api_path, {"per_page": "1"})
        try:
            payload = self._request_json(url, method="GET")
        except Exception:
            logger.debug("Failed to fetch check-runs for check-suite %s", check_suite_id)
            return None
        if not isinstance(payload, dict):
            return None
        check_runs = payload.get("check_runs")
        if isinstance(check_runs, list) and check_runs:
            first = _as_json_object(check_runs[0])
            if first is not None:
                html_url = first.get("html_url")
                if isinstance(html_url, str):
                    return html_url
        return None

    def _resolve_release(self, subject_url: str) -> str | None:
        parsed = urlparse(subject_url)
        segments = [s for s in parsed.path.split("/") if s]
        # Expected: ["repos", owner, repo, "releases", id]
        if len(segments) < _RELEASE_PATH_SEGMENTS or segments[3] != "releases":
            return None
        try:
            self._validate_api_host(subject_url)
            payload = self._request_json(subject_url, method="GET")
        except Exception:
            logger.debug("Failed to fetch release metadata from %s", subject_url)
            return None
        payload_object = _as_json_object(payload)
        if payload_object is None:
            return None
        html_url = payload_object.get("html_url")
        if isinstance(html_url, str):
            return html_url
        return None

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        """Fetch JSON from a fully-qualified API URL with host validation."""
        self._validate_api_host(url)
        return self._request_json(url, method="GET", timeout_seconds=timeout_seconds)

    def _build_url(self, path: str, query: dict[str, str]) -> str:
        base = self.api_base_url.rstrip("/")
        encoded_query = parse.urlencode(query)
        return f"{base}{path}?{encoded_query}" if encoded_query else f"{base}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "corvix",
        }

    def _request_json(self, url: str, method: str, timeout_seconds: float = 30.0) -> JsonValue:
        req = request.Request(url=url, method=method, headers=self._headers())

        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        return _coerce_json_value(json.loads(raw))

    def _request_no_content(self, url: str, method: str) -> None:
        req = request.Request(url=url, method=method, headers=self._headers(), data=b"")

        with request.urlopen(req, timeout=30):
            return

    def _request_no_content_with_backoff(self, url: str, method: str, max_attempts: int = 4) -> None:
        """Perform no-content request with retries for GitHub throttling responses."""
        attempt = 1
        while attempt <= max_attempts:
            try:
                self._request_no_content(url, method)
                return
            except url_error.HTTPError as error:
                retryable = error.code in {403, 429}
                if not retryable or attempt >= max_attempts:
                    detail = _http_error_detail(error)
                    msg = f"GitHub API request failed with status {error.code}: {detail}"
                    raise RuntimeError(msg) from error
                delay_seconds = _retry_delay_seconds(error=error, attempt=attempt)
                logger.warning(
                    "GitHub API throttled dismiss request; retrying",
                    extra={"attempt": attempt, "max_attempts": max_attempts, "delay_seconds": delay_seconds},
                )
                time.sleep(delay_seconds)
                attempt += 1

    def _validate_api_host(self, url: str) -> None:
        expected = parse.urlparse(self.api_base_url).hostname
        actual = parse.urlparse(url).hostname
        if not expected or not actual or actual.casefold() != expected.casefold():
            msg = "URL host must match configured GitHub API base host."
            raise ValueError(msg)


def _http_error_detail(error: url_error.HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except Exception:
        return error.reason if isinstance(error.reason, str) else "request failed"
    if not isinstance(payload, dict):
        return error.reason if isinstance(error.reason, str) else "request failed"
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return error.reason if isinstance(error.reason, str) else "request failed"
    return message


def _retry_delay_seconds(error: url_error.HTTPError, attempt: int) -> float:
    retry_after_raw = error.headers.get("Retry-After") if error.headers is not None else None
    if isinstance(retry_after_raw, str):
        try:
            retry_after_seconds = float(retry_after_raw)
        except ValueError:
            retry_after_seconds = 0.0
        if retry_after_seconds > 0:
            return min(retry_after_seconds, 10.0)
    return min(0.5 * (2 ** (attempt - 1)), 5.0)
