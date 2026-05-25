"""GitHub notifications ingestion client."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from urllib import error as url_error
from urllib import parse, request

from corvix.config import PollingConfig
from corvix.domain import Notification
from corvix.types import JsonObject, JsonValue

logger = logging.getLogger(__name__)
REQUEST_FAILED_DETAIL = "request failed"

# GitHub notification thread IDs are positive integers.
_THREAD_ID_RE = re.compile(r"^[1-9]\d*$")


def _as_json_object(value: JsonValue) -> JsonObject | None:
    """Return value as a JSON object when it is a dict."""
    if not isinstance(value, dict):
        return None
    return value


def _validate_thread_id(thread_id: str) -> None:
    """Raise ValueError if *thread_id* is not a valid GitHub notification thread ID.

    GitHub thread IDs are positive decimal integers.  Rejecting anything that
    does not match prevents path-traversal sequences such as ``../`` from being
    embedded in the URL path constructed by callers.
    """
    if not _THREAD_ID_RE.fullmatch(thread_id):
        msg = f"Invalid thread_id {thread_id!r}: must be a positive integer string."
        raise ValueError(msg)


def _coerce_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
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


@dataclass(slots=True)
class GitHubNotificationsClient:
    """Client for GitHub notifications API."""

    token: str
    api_base_url: str = "https://api.github.com"
    account_id: str = "primary"
    account_label: str = "Primary"
    request_timeout_seconds: float = 30.0

    def fetch_notifications(self, polling: PollingConfig) -> list[Notification]:
        """Fetch notifications with pagination."""
        notifications: list[Notification] = []
        page = 1
        while page <= polling.max_pages:
            raw = self._fetch_page(
                polling=polling,
                page=page,
                timeout_seconds=polling.request_timeout_seconds,
            )
            if not raw:
                break
            notifications.extend(
                Notification.from_api_payload(
                    payload,
                    account_id=self.account_id,
                    account_label=self.account_label,
                )
                for payload in raw
            )
            page += 1
        return notifications

    def _fetch_page(self, polling: PollingConfig, page: int, timeout_seconds: float) -> list[JsonObject]:
        query = {
            "all": str(polling.all).lower(),
            "participating": str(polling.participating).lower(),
            "per_page": str(polling.per_page),
            "page": str(page),
        }
        url = self._build_url("/notifications", query)
        payload = self._request_json(url, method="GET", timeout_seconds=timeout_seconds)
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
        _validate_thread_id(thread_id)
        url = self._build_url(f"/notifications/threads/{thread_id}", {})
        self._request_no_content(url, method="PATCH")

    def dismiss_thread(self, thread_id: str) -> None:
        """Dismiss a notification thread (removes it from inbox permanently)."""
        _validate_thread_id(thread_id)
        url = self._build_url(f"/notifications/threads/{thread_id}", {})
        self._request_no_content_with_backoff(url, method="DELETE")

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        """Fetch JSON from a fully-qualified API URL with host validation."""
        safe_url = self._sanitize_api_url(url)
        return self._request_json(safe_url, method="GET", timeout_seconds=timeout_seconds)

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

    def _request_json(self, url: str, method: str, timeout_seconds: float | None = None) -> JsonValue:
        req = request.Request(url=url, method=method, headers=self._headers())  # NOSONAR python:S5144
        effective_timeout = self.request_timeout_seconds if timeout_seconds is None else timeout_seconds

        # nosec B310 - url is always constructed from self.api_base_url (trusted config) or
        # sanitised by _sanitize_api_url which enforces matching host and trusted scheme.
        with request.urlopen(req, timeout=effective_timeout) as response:  # nosec B310  # NOSONAR python:S5144
            raw = response.read().decode("utf-8")
        return _coerce_json_value(json.loads(raw))

    def _request_no_content(self, url: str, method: str, timeout_seconds: float | None = None) -> None:
        req = request.Request(url=url, method=method, headers=self._headers(), data=b"")  # NOSONAR python:S5144
        effective_timeout = self.request_timeout_seconds if timeout_seconds is None else timeout_seconds

        # nosec B310 - url always originates from _build_url (self.api_base_url) after thread-id
        # validation; no external data can reach this call without passing _validate_thread_id.
        with request.urlopen(req, timeout=effective_timeout):  # nosec B310  # NOSONAR python:S5144
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

    def _sanitize_api_url(self, url: str) -> str:
        """Validate ``url`` and return a safe reconstruction using the trusted base host.

        Reconstructs the URL with the scheme and netloc from ``self.api_base_url``
        so that only the path and query from the input survive into the request.
        This neutralises SSRF via scheme injection or host-header manipulation
        while still allowing the caller to supply the full API path.
        """
        parsed = parse.urlparse(url)
        base = parse.urlparse(self.api_base_url)
        expected_host = base.hostname
        actual_host = parsed.hostname
        if not expected_host or not actual_host or actual_host.casefold() != expected_host.casefold():
            msg = "URL host must match configured GitHub API base host."
            raise ValueError(msg)
        # Reconstruct with trusted scheme + netloc; keep only path and query from input.
        return parse.urlunparse((base.scheme, base.netloc, parsed.path, "", parsed.query, ""))


def _http_error_detail(error: url_error.HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except Exception:
        return error.reason if isinstance(error.reason, str) else REQUEST_FAILED_DETAIL
    if not isinstance(payload, dict):
        return error.reason if isinstance(error.reason, str) else REQUEST_FAILED_DETAIL
    message = payload.get("message")
    if not isinstance(message, str) or not message:
        return error.reason if isinstance(error.reason, str) else REQUEST_FAILED_DETAIL
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
