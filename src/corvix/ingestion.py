"""GitHub notifications ingestion client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import parse, request

from corvix.config import PollingConfig
from corvix.domain import Notification


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

    def _fetch_page(self, polling: PollingConfig, page: int) -> list[dict[str, Any]]:
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
        output: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                output.append(item)
        return output

    def mark_thread_read(self, thread_id: str) -> None:
        """Mark a notification thread as read."""
        url = self._build_url(f"/notifications/threads/{thread_id}", {})
        self._request_no_content(url, method="PATCH")

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

    def _request_json(self, url: str, method: str) -> object:
        req = request.Request(url=url, method=method, headers=self._headers())

        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw)

    def _request_no_content(self, url: str, method: str) -> None:
        req = request.Request(url=url, method=method, headers=self._headers(), data=b"")

        with request.urlopen(req, timeout=30):
            return
