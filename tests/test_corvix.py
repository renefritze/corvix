"""Tests for `corvix` package."""

from click.testing import CliRunner

import corvix
from corvix import cli


def test_version() -> None:
    assert corvix.__version__


def test_import() -> None:
    import corvix  # noqa: F401, PLC0415


def test_command_line_interface() -> None:
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "corvix.cli.main" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help  Show this message and exit." in help_result.output
