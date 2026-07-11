"""Hydration provider for deriving browser URLs from GitHub notification subjects."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import TypeIs
from urllib.parse import ParseResult, quote, urlparse

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.provider import PipelineContext

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
_CHECK_SUITE_TITLE_RE = re.compile(
    r"^(?P<workflow>(?:(?! workflow run).)+) workflow run"
    r"(?:, Attempt #(?P<attempt>\d+))?"
    r" (?P<state>(?:(?! for ).)+) for (?P<branch>(?:(?! branch$).)+) branch$"
)


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

    def hydrate(self, notification: Notification, client: JsonFetchClient, ctx: PipelineContext) -> Notification:
        if notification.web_url is not None:
            return notification
        repo_base = notification.repository_url or f"https://github.com/{notification.repository}"
        if notification.subject_url:
            direct_url = map_subject_api_url_to_web(
                subject_url=notification.subject_url,
                repo_name=notification.repository,
                repo_base=repo_base,
            )
            if direct_url is not None:
                return replace(notification, web_url=direct_url)
        if notification.subject_type == "CheckSuite":
            web_url = self._resolve_check_suite(
                client=client,
                ctx=ctx,
                notification=notification,
                repo_base=repo_base,
            )
            return replace(notification, web_url=web_url) if web_url is not None else notification
        if notification.subject_type == "Release" and notification.subject_url:
            web_url = self._resolve_release(client=client, ctx=ctx, subject_url=notification.subject_url)
            return replace(notification, web_url=web_url) if web_url is not None else notification
        return notification

    def _resolve_check_suite(
        self,
        client: JsonFetchClient,
        ctx: PipelineContext,
        notification: Notification,
        repo_base: str,
    ) -> str | None:
        resolved_url: str | None = None
        if notification.subject_url:
            try:
                url_from_subject = self._resolve_check_suite_from_subject_url(
                    client=client,
                    ctx=ctx,
                    subject_url=notification.subject_url,
                    repository=notification.repository,
                )
            except Exception:
                url_from_subject = None
            if url_from_subject is not None:
                resolved_url = url_from_subject

        if resolved_url is None:
            parsed_title = _parse_check_suite_title(notification.subject_title)
            if parsed_title is not None:
                fallback_url = _build_actions_branch_url(repo_base=repo_base, branch=parsed_title.branch)
                # Use client.api_base_url (trusted config) rather than parsing repo_base
                # (external API data) to avoid an SSRF taint flow through the netloc component.
                api_base = client.api_base_url.rstrip("/")
                runs_url = (
                    f"{api_base}/repos/{notification.repository}/actions/runs"
                    f"?branch={quote(parsed_title.branch, safe='')}&per_page=25"
                )
                try:
                    payload = ctx.get_json(client=client, url=runs_url, timeout_seconds=self.timeout_seconds)
                except RuntimeError:
                    resolved_url = fallback_url
                else:
                    if _is_str_object_map(payload):
                        workflow_runs = payload.get("workflow_runs")
                        if isinstance(workflow_runs, list):
                            candidate = _match_check_suite_run(
                                workflow_runs=workflow_runs,
                                workflow_name=parsed_title.workflow,
                                run_attempt=parsed_title.attempt,
                                target_timestamp=notification.updated_at,
                            )
                            if candidate is not None:
                                html_url = candidate.get("html_url")
                                if isinstance(html_url, str):
                                    resolved_url = html_url
                    if resolved_url is None:
                        resolved_url = fallback_url

        return resolved_url

    def _resolve_check_suite_from_subject_url(
        self,
        client: JsonFetchClient,
        ctx: PipelineContext,
        subject_url: str,
        repository: str,
    ) -> str | None:
        _, segments, repos_index = _parse_github_api_path(subject_url)
        if repos_index < 0 or len(segments) < repos_index + 5 or segments[repos_index + 3] != "check-suites":
            return None
        check_suite_id = segments[repos_index + 4]
        # Validate check_suite_id is a positive integer to prevent path injection.
        if not re.fullmatch(r"[1-9]\d*", check_suite_id):
            return None
        # Build the check-runs URL from client.api_base_url (trusted config), not from
        # parsed.scheme / parsed.netloc of the external subject_url, to avoid SSRF.
        # The enterprise path prefix (e.g. /api/v3) is already part of api_base_url.
        base = client.api_base_url.rstrip("/")
        check_runs_url = f"{base}/repos/{repository}/check-suites/{check_suite_id}/check-runs?per_page=1"
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

    def _resolve_release(self, client: JsonFetchClient, ctx: PipelineContext, subject_url: str) -> str | None:
        _, segments, repos_index = _parse_github_api_path(subject_url)
        if repos_index < 0 or len(segments) < repos_index + 5 or segments[repos_index + 3] != "releases":
            return None
        payload = ctx.get_json(client=client, url=subject_url, timeout_seconds=self.timeout_seconds)
        if not _is_str_object_map(payload):
            return None
        html_url = payload.get("html_url")
        return html_url if isinstance(html_url, str) else None


@dataclass(slots=True)
class _ParsedCheckSuiteTitle:
    workflow: str
    branch: str
    attempt: int | None


def _parse_check_suite_title(title: str) -> _ParsedCheckSuiteTitle | None:
    match = _CHECK_SUITE_TITLE_RE.match(title)
    if match is None:
        return None
    workflow = match.group("workflow")
    branch = match.group("branch")
    raw_attempt = match.group("attempt")
    attempt = int(raw_attempt) if raw_attempt is not None else None
    return _ParsedCheckSuiteTitle(workflow=workflow, branch=branch, attempt=attempt)


def _build_actions_branch_url(repo_base: str, branch: str) -> str:
    return f"{repo_base}/actions?query={quote(f'branch:{branch}', safe='')}"


def _build_actions_api_base(repo_base: str) -> str:
    # NOTE: This function is kept for reference/testing but is no longer called in
    # production code; _resolve_check_suite now uses client.api_base_url (trusted
    # config) instead to eliminate the SSRF taint via parsed.netloc.
    parsed = urlparse(repo_base)
    if parsed.netloc == "github.com":
        return "https://api.github.com"
    return f"https://{parsed.netloc}/api/v3"  # NOSONAR python:S5144 - tested helper, not called in production paths


def _match_check_suite_run(
    workflow_runs: list[object],
    workflow_name: str,
    run_attempt: int | None,
    target_timestamp: datetime,
) -> dict[str, object] | None:
    normalized_name = workflow_name.casefold()
    candidates: list[dict[str, object]] = []
    for run in workflow_runs:
        if not _is_str_object_map(run):
            continue
        name = run.get("name")
        path = run.get("path")
        if not (
            (isinstance(name, str) and name.casefold() == normalized_name)
            or (isinstance(path, str) and path.casefold() == normalized_name)
        ):
            continue
        if run_attempt is not None:
            current_attempt = run.get("run_attempt")
            if not isinstance(current_attempt, int) or current_attempt != run_attempt:
                continue
        candidates.append(run)
    if not candidates:
        return None

    def _distance_seconds(run: dict[str, object]) -> float:
        updated_raw = run.get("updated_at")
        created_raw = run.get("created_at")
        for raw in (updated_raw, created_raw):
            if isinstance(raw, str):
                timestamp = _parse_github_timestamp(raw)
                if timestamp is not None:
                    return abs((timestamp - target_timestamp).total_seconds())
        return float("inf")

    return min(candidates, key=_distance_seconds)


def _parse_github_timestamp(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


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
