"""Scoring configuration model and YAML parsing."""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.config._utils import _ensure_map, _get_float, _to_float_map


@dataclass(slots=True)
class ScoringConfig:
    """Configurable scoring model for notifications."""

    unread_bonus: float = 15.0
    age_decay_per_hour: float = 0.25
    reason_weights: dict[str, float] = field(default_factory=dict)
    repository_weights: dict[str, float] = field(default_factory=dict)
    subject_type_weights: dict[str, float] = field(default_factory=dict)
    title_keyword_weights: dict[str, float] = field(default_factory=dict)


def _parse_scoring(value: object) -> ScoringConfig:
    scoring = _ensure_map(value, "scoring")
    return ScoringConfig(
        unread_bonus=_get_float(scoring, "unread_bonus", 15.0, "scoring.unread_bonus"),
        age_decay_per_hour=_get_float(scoring, "age_decay_per_hour", 0.25, "scoring.age_decay_per_hour"),
        reason_weights=_to_float_map(scoring.get("reason_weights", {}), "scoring.reason_weights"),
        repository_weights=_to_float_map(scoring.get("repository_weights", {}), "scoring.repository_weights"),
        subject_type_weights=_to_float_map(scoring.get("subject_type_weights", {}), "scoring.subject_type_weights"),
        title_keyword_weights=_to_float_map(scoring.get("title_keyword_weights", {}), "scoring.title_keyword_weights"),
    )
