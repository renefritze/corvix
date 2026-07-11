"""Tests for the field-completion providers (thread-subject, web-url) via PipelineEngine."""

from __future__ import annotations

from datetime import UTC, datetime

from corvix.domain import Notification
from corvix.pipeline.base import JsonFetchClient
from corvix.pipeline.engine import PipelineEngine
from corvix.pipeline.providers.github_thread_subject import GitHubThreadSubjectProvider
from corvix.pipeline.providers.github_web_url import (
    GitHubWebUrlProvider,
    _build_actions_api_base,
    _match_check_suite_run,
    _parse_github_api_path,
    _parse_github_timestamp,
    map_subject_api_url_to_web,
)
from corvix.types import JsonValue


def _notification(
    *,
    thread_id: str = "1",
    subject_type: str = "PullRequest",
    subject_url: str | None = "https://api.example.com/repos/org/repo/pulls/1",
    web_url: str | None = None,
    subject_title: str = "Test",
    updated_at: datetime | None = None,
    repository_url: str | None = "https://github.com/org/repo",
) -> Notification:
    return Notification(
        thread_id=thread_id,
        repository="org/repo",
        reason="mention",
        subject_title=subject_title,
        subject_type=subject_type,
        unread=True,
        updated_at=updated_at or datetime(2024, 1, 1, tzinfo=UTC),
        thread_url=f"https://api.example.com/notifications/threads/{thread_id}",
        subject_url=subject_url,
        web_url=web_url,
        repository_url=repository_url,
    )


class _FakeClient(JsonFetchClient):
    def __init__(
        self,
        responses: dict[str, JsonValue],
        api_base_url: str = "https://api.example.com",
        account_id: str = "primary",
    ) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.api_base_url = api_base_url
        self.account_id = account_id

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        del timeout_seconds
        self.calls.append(url)
        return self.responses[url]


class _FakeRaiseClient(JsonFetchClient):
    def __init__(
        self,
        exc: Exception | None = None,
        api_base_url: str = "https://api.example.com",
        account_id: str = "primary",
    ) -> None:
        self.calls: list[str] = []
        self._exc = exc or RuntimeError("simulated failure")
        self.api_base_url = api_base_url
        self.account_id = account_id

    def fetch_json_url(self, url: str, timeout_seconds: float = 30.0) -> JsonValue:
        self.calls.append(url)
        raise self._exc


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
        repository_url="https://ghe.example.com/org/repo",
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=_FakeClient(responses={}))

    assert result.notifications[0].web_url == "https://ghe.example.com/org/repo/issues/7"


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
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert result.notifications[0].subject_url == "https://api.example.com/repos/org/repo/check-suites/555"
    assert result.notifications[0].web_url == "https://github.com/org/repo/actions/runs/777/job/1"


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
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.notifications[0].web_url == "https://github.com/org/repo/releases/tag/v1.2.3"


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
        },
        api_base_url="https://ghe.example.com/api/v3",
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.notifications[0].web_url == "https://ghe.example.com/org/repo/actions/runs/777/job/1"


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
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.notifications[0].web_url == "https://ghe.example.com/org/repo/releases/tag/v1.2.3"


def test_hydration_fails_open_for_malformed_thread_payload() -> None:
    notification = _notification(thread_id="7", subject_type="CheckSuite", subject_url=None, web_url=None)
    client = _FakeClient(responses={"https://api.example.com/notifications/threads/7": []})
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.subject_url is None
    assert notification.web_url is None


