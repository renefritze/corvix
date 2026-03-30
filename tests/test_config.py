"""Configuration parsing tests."""

from __future__ import annotations

from pathlib import Path

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
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.github.token_env == "GH_TOKEN"
    assert len(config.rules.global_rules) == 1
    assert "org/repo" in config.rules.per_repository
    assert config.dashboards[0].name == "triage"
    assert config.dashboards[0].match.reason_in == ["mention"]
