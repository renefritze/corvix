"""Hydration provider for recovering missing subject URLs from thread payloads."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TypeIs

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.provider import PipelineContext


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


@dataclass(slots=True)
class GitHubThreadSubjectProvider:
    """Backfills subject_url from a notification thread payload."""

    timeout_seconds: float = 10.0
    name: str = "github.thread_subject"

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> Notification:
        if notification.subject_url is not None or not notification.thread_url:
            return notification
        payload = ctx.get_json(client=client, url=notification.thread_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(payload):
            return notification
        subject = payload.get("subject")
        if not _is_str_object_map(subject):
            return notification
        subject_url = subject.get("url")
        if isinstance(subject_url, str) and subject_url:
            return replace(notification, subject_url=subject_url)
        return notification
