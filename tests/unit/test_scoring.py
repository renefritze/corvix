"""Tests for notification scoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from corvix.config import ScoringConfig
from corvix.domain import Notification
from corvix.scoring import score_notification


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
        updated_at=updated_at or datetime.now(tz=UTC),
    )


def _config(**kwargs: object) -> ScoringConfig:
    defaults: dict[str, object] = {
        "unread_bonus": 10.0,
        "age_decay_per_hour": 0.0,
        "reason_weights": {},
        "repository_weights": {},
        "subject_type_weights": {},
        "title_keyword_weights": {},
    }
    defaults.update(kwargs)
    return ScoringConfig(**defaults)  # type: ignore[arg-type]


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def test_unread_bonus_applied() -> None:
    score = score_notification(_make_notification(unread=True), _config(unread_bonus=10.0), now=NOW)
    assert score == 10.0


def test_no_unread_bonus_when_read() -> None:
    score = score_notification(_make_notification(unread=False), _config(unread_bonus=10.0), now=NOW)
    assert score == 0.0


def test_reason_weight_applied() -> None:
    score = score_notification(
        _make_notification(reason="mention", unread=False),
        _config(reason_weights={"mention": 50.0}),
        now=NOW,
    )
    assert score == 50.0


def test_reason_weight_no_match_zero() -> None:
    score = score_notification(
        _make_notification(reason="subscribed", unread=False),
        _config(reason_weights={"mention": 50.0}),
        now=NOW,
    )
    assert score == 0.0


def test_repository_weight_applied() -> None:
    score = score_notification(
        _make_notification(repository="org/critical", unread=False),
        _config(repository_weights={"org/critical": 25.0}),
        now=NOW,
    )
    assert score == 25.0


def test_subject_type_weight_applied() -> None:
    score = score_notification(
        _make_notification(subject_type="PullRequest", unread=False),
        _config(subject_type_weights={"PullRequest": 10.0}),
        now=NOW,
    )
    assert score == 10.0


def test_title_keyword_match_case_insensitive() -> None:
    score = score_notification(
        _make_notification(subject_title="SECURITY patch", unread=False),
        _config(title_keyword_weights={"security": 20.0}),
        now=NOW,
    )
    assert score == 20.0


def test_title_keyword_no_match() -> None:
    score = score_notification(
        _make_notification(subject_title="routine update", unread=False),
        _config(title_keyword_weights={"security": 20.0}),
        now=NOW,
    )
    assert score == 0.0


def test_multiple_title_keywords_accumulate() -> None:
    score = score_notification(
        _make_notification(subject_title="security urgent fix", unread=False),
        _config(title_keyword_weights={"security": 20.0, "urgent": 15.0}),
        now=NOW,
    )
    assert score == 35.0


def test_age_decay_reduces_score() -> None:
    score = score_notification(
        _make_notification(unread=False, updated_at=NOW - timedelta(hours=4)),
        _config(age_decay_per_hour=1.0),
        now=NOW,
    )
    assert score == -4.0


def test_age_decay_zero_for_fresh_notification() -> None:
    score = score_notification(
        _make_notification(unread=False, updated_at=NOW),
        _config(age_decay_per_hour=1.0),
        now=NOW,
    )
    assert score == 0.0


def test_all_weights_combined() -> None:
    n = _make_notification(
        reason="mention",
        repository="org/critical",
        subject_type="PullRequest",
        subject_title="security patch",
        unread=True,
        updated_at=NOW - timedelta(hours=2),
    )
    config = ScoringConfig(
        unread_bonus=10.0,
        age_decay_per_hour=1.0,
        reason_weights={"mention": 50.0},
        repository_weights={"org/critical": 25.0},
        subject_type_weights={"PullRequest": 10.0},
        title_keyword_weights={"security": 20.0},
    )
    # 10 (unread) + 50 (reason) + 25 (repo) + 10 (type) + 20 (keyword) - 2 (decay) = 113
    assert score_notification(n, config, now=NOW) == pytest.approx(113.0)


def test_now_defaults_to_current_time() -> None:
    score = score_notification(_make_notification(), _config())
    assert isinstance(score, float)
