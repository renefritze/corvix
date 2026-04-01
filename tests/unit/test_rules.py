"""Tests for rule matching and evaluation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from corvix.config import ContextPredicate, MatchCriteria, Rule, RuleAction, RuleSet
from corvix.domain import Notification
from corvix.rules import evaluate_rules, matches_criteria

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_notification(
    *,
    repository: str = "org/repo",
    reason: str = "mention",
    subject_title: str = "Fix bug",
    subject_type: str = "PullRequest",
    unread: bool = True,
    updated_at: datetime | None = None,
) -> Notification:
    return Notification(
        thread_id="1",
        repository=repository,
        reason=reason,
        subject_title=subject_title,
        subject_type=subject_type,
        unread=unread,
        updated_at=updated_at or NOW,
    )


# --- matches_criteria ---


def test_empty_criteria_matches_everything() -> None:
    assert matches_criteria(MatchCriteria(), _make_notification(), score=0.0, now=NOW) is True


def test_repository_in_match() -> None:
    assert matches_criteria(MatchCriteria(repository_in=["org/repo"]), _make_notification(), score=0.0, now=NOW) is True


def test_repository_in_no_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(repository_in=["org/repo"]), _make_notification(repository="org/other"), score=0.0, now=NOW
        )
        is False
    )


def test_repository_glob_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(repository_glob=["org/oasys*"]),
            _make_notification(repository="org/oasys-core"),
            score=0.0,
            now=NOW,
        )
        is True
    )


def test_repository_glob_no_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(repository_glob=["org/oasys*"]),
            _make_notification(repository="org/other"),
            score=0.0,
            now=NOW,
        )
        is False
    )


def test_reason_in_match() -> None:
    assert (
        matches_criteria(MatchCriteria(reason_in=["mention"]), _make_notification(reason="mention"), score=0.0, now=NOW)
        is True
    )


def test_reason_in_no_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(reason_in=["mention"]), _make_notification(reason="subscribed"), score=0.0, now=NOW
        )
        is False
    )


def test_subject_type_in_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(subject_type_in=["PullRequest"]),
            _make_notification(subject_type="PullRequest"),
            score=0.0,
            now=NOW,
        )
        is True
    )


def test_subject_type_in_no_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(subject_type_in=["PullRequest"]), _make_notification(subject_type="Issue"), score=0.0, now=NOW
        )
        is False
    )


def test_title_contains_any_case_insensitive() -> None:
    assert (
        matches_criteria(
            MatchCriteria(title_contains_any=["security"]),
            _make_notification(subject_title="Fix SECURITY issue"),
            score=0.0,
            now=NOW,
        )
        is True
    )


def test_title_contains_any_no_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(title_contains_any=["security"]),
            _make_notification(subject_title="routine update"),
            score=0.0,
            now=NOW,
        )
        is False
    )


def test_title_contains_any_multiple_tokens_or_logic() -> None:
    # Any token matching is enough
    assert (
        matches_criteria(
            MatchCriteria(title_contains_any=["chore", "deps"]),
            _make_notification(subject_title="update deps"),
            score=0.0,
            now=NOW,
        )
        is True
    )


def test_title_regex_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(title_regex=r".*\[bot\].*"),
            _make_notification(subject_title="[bot] auto update"),
            score=0.0,
            now=NOW,
        )
        is True
    )


def test_title_regex_no_match() -> None:
    assert (
        matches_criteria(
            MatchCriteria(title_regex=r".*\[bot\].*"),
            _make_notification(subject_title="human review"),
            score=0.0,
            now=NOW,
        )
        is False
    )


def test_unread_true_matches_unread() -> None:
    assert matches_criteria(MatchCriteria(unread=True), _make_notification(unread=True), score=0.0, now=NOW) is True


def test_unread_true_no_match_when_read() -> None:
    assert matches_criteria(MatchCriteria(unread=True), _make_notification(unread=False), score=0.0, now=NOW) is False


def test_unread_false_matches_read() -> None:
    assert matches_criteria(MatchCriteria(unread=False), _make_notification(unread=False), score=0.0, now=NOW) is True


def test_min_score_match() -> None:
    assert matches_criteria(MatchCriteria(min_score=10.0), _make_notification(), score=20.0, now=NOW) is True


def test_min_score_no_match() -> None:
    assert matches_criteria(MatchCriteria(min_score=50.0), _make_notification(), score=20.0, now=NOW) is False


def test_max_age_hours_match() -> None:
    n = _make_notification(updated_at=NOW - timedelta(hours=2))
    assert matches_criteria(MatchCriteria(max_age_hours=5.0), n, score=0.0, now=NOW) is True


def test_max_age_hours_no_match() -> None:
    n = _make_notification(updated_at=NOW - timedelta(hours=10))
    assert matches_criteria(MatchCriteria(max_age_hours=5.0), n, score=0.0, now=NOW) is False


def test_and_logic_all_criteria_must_match() -> None:
    # reason matches but repository doesn't
    assert (
        matches_criteria(
            MatchCriteria(reason_in=["mention"], repository_in=["org/repo"]),
            _make_notification(reason="mention", repository="org/other"),
            score=0.0,
            now=NOW,
        )
        is False
    )


def test_context_equals_match() -> None:
    criteria = MatchCriteria(
        context=[ContextPredicate(path="github.latest_comment.author.login", op="equals", value="codecov[bot]")]
    )
    context = {"github": {"latest_comment": {"author": {"login": "codecov[bot]"}}}}
    assert matches_criteria(criteria, _make_notification(), score=0.0, now=NOW, context=context) is True


def test_context_not_equals_match() -> None:
    criteria = MatchCriteria(
        context=[ContextPredicate(path="github.latest_comment.author.login", op="not_equals", value="someone")]
    )
    context = {"github": {"latest_comment": {"author": {"login": "codecov[bot]"}}}}
    assert matches_criteria(criteria, _make_notification(), score=0.0, now=NOW, context=context) is True


def test_context_contains_case_insensitive() -> None:
    criteria = MatchCriteria(
        context=[
            ContextPredicate(
                path="github.latest_comment.body",
                op="contains",
                value="test report",
                case_insensitive=True,
            )
        ]
    )
    context = {"github": {"latest_comment": {"body": "This has a Test Report link"}}}
    assert matches_criteria(criteria, _make_notification(), score=0.0, now=NOW, context=context) is True


def test_context_regex_match() -> None:
    criteria = MatchCriteria(context=[ContextPredicate(path="github.latest_comment.body", op="regex", value=r"^CI$")])
    context = {"github": {"latest_comment": {"body": "CI"}}}
    assert matches_criteria(criteria, _make_notification(), score=0.0, now=NOW, context=context) is True


def test_context_in_match() -> None:
    criteria = MatchCriteria(
        context=[
            ContextPredicate(
                path="github.latest_comment.author.login",
                op="in",
                value=["dependabot[bot]", "codecov[bot]"],
            )
        ]
    )
    context = {"github": {"latest_comment": {"author": {"login": "codecov[bot]"}}}}
    assert matches_criteria(criteria, _make_notification(), score=0.0, now=NOW, context=context) is True


def test_context_exists_true_and_false() -> None:
    exists_criteria = MatchCriteria(context=[ContextPredicate(path="github.latest_comment.body", op="exists")])
    missing_criteria = MatchCriteria(
        context=[ContextPredicate(path="github.latest_comment.body", op="exists", value=False)]
    )
    context = {"github": {"latest_comment": {"body": "CI"}}}
    assert matches_criteria(exists_criteria, _make_notification(), score=0.0, now=NOW, context=context) is True
    assert matches_criteria(missing_criteria, _make_notification(), score=0.0, now=NOW, context=context) is False


def test_context_missing_path_fails_non_exists_ops() -> None:
    criteria = MatchCriteria(context=[ContextPredicate(path="github.latest_comment.body", op="equals", value="CI")])
    assert matches_criteria(criteria, _make_notification(), score=0.0, now=NOW, context={}) is False


# --- evaluate_rules ---


def test_global_rule_matches() -> None:
    n = _make_notification(reason="mention")
    rules = RuleSet(global_rules=[Rule(name="test-rule", match=MatchCriteria(reason_in=["mention"]))])
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert "test-rule" in result.matched_rules


def test_rule_evaluation_with_context_predicate() -> None:
    n = _make_notification(reason="comment")
    rules = RuleSet(
        global_rules=[
            Rule(
                name="mute-codecov",
                match=MatchCriteria(
                    context=[
                        ContextPredicate(
                            path="github.latest_comment.author.login",
                            op="equals",
                            value="codecov[bot]",
                        )
                    ]
                ),
            )
        ]
    )
    context = {"github": {"latest_comment": {"author": {"login": "codecov[bot]"}}}}
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW, context=context)
    assert result.matched_rules == ["mute-codecov"]


def test_per_repo_rule_matches() -> None:
    n = _make_notification(repository="org/repo")
    rules = RuleSet(per_repository={"org/repo": [Rule(name="repo-rule", match=MatchCriteria())]})
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert "repo-rule" in result.matched_rules


def test_per_repo_rule_not_applied_to_other_repo() -> None:
    n = _make_notification(repository="org/other")
    rules = RuleSet(per_repository={"org/repo": [Rule(name="repo-rule", match=MatchCriteria())]})
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert result.matched_rules == []


def test_exclude_flag_propagated() -> None:
    n = _make_notification()
    rules = RuleSet(global_rules=[Rule(name="exclude-rule", match=MatchCriteria(), exclude_from_dashboards=True)])
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert result.excluded is True


def test_no_match_not_excluded() -> None:
    n = _make_notification(reason="subscribed")
    rules = RuleSet(
        global_rules=[Rule(name="rule", match=MatchCriteria(reason_in=["mention"]), exclude_from_dashboards=True)]
    )
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert result.excluded is False


def test_rule_actions_collected() -> None:
    n = _make_notification()
    rules = RuleSet(
        global_rules=[Rule(name="rule", match=MatchCriteria(), actions=[RuleAction(action_type="mark_read")])]
    )
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert any(a.action_type == "mark_read" for a in result.actions)


def test_empty_rules_no_match() -> None:
    result = evaluate_rules(_make_notification(), score=0.0, rules=RuleSet(), now=NOW)
    assert result.matched_rules == []
    assert result.actions == []
    assert result.excluded is False


def test_multiple_matching_rules_all_collected() -> None:
    n = _make_notification()
    rules = RuleSet(
        global_rules=[Rule(name="rule-a", match=MatchCriteria()), Rule(name="rule-b", match=MatchCriteria())]
    )
    result = evaluate_rules(n, score=0.0, rules=rules, now=NOW)
    assert "rule-a" in result.matched_rules
    assert "rule-b" in result.matched_rules


def test_now_defaults_to_current_time() -> None:
    result = evaluate_rules(_make_notification(), score=0.0, rules=RuleSet())
    assert result.matched_rules == []
