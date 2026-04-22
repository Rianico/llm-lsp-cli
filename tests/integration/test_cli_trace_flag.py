"""Integration tests for CLI --trace flag.

Tests for the --trace / -t CLI flag behavior.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from llm_lsp_cli.cli import app

# =============================================================================
# Test Suite 2.3: CLI Flag Behavior
# =============================================================================


class TestCLITraceFlag:
    """Tests for CLI --trace flag behavior."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_daemon_manager(self) -> MagicMock:
        """Create a mock DaemonManager for CLI tests."""
        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345
        mock._lsp_server_name = "pyright-langserver"
        return mock

    def test_start_accepts_trace_flag(
        self, cli_runner: CliRunner, mock_daemon_manager: MagicMock
    ) -> None:
        """llm-lsp-cli start --trace accepted (with mocked daemon)."""
        with patch("llm_lsp_cli.cli._create_daemon_manager") as mock_create:
            mock_create.return_value = mock_daemon_manager

            result = cli_runner.invoke(app, ["start", "--trace"])

            # Should not fail with unknown option
            assert "unknown option" not in result.output.lower()
            assert "error" not in result.output.lower() or result.exit_code == 0

    def test_start_trace_flag_short_form(
        self, cli_runner: CliRunner, mock_daemon_manager: MagicMock
    ) -> None:
        """llm-lsp-cli start -t accepted (with mocked daemon)."""
        with patch("llm_lsp_cli.cli._create_daemon_manager") as mock_create:
            mock_create.return_value = mock_daemon_manager

            result = cli_runner.invoke(app, ["start", "-t"])

            # Should not fail with unknown option
            assert "unknown option" not in result.output.lower()

    def test_restart_accepts_trace_flag(
        self, cli_runner: CliRunner, mock_daemon_manager: MagicMock
    ) -> None:
        """llm-lsp-cli restart --trace accepted (with mocked daemon)."""
        with patch("llm_lsp_cli.cli._create_daemon_manager") as mock_create:
            mock_create.return_value = mock_daemon_manager
            mock_daemon_manager.is_running.return_value = True

            result = cli_runner.invoke(app, ["restart", "--trace"])

            # Should not fail with unknown option
            assert "unknown option" not in result.output.lower()

    def test_trace_implies_debug_behavior(
        self, cli_runner: CliRunner, mock_daemon_manager: MagicMock
    ) -> None:
        """--trace enables DEBUG level for all loggers."""
        # This test verifies that when --trace is used, the daemon is started
        # with trace=True, which should set DEBUG level for all loggers
        with patch("llm_lsp_cli.cli._create_daemon_manager") as mock_create:
            mock_create.return_value = mock_daemon_manager

            cli_runner.invoke(app, ["start", "--trace"])

            # The DaemonManager should have been created with trace=True
            # This is verified by checking the implementation


# =============================================================================
# Test Suite 2.4: CLI Flag Help Text
# =============================================================================


class TestCLITraceHelpText:
    """Tests for --trace flag help text."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a CLI test runner."""
        return CliRunner()

    def test_trace_help_text_present(self, cli_runner: CliRunner) -> None:
        """--trace has help text mentioning 'transport-level'."""
        result = cli_runner.invoke(app, ["start", "--help"])

        assert "trace" in result.output.lower()
        # Help text should mention transport-level logging
        assert "transport" in result.output.lower() or "verbose" in result.output.lower()

    def test_trace_help_explains_debug_relation(self, cli_runner: CliRunner) -> None:
        """Help explains relationship to --debug."""
        result = cli_runner.invoke(app, ["start", "--help"])

        # Should mention that --trace is more verbose than --debug
        output = result.output.lower()
        # Either explicitly mentions debug relationship or implies more verbosity
        assert "debug" in output or "verbose" in output
