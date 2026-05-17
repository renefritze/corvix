"""Hydration provider for deriving browser URLs from GitHub notification subjects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeIs
from urllib.parse import urlparse

from corvix.domain import Notification
from corvix.hydration.base import HydrationContext
from corvix.pipeline.base import JsonFetchClient

_MIN_API_REPO_SEGMENTS = 4
_MIN_RESOURCE_SEGMENTS = 2
_RELEASE_TAG_SEGMENTS = 3
_ACTIONS_RUNS_SEGMENTS = 3
_CHECK_SUITE_PATH_SEGMENTS = 5
_RELEASE_PATH_SEGMENTS = 5
_API_RESOURCE_TO_WEB_PATH = {
    "pulls": "pull",
    "issues": "issues",
    "commits": "commit",
    "compare": "compare",
    "discussions": "discussions",
}


def _is_str_object_map(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


@dataclass(slots=True)
class GitHubWebUrlProvider:
    """Hydrates notification.web_url with direct and API-based mappings."""

    timeout_seconds: float = 10.0
    name: str = "github.web_url"

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: HydrationContext) -> None:
        if notification.web_url is not None or not notification.subject_url:
            return
        repo_base = notification.repository_url or f"https://github.com/{notification.repository}"
        direct_url = map_subject_api_url_to_web(
            subject_url=notification.subject_url,
            repo_name=notification.repository,
            repo_base=repo_base,
        )
        if direct_url is not None:
            notification.web_url = direct_url
            return
        if notification.subject_type == "CheckSuite":
            notification.web_url = self._resolve_check_suite(
                client=client,
                ctx=ctx,
                subject_url=notification.subject_url,
                repository=notification.repository,
            )
            return
        if notification.subject_type == "Release":
            notification.web_url = self._resolve_release(client=client, ctx=ctx, subject_url=notification.subject_url)

    def _resolve_check_suite(
        self,
        client: JsonFetchClient,
        ctx: HydrationContext,
        subject_url: str,
        repository: str,
    ) -> str | None:
        parsed = urlparse(subject_url)
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) < _CHECK_SUITE_PATH_SEGMENTS or segments[3] != "check-suites":
            return None
        check_suite_id = segments[4]
        check_runs_url = (
            f"{parsed.scheme}://{parsed.netloc}/repos/{repository}/check-suites/{check_suite_id}/check-runs?per_page=1"
        )
        payload = ctx.get_json(client=client, url=check_runs_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(payload):
            return None
        check_runs = payload.get("check_runs")
        if isinstance(check_runs, list) and check_runs:
            first = check_runs[0]
            if _is_str_object_map(first):
                html_url = first.get("html_url")
                if isinstance(html_url, str):
                    return html_url
        return None

    def _resolve_release(self, client: JsonFetchClient, ctx: HydrationContext, subject_url: str) -> str | None:
        parsed = urlparse(subject_url)
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) < _RELEASE_PATH_SEGMENTS or segments[3] != "releases":
            return None
        payload = ctx.get_json(client=client, url=subject_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(payload):
            return None
        html_url = payload.get("html_url")
        return html_url if isinstance(html_url, str) else None


def map_subject_api_url_to_web(subject_url: str, repo_name: str, repo_base: str) -> str | None:
    """Map a subject API URL to its browser URL when possible."""
    parsed = urlparse(subject_url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    result: str | None = None
    try:
        repos_index = path_segments.index("repos")
    except ValueError:
        repos_index = -1
    if len(path_segments) >= repos_index + _MIN_API_REPO_SEGMENTS and repos_index >= 0:
        api_repo_name = "/".join(path_segments[repos_index + 1 : repos_index + 3])
        if api_repo_name == repo_name:
            resource = path_segments[repos_index + 3 :]
            resource_name = resource[0]
            mapped_web_path = _API_RESOURCE_TO_WEB_PATH.get(resource_name)
            if mapped_web_path is not None and len(resource) >= _MIN_RESOURCE_SEGMENTS:
                result = f"{repo_base}/{mapped_web_path}/{resource[1]}"
            elif resource_name == "releases" and len(resource) >= _RELEASE_TAG_SEGMENTS and resource[1] == "tags":
                result = f"{repo_base}/releases/tag/{resource[2]}"
            elif resource_name == "actions" and len(resource) >= _ACTIONS_RUNS_SEGMENTS and resource[1] == "runs":
                result = f"{repo_base}/actions/runs/{resource[2]}"
    return result
