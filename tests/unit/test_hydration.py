"""Tests for hydration engine and providers."""

from __future__ import annotations

from datetime import UTC, datetime

from corvix.domain import Notification
from corvix.hydration.engine import HydrationEngine
from corvix.hydration.providers.github_thread_subject import GitHubThreadSubjectProvider
from corvix.hydration.providers.github_web_url import GitHubWebUrlProvider, map_subject_api_url_to_web
from corvix.pipeline.base import JsonFetchClient
from corvix.types import JsonValue


def _notification(
    *,
    thread_id: str = "1",
    subject_type: str = "PullRequest",
    subject_url: str | None = "https://api.example.com/repos/org/repo/pulls/1",
    web_url: str | None = None,
) -> Notification:
    return Notification(
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title="Test",
        subject_type=subject_type,
        unread=True,
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        thread_url=f"https://api.example.com/notifications/threads/{thread_id}",
        subject_url=subject_url,
        web_url=web_url,
        repository_url="https://github.com/org/repo",
    )


class _FakeClient(JsonFetchClient):
    def __init__(self, responses: dict[str, JsonValue]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        del timeout_seconds
        self.calls.append(url)
        return self.responses[url]


def test_map_subject_api_url_to_web_maps_pull_request() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/pulls/42",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/pull/42"


def test_map_subject_api_url_to_web_mismatched_repo_returns_none() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/other/repo/issues/7",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result is None


def test_map_subject_api_url_to_web_maps_issue() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/issues/9",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/issues/9"


def test_map_subject_api_url_to_web_maps_commit() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/commits/deadbeef",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/commit/deadbeef"


def test_map_subject_api_url_to_web_maps_compare() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/compare/base...head",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/compare/base...head"


def test_map_subject_api_url_to_web_maps_discussion() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/discussions/123",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/discussions/123"


def test_map_subject_api_url_to_web_maps_release_tag() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/releases/tags/v1.2.3",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/releases/tag/v1.2.3"


def test_map_subject_api_url_to_web_maps_actions_run() -> None:
    result = map_subject_api_url_to_web(
        subject_url="https://api.github.com/repos/org/repo/actions/runs/777",
        repo_name="org/repo",
        repo_base="https://github.com/org/repo",
    )
    assert result == "https://github.com/org/repo/actions/runs/777"


def test_hydration_uses_repository_url_for_direct_mapping() -> None:
    notification = _notification(
        subject_type="Issue",
        subject_url="https://ghe.example.com/api/v3/repos/org/repo/issues/7",
        web_url=None,
    )
    notification.repository_url = "https://ghe.example.com/org/repo"
    engine = HydrationEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=_FakeClient(responses={}))

    assert notification.web_url == "https://ghe.example.com/org/repo/issues/7"


def test_hydration_thread_subject_then_check_suite_web_url() -> None:
    notification = _notification(thread_id="99", subject_type="CheckSuite", subject_url=None, web_url=None)
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/99": {
                "subject": {"url": "https://api.example.com/repos/org/repo/check-suites/555"}
            },
            "https://api.example.com/repos/org/repo/check-suites/555/check-runs?per_page=1": {
                "check_runs": [{"html_url": "https://github.com/org/repo/actions/runs/777/job/1"}]
            },
        }
    )
    engine = HydrationEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.subject_url == "https://api.example.com/repos/org/repo/check-suites/555"
    assert notification.web_url == "https://github.com/org/repo/actions/runs/777/job/1"


def test_hydration_release_web_url_from_api_payload() -> None:
    notification = _notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/123",
        web_url=None,
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/repos/org/repo/releases/123": {
                "html_url": "https://github.com/org/repo/releases/tag/v1.2.3"
            }
        }
    )
    engine = HydrationEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=client)

    assert notification.web_url == "https://github.com/org/repo/releases/tag/v1.2.3"


def test_hydration_check_suite_enterprise_prefix() -> None:
    notification = _notification(
        thread_id="55",
        subject_type="CheckSuite",
        subject_url="https://ghe.example.com/api/v3/repos/org/repo/check-suites/555",
        web_url=None,
    )
    client = _FakeClient(
        responses={
            "https://ghe.example.com/api/v3/repos/org/repo/check-suites/555/check-runs?per_page=1": {
                "check_runs": [{"html_url": "https://ghe.example.com/org/repo/actions/runs/777/job/1"}]
            }
        }
    )
    engine = HydrationEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=client)

    assert notification.web_url == "https://ghe.example.com/org/repo/actions/runs/777/job/1"


