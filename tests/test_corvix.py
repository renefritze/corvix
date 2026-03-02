"""Tests for `corvix` package."""

from pathlib import Path

from click.testing import CliRunner

import corvix
from corvix import cli


def test_version() -> None:
    assert corvix.__version__


def test_import() -> None:
    import corvix  # noqa: F401, PLC0415


def test_command_line_interface() -> None:
    """Test the CLI root and init-config command."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "init-config" in result.output
    assert "poll" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help" in help_result.output
    assert "Show this message and exit." in help_result.output


def test_init_config_command(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "corvix.yaml"
    result = runner.invoke(cli.main, ["init-config", str(config_path)])
    assert result.exit_code == 0
    assert config_path.exists()
    assert "github:" in config_path.read_text(encoding="utf-8")