def test_hydration_check_suite_without_subject_url_resolves_exact_run() -> None:
    notification = _notification(
        thread_id="99",
        subject_type="CheckSuite",
        subject_url=None,
        web_url=None,
        subject_title="Docs workflow run failed for ci_activities branch",
        updated_at=datetime(2026, 5, 17, 14, 9, 26, tzinfo=UTC),
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/99": {"subject": {"url": None}},
            "https://api.example.com/repos/org/repo/actions/runs?branch=ci_activities&per_page=25": {
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
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert result.notifications[0].subject_url is None
    assert result.notifications[0].web_url == "https://github.com/org/repo/actions/runs/123"


def test_hydration_check_suite_without_subject_url_falls_back_to_branch_page() -> None:
    notification = _notification(
        thread_id="77",
        subject_type="CheckSuite",
        subject_url=None,
        web_url=None,
        subject_title="pytest workflow run failed for feature/no-filters-dashboard branch",
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/77": {"subject": {"url": None}},
            "https://api.example.com/repos/org/repo/actions/runs?branch=feature%2Fno-filters-dashboard&per_page=25": {
                "workflow_runs": []
            },
        }
    )
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert result.notifications[0].web_url == "https://github.com/org/repo/actions?query=branch%3Afeature%2Fno-filters-dashboard"


def test_hydration_check_suite_attempt_title_matches_run_attempt() -> None:
    notification = _notification(
        thread_id="55",
        subject_type="CheckSuite",
        subject_url=None,
        web_url=None,
        subject_title="test repo/hooks workflow run, Attempt #4 failed for task/OSS-1123 branch",
        updated_at=datetime(2026, 5, 15, 8, 44, 7, tzinfo=UTC),
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/55": {"subject": {"url": None}},
            "https://api.example.com/repos/org/repo/actions/runs?branch=task%2FOSS-1123&per_page=25": {
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
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert result.notifications[0].web_url == "https://github.com/org/repo/actions/runs/222"


# -- _parse_github_api_path (line 38-39) --


def test_parse_github_api_path_missing_repos() -> None:
    _parsed, segments, repos_index = _parse_github_api_path("https://api.example.com/notifications/threads/1")
    assert repos_index == -1
    assert "repos" not in segments


# -- _parse_github_timestamp (line 239-240) --


def test_parse_github_timestamp_invalid() -> None:
    assert _parse_github_timestamp("not-a-date") is None


# -- _match_check_suite_run edge cases --


def test_match_check_suite_run_skips_non_dict_entries() -> None:
    runs: list[object] = [
        "not a dict",
        {"name": "target", "updated_at": "2024-01-01T12:00:00Z", "html_url": "https://example.com/run/1"},
    ]
    result = _match_check_suite_run(runs, "target", None, datetime(2024, 1, 1, tzinfo=UTC))
    assert result is not None
    assert result["html_url"] == "https://example.com/run/1"


def test_match_check_suite_run_skips_non_matching_name_and_path() -> None:
    runs: list[object] = [
        {"name": "other", "path": "other", "updated_at": "2024-01-01T12:00:00Z"},
        {"name": "target", "updated_at": "2024-01-01T12:00:00Z", "html_url": "https://example.com/run/1"},
    ]
    result = _match_check_suite_run(runs, "target", None, datetime(2024, 1, 1, tzinfo=UTC))
    assert result is not None
    assert result["html_url"] == "https://example.com/run/1"


def test_match_check_suite_run_by_path_field() -> None:
    runs: list[object] = [
        {"path": "ci/build", "updated_at": "2024-01-01T12:00:00Z", "html_url": "https://example.com/run/path-match"},
    ]
    result = _match_check_suite_run(runs, "ci/build", None, datetime(2024, 1, 1, tzinfo=UTC))
    assert result is not None
    assert result["html_url"] == "https://example.com/run/path-match"


def test_match_check_suite_run_invalid_timestamp_uses_inf() -> None:
    runs: list[object] = [
        {"name": "target", "updated_at": "bad-date", "html_url": "https://example.com/run/bad"},
        {"name": "target", "updated_at": "2024-01-01T12:00:00Z", "html_url": "https://example.com/run/good"},
    ]
    result = _match_check_suite_run(runs, "target", None, datetime(2024, 1, 1, tzinfo=UTC))
    assert result is not None
    assert result["html_url"] == "https://example.com/run/good"


# -- _build_actions_api_base (line 194) --


def test_build_actions_api_base_enterprise() -> None:
    assert _build_actions_api_base("https://ghe.example.com/org/repo") == "https://ghe.example.com/api/v3"


# -- hydrate early return (line 56) --


def test_hydration_skips_when_web_url_already_set() -> None:
    notification = _notification(web_url="https://github.com/org/repo/pull/1")
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=_FakeClient(responses={}))

    assert notification.web_url == "https://github.com/org/repo/pull/1"


# -- _resolve_check_suite exception fallthrough (lines 94-95, 110-111) --


def test_check_suite_subject_url_api_error_falls_to_fallback() -> None:
    notification = _notification(
        thread_id="99",
        subject_type="CheckSuite",
        subject_url="https://api.example.com/repos/org/repo/check-suites/555",
        web_url=None,
        subject_title="Docs workflow run failed for main branch",
    )
    raise_client = _FakeRaiseClient()
    engine = PipelineEngine(
        providers=[GitHubWebUrlProvider()],
        max_requests_per_cycle=2,
    )

    result = engine.run(notifications=[notification], client=raise_client)

    assert result.notifications[0].web_url == "https://github.com/org/repo/actions?query=branch%3Amain"


# -- _resolve_check_suite_from_subject_url (lines 140, 147, 155) --


def test_check_suite_subject_url_not_check_suite_pattern() -> None:
    notification = _notification(
        thread_id="99",
        subject_type="CheckSuite",
        subject_url="https://api.example.com/repos/other/repo/discussions/123",
        web_url=None,
        subject_title="Docs workflow run failed for main branch",
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/repos/org/repo/actions/runs?branch=main&per_page=25": {
                "workflow_runs": [
                    {
                        "name": "Docs",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "html_url": "https://github.com/org/repo/actions/runs/1",
                    }
                ]
            },
        }
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.notifications[0].web_url == "https://github.com/org/repo/actions/runs/1"


def test_check_suite_from_subject_url_non_dict_response() -> None:
    notification = _notification(
        subject_type="CheckSuite",
        subject_url="https://api.example.com/repos/org/repo/check-suites/555",
        web_url=None,
        subject_title="Docs workflow run failed for main branch",
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/repos/org/repo/check-suites/555/check-runs?per_page=1": ["not", "a", "dict"],
            "https://api.example.com/repos/org/repo/actions/runs?branch=main&per_page=25": {
                "workflow_runs": [
                    {
                        "name": "Docs",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "html_url": "https://github.com/org/repo/actions/runs/1",
                    }
                ]
            },
        }
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.notifications[0].web_url == "https://github.com/org/repo/actions/runs/1"


def test_check_suite_from_subject_url_empty_check_runs() -> None:
    notification = _notification(
        subject_type="CheckSuite",
        subject_url="https://api.example.com/repos/org/repo/check-suites/555",
        web_url=None,
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/repos/org/repo/check-suites/555/check-runs?per_page=1": {
                "check_runs": [],
            },
        }
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=client)

    assert notification.web_url is None