def test_hydration_release_enterprise_prefix() -> None:
    notification = _notification(
        subject_type="Release",
        subject_url="https://ghe.example.com/api/v3/repos/org/repo/releases/123",
        web_url=None,
    )
    client = _FakeClient(
        responses={
            "https://ghe.example.com/api/v3/repos/org/repo/releases/123": {
                "html_url": "https://ghe.example.com/org/repo/releases/tag/v1.2.3"
            }
        }
    )
    engine = HydrationEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=client)

    assert notification.web_url == "https://ghe.example.com/org/repo/releases/tag/v1.2.3"


def test_hydration_fails_open_for_malformed_thread_payload() -> None:
    notification = _notification(thread_id="7", subject_type="CheckSuite", subject_url=None, web_url=None)
    client = _FakeClient(responses={"https://api.example.com/notifications/threads/7": []})
    engine = HydrationEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.subject_url is None
    assert notification.web_url is None


def test_hydration_check_suite_without_subject_url_resolves_exact_run() -> None:
    notification = _notification(thread_id="99", subject_type="CheckSuite", subject_url=None, web_url=None)
    notification.subject_title = "Docs workflow run failed for ci_activities branch"
    notification.updated_at = datetime(2026, 5, 17, 14, 9, 26, tzinfo=UTC)
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/99": {"subject": {"url": None}},
            "https://api.github.com/repos/org/repo/actions/runs?branch=ci_activities&per_page=25": {
                "workflow_runs": [
                    {
                        "name": "Docs",
                        "run_attempt": 1,
                        "updated_at": "2026-05-17T14:09:22Z",
                        "html_url": "https://github.com/org/repo/actions/runs/123",
                    },
                    {
                        "name": "Docs",
                        "run_attempt": 1,
                        "updated_at": "2026-05-17T14:39:22Z",
                        "html_url": "https://github.com/org/repo/actions/runs/124",
                    },
                ]
            },
        }
    )
    engine = HydrationEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.subject_url is None
    assert notification.web_url == "https://github.com/org/repo/actions/runs/123"


def test_hydration_check_suite_without_subject_url_falls_back_to_branch_page() -> None:
    notification = _notification(thread_id="77", subject_type="CheckSuite", subject_url=None, web_url=None)
    notification.subject_title = "pytest workflow run failed for feature/no-filters-dashboard branch"
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/77": {"subject": {"url": None}},
            "https://api.github.com/repos/org/repo/actions/runs?branch=feature%2Fno-filters-dashboard&per_page=25": {
                "workflow_runs": []
            },
        }
    )
    engine = HydrationEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.web_url == "https://github.com/org/repo/actions?query=branch%3Afeature%2Fno-filters-dashboard"


def test_hydration_check_suite_attempt_title_matches_run_attempt() -> None:
    notification = _notification(thread_id="55", subject_type="CheckSuite", subject_url=None, web_url=None)
    notification.subject_title = "test repo/hooks workflow run, Attempt #4 failed for task/OSS-1123 branch"
    notification.updated_at = datetime(2026, 5, 15, 8, 44, 7, tzinfo=UTC)
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/55": {"subject": {"url": None}},
            "https://api.github.com/repos/org/repo/actions/runs?branch=task%2FOSS-1123&per_page=25": {
                "workflow_runs": [
                    {
                        "name": "test repo/hooks",
                        "run_attempt": 1,
                        "updated_at": "2026-05-15T08:11:00Z",
                        "html_url": "https://github.com/org/repo/actions/runs/111",
                    },
                    {
                        "name": "test repo/hooks",
                        "run_attempt": 4,
                        "updated_at": "2026-05-15T08:43:44Z",
                        "html_url": "https://github.com/org/repo/actions/runs/222",
                    },
                ]
            },
        }
    )
    engine = HydrationEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.web_url == "https://github.com/org/repo/actions/runs/222"
