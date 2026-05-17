"""Hydration provider for deriving browser URLs from GitHub notification subjects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeIs
from urllib.parse import ParseResult, urlparse

from corvix.domain import Notification
from corvix.hydration.base import HydrationContext
from corvix.pipeline.base import JsonFetchClient

_MIN_API_REPO_SEGMENTS = 4
_MIN_RESOURCE_SEGMENTS = 2
_RELEASE_TAG_SEGMENTS = 3
_ACTIONS_RUNS_SEGMENTS = 3
_API_RESOURCE_TO_WEB_PATH = {
    "pulls": "pull",
    "issues": "issues",
    "commits": "commit",
    "compare": "compare",
    "discussions": "discussions",
}


def _parse_github_api_path(subject_url: str) -> tuple[ParseResult, list[str], int]:
    parsed = urlparse(subject_url)
    segments = [s for s in parsed.path.split("/") if s]
    try:
        repos_index = segments.index("repos")
    except ValueError:
        repos_index = -1
    return parsed, segments, repos_index


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
        parsed, segments, repos_index = _parse_github_api_path(subject_url)
        if repos_index < 0 or len(segments) < repos_index + 5 or segments[repos_index + 3] != "check-suites":
            return None
        check_suite_id = segments[repos_index + 4]
        prefix = segments[:repos_index]
        base_path = f"{'/'.join(prefix)}/" if prefix else ""
        check_runs_url = f"{parsed.scheme}://{parsed.netloc}/{base_path}repos/{repository}/check-suites/{check_suite_id}/check-runs?per_page=1"
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
        _, segments, repos_index = _parse_github_api_path(subject_url)
        if repos_index < 0 or len(segments) < repos_index + 5 or segments[repos_index + 3] != "releases":
            return None
        payload = ctx.get_json(client=client, url=subject_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(payload):
            return None
        html_url = payload.get("html_url")
        return html_url if isinstance(html_url, str) else None


def map_subject_api_url_to_web(subject_url: str, repo_name: str, repo_base: str) -> str | None:
    """Map a subject API URL to its browser URL when possible."""
    _, path_segments, repos_index = _parse_github_api_path(subject_url)
    result: str | None = None
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