# -- _resolve_release edge cases (lines 160, 163) --


def test_release_subject_url_not_release_pattern() -> None:
    notification = _notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/tags/v1.0",
        web_url=None,
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=_FakeClient(responses={}))

    assert notification.web_url is None


def test_release_non_dict_response() -> None:
    notification = _notification(
        subject_type="Release",
        subject_url="https://api.example.com/repos/org/repo/releases/123",
        web_url=None,
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/repos/org/repo/releases/123": ["not", "a", "dict"],
        }
    )
    engine = PipelineEngine(providers=[GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=client)

    assert notification.web_url is None


# -- enterprise host in check-suite fallback (line 194 integrated) --


def test_enterprise_check_suite_fallback() -> None:
    notification = _notification(
        thread_id="1",
        subject_type="CheckSuite",
        subject_url=None,
        web_url=None,
        subject_title="CI workflow run failed for main branch",
        repository_url="https://ghe.example.com/org/repo",
    )
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/1": {"subject": {"url": None}},
            # _resolve_check_suite uses client.api_base_url (trusted) for the API base,
            # not the repo_base from the notification (which could be external data).
            "https://api.example.com/repos/org/repo/actions/runs?branch=main&per_page=25": {
                "workflow_runs": [
                    {
                        "name": "CI",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "html_url": "https://ghe.example.com/org/repo/actions/runs/1",
                    }
                ]
            },
        }
    )
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert result.notifications[0].web_url == "https://ghe.example.com/org/repo/actions/runs/1"


# -- GitHubThreadSubjectProvider edge cases (lines 26, 32) --


def test_thread_subject_skips_when_subject_url_already_set() -> None:
    notification = _notification(
        thread_id="1",
        subject_type="CheckSuite",
        subject_url="https://api.example.com/repos/org/repo/check-suites/1",
        web_url=None,
    )
    client = _FakeClient(responses={})
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider(), GitHubWebUrlProvider()])

    engine.run(notifications=[notification], client=client)

    assert notification.subject_url == "https://api.example.com/repos/org/repo/check-suites/1"


def test_thread_subject_ignores_non_dict_subject_field() -> None:
    notification = _notification(thread_id="7", subject_type="CheckSuite", subject_url=None, web_url=None)
    client = _FakeClient(
        responses={
            "https://api.example.com/notifications/threads/7": {"subject": "not-a-dict"},
        }
    )
    engine = PipelineEngine(providers=[GitHubThreadSubjectProvider()])

    result = engine.run(notifications=[notification], client=client)

    assert result.errors == []
    assert notification.subject_url is None


# -- PipelineEngine empty providers (line 33) --


def test_engine_empty_providers_returns_empty_result() -> None:
    notification = _notification()
    engine = PipelineEngine(providers=[])

    result = engine.run(notifications=[notification], client=_FakeClient(responses={}))

    assert result.errors == []
    assert notification.web_url is None
