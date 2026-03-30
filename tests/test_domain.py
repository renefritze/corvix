"""Tests for notification domain helpers."""

from __future__ import annotations

from corvix.domain import Notification


def test_notification_from_api_payload_derives_pull_request_web_url() -> None:
    payload = {
        "id": "1",
        "reason": "review_requested",
        "unread": True,
        "updated_at": "2026-03-30T10:15:00Z",
        "url": "https://api.github.com/notifications/threads/1",
        "repository": {
            "full_name": "octo/repo",
            "html_url": "https://github.com/octo/repo",
        },
        "subject": {
            "title": "Review this change",
            "type": "PullRequest",
            "url": "https://api.github.com/repos/octo/repo/pulls/42",
        },
    }

    notification = Notification.from_api_payload(payload)

    assert notification.thread_url == "https://api.github.com/notifications/threads/1"
    assert notification.web_url == "https://github.com/octo/repo/pull/42"


def test_notification_from_api_payload_falls_back_to_repository_web_url() -> None:
    payload = {
        "id": "1",
        "reason": "subscribed",
        "unread": True,
        "updated_at": "2026-03-30T10:15:00Z",
        "url": "https://api.github.com/notifications/threads/1",
        "repository": {
            "full_name": "octo/repo",
            "html_url": "https://github.com/octo/repo",
        },
        "subject": {
            "title": "Repository notice",
            "type": "RepositoryVulnerabilityAlert",
            "url": None,
        },
    }

    notification = Notification.from_api_payload(payload)

    assert notification.web_url == "https://github.com/octo/repo"
