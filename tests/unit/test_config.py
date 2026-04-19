"""Configuration parsing tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from corvix.config import load_config


def test_load_config_parses_rules_and_dashboards(tmp_path: Path) -> None:
    config_path = tmp_path / "corvix.yaml"
    config_path.write_text(
        """
github:
  token_env: GH_TOKEN

rules:
  global:
    - name: bots
      match:
        title_regex: ".*bot.*"
      actions:
        - type: mark_read
      exclude_from_dashboards: true
  per_repository:
    org/repo:
      - name: mute-chore
        match:
          title_contains_any: ["chore"]
        actions:
          - type: mark_read

dashboards:
  - name: triage
    group_by: repository
    sort_by: score
    descending: true
    match:
      reason_in: ["mention"]
    ignore_rules:
      - reason_in: ["subscribed"]
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.github.token_env == "GH_TOKEN"
    assert len(config.rules.global_rules) == 1
    assert "org/repo" in config.rules.per_repository
    assert config.dashboards[0].name == "triage"
    assert config.dashboards[0].match.reason_in == ["mention"]
    assert len(config.dashboards[0].ignore_rules) == 1
    assert config.dashboards[0].ignore_rules[0].reason_in == ["subscribed"]


def test_config_parses_auth_and_database_sections(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
github:
  token_env: GITHUB_TOKEN
auth:
  mode: multi_user
  session_secret: supersecret
database:
  url_env: DATABASE_URL
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.auth.mode == "multi_user"
    assert config.auth.session_secret == "supersecret"
    assert config.database.url_env == "DATABASE_URL"


def test_config_auth_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("github:\n  token_env: GITHUB_TOKEN\n", encoding="utf-8")
    config = load_config(config_file)
    assert config.auth.mode == "single_user"
    assert config.auth.session_secret == ""
    assert config.database.url_env == "DATABASE_URL"


def test_config_github_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("{}\n", encoding="utf-8")
    config = load_config(config_file)
    assert config.github.token_env == "GITHUB_TOKEN"
    assert config.github.api_base_url == "https://api.github.com"
    assert len(config.github.accounts) == 1
    assert config.github.accounts[0].id == "primary"
    assert config.github.accounts[0].label == "Primary"


def test_config_polling_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("{}\n", encoding="utf-8")
    config = load_config(config_file)
    assert config.polling.interval_seconds == 60
    assert config.polling.per_page == 50
    assert config.polling.max_pages == 5


def test_config_polling_per_page_accepts_boundaries(tmp_path: Path) -> None:
    for per_page in (1, 50):
        config_file = tmp_path / f"corvix-{per_page}.yaml"
        config_file.write_text(f"polling:\n  per_page: {per_page}\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.polling.per_page == per_page


@pytest.mark.parametrize("per_page", [0, 51, -1])
def test_config_polling_per_page_rejects_invalid_values(tmp_path: Path, per_page: int) -> None:
    config_file = tmp_path / f"invalid-{per_page}.yaml"
    config_file.write_text(f"polling:\n  per_page: {per_page}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="polling\\.per_page"):
        load_config(config_file)


def test_config_scoring_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("{}\n", encoding="utf-8")
    config = load_config(config_file)
    assert config.scoring.unread_bonus == 15.0
    assert config.scoring.age_decay_per_hour == 0.25


def test_config_match_criteria_fields(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
rules:
  global:
    - name: complex
      match:
        repository_in: ["org/repo"]
        repository_glob: ["org/*"]
        reason_in: ["mention"]
        subject_type_in: ["PullRequest"]
        title_contains_any: ["urgent"]
        title_regex: ".*HOTFIX.*"
        unread: true
        min_score: 10.0
        max_age_hours: 48.0
        context:
          - path: github.latest_comment.author.login
            op: equals
            value: codecov[bot]
            case_insensitive: true
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    m = config.rules.global_rules[0].match
    assert m.repository_in == ["org/repo"]
    assert m.repository_glob == ["org/*"]
    assert m.reason_in == ["mention"]
    assert m.subject_type_in == ["PullRequest"]
    assert m.title_contains_any == ["urgent"]
    assert m.title_regex == ".*HOTFIX.*"
    assert m.unread is True
    assert m.min_score == 10.0
    assert m.max_age_hours == 48.0
    assert len(m.context) == 1
    assert m.context[0].path == "github.latest_comment.author.login"
    assert m.context[0].op == "equals"
    assert m.context[0].value == "codecov[bot]"
    assert m.context[0].case_insensitive is True


def test_config_enrichment_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("{}\n", encoding="utf-8")

    config = load_config(config_file)

    assert config.enrichment.enabled is False
    assert config.enrichment.max_requests_per_cycle == 25
    assert config.enrichment.github_latest_comment.enabled is False
    assert config.enrichment.github_latest_comment.timeout_seconds == 10.0
    assert config.enrichment.github_pr_state.enabled is False
    assert config.enrichment.github_pr_state.timeout_seconds == 10.0


def test_config_enrichment_override(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
enrichment:
  enabled: true
  max_requests_per_cycle: 100
  github_latest_comment:
    enabled: true
    timeout_seconds: 4.5
  github_pr_state:
    enabled: true
    timeout_seconds: 7.5
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.enrichment.enabled is True
    assert config.enrichment.max_requests_per_cycle == 100
    assert config.enrichment.github_latest_comment.enabled is True
    assert config.enrichment.github_latest_comment.timeout_seconds == 4.5
    assert config.enrichment.github_pr_state.enabled is True
    assert config.enrichment.github_pr_state.timeout_seconds == 7.5


def test_config_match_context_invalid_operator_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
rules:
  global:
    - name: bad-op
      match:
        context:
          - path: github.latest_comment.body
            op: starts_with
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"match\.context\[\]\.op"):
        load_config(config_file)


def test_config_match_context_regex_requires_string_value(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
rules:
  global:
    - name: bad-regex-value
      match:
        context:
          - path: github.latest_comment.body
            op: regex
            value: 123
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"match\.context\[\]\.value"):
        load_config(config_file)


def test_config_match_context_invalid_regex_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
rules:
  global:
    - name: bad-regex
      match:
        context:
          - path: github.latest_comment.body
            op: regex
            value: "("
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"match\.context\[\]\.value.*invalid regex"):
        load_config(config_file)


def test_config_match_context_requires_path(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
rules:
  global:
    - name: bad-path
      match:
        context:
          - op: equals
            value: x
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"match\.context\[\]\.path"):
        load_config(config_file)


def test_dashboard_ignore_rules_errors_reference_ignore_rules_section(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
dashboards:
  - name: triage
    ignore_rules:
      - min_score: nope
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"dashboards\[\]\.ignore_rules\[\]\.min_score"):
        load_config(config_file)


def test_load_config_non_dict_top_level(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("hello\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Top-level YAML must be a map/object"):
        load_config(config_file)


def test_ensure_map_raises_for_non_dict(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("github: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Config section 'github' must be a map/object"):
        load_config(config_file)


def test_ensure_list_raises_for_non_list(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text("dashboards: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Config section 'dashboards' must be a list"):
        load_config(config_file)


def test_to_str_list_raises_for_non_list(tmp_path: Path) -> None:
    config_file = tmp_path / "corvix.yaml"
    config_file.write_text(
        """
rules:
  global:
    - name: bad-match
      match:
        repository_in: not-a-list
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Expected a list"):
        load_config(config_file)
