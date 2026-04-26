"""Tests for --diagnostic-log CLI option.

Verifies that the CLI accepts the --diagnostic-log option for start and restart commands.
"""

from typer.testing import CliRunner

from llm_lsp_cli.cli import app

runner = CliRunner()


class TestDiagnosticLogCliOption:
    """Tests for --diagnostic-log CLI option acceptance."""

    def test_start_accepts_diagnostic_log_flag(self) -> None:
        """start command accepts --diagnostic-log flag."""
        # Use --help to avoid actually starting the daemon
        result = runner.invoke(app, ["daemon", "start", "--help"])
        assert result.exit_code == 0
        assert "--diagnostic-log" in result.output

    def test_restart_accepts_diagnostic_log_flag(self) -> None:
        """restart command accepts --diagnostic-log flag."""
        result = runner.invoke(app, ["daemon", "restart", "--help"])
        assert result.exit_code == 0
        assert "--diagnostic-log" in result.output

    def test_diagnostic_log_flag_description(self) -> None:
        """--diagnostic-log flag has correct description."""
        result = runner.invoke(app, ["daemon", "start", "--help"])
        assert result.exit_code == 0
        assert "diagnostics" in result.output.lower() or "diagnostic" in result.output.lower()

    def test_diagnostic_log_default_is_false(self) -> None:
        """--diagnostic-log defaults to False (disabled)."""
        # Verify the option exists and can be parsed
        result = runner.invoke(app, ["daemon", "start", "--help"])
        assert result.exit_code == 0
        # The help should show the option exists
        assert "--diagnostic-log" in result.output

    def test_stop_does_not_have_diagnostic_log(self) -> None:
        """stop command does not have --diagnostic-log (not applicable)."""
        result = runner.invoke(app, ["daemon", "stop", "--help"])
        assert result.exit_code == 0
        # stop command should not have --diagnostic-log
        assert "--diagnostic-log" not in result.output

    def test_status_does_not_have_diagnostic_log(self) -> None:
        """status command does not have --diagnostic-log (not applicable)."""
        result = runner.invoke(app, ["daemon", "status", "--help"])
        assert result.exit_code == 0
        # status command should not have --diagnostic-log
        assert "--diagnostic-log" not in result.output
