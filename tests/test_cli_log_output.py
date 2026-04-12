"""Unit tests for CLI log output format with [START], [STOP], [RESTART] prefixes."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_daemon_not_running() -> MagicMock:
    """Create a mock daemon manager that is not running."""
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = False
    return mock_instance


@pytest.fixture
def mock_daemon_running() -> MagicMock:
    """Create a mock daemon manager that is running."""
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = True
    return mock_instance


def _create_mock_manager(is_running: bool = False) -> MagicMock:
    """Create a mock daemon manager with specified running state.

    Args:
        is_running: Whether the daemon should appear running

    Returns:
        Configured mock instance
    """
    mock_instance = MagicMock()
    mock_instance.is_running.return_value = is_running
    return mock_instance


def _invoke_start(args: list[str], mock_instance: MagicMock) -> Any:
    """Invoke start command with mocked daemon manager.

    Args:
        args: CLI arguments
        mock_instance: Mock daemon manager instance

    Returns:
        Test result object
    """
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance
        return runner.invoke(app, ["start", *args])


def _invoke_stop(args: list[str], mock_instance: MagicMock) -> Any:
    """Invoke stop command with mocked daemon manager."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance
        return runner.invoke(app, ["stop", *args])


def _invoke_restart(args: list[str], mock_instance: MagicMock) -> Any:
    """Invoke restart command with mocked daemon manager."""
    from llm_lsp_cli.cli import app

    with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
        mock_manager.return_value = mock_instance
        return runner.invoke(app, ["restart", *args])


# =============================================================================
# START Command Log Output Tests
# =============================================================================


class TestStartLogOutput:
    """Tests for START command log output."""

    def test_detected_language(self, temp_dir) -> None:
        """Test that auto-detected language is logged with [START] prefix."""
        (temp_dir / "pyproject.toml").touch()
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_start(["-w", str(temp_dir)], mock_instance)

        assert result.exit_code == 0
        assert "[START] Detected language:" in result.stderr

    def test_initializing(self) -> None:
        """Test that initialization message is logged with [START] prefix."""
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_start(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[START] Initializing daemon..." in result.stderr

    def test_spawning(self) -> None:
        """Test that server spawn message is logged with [START] prefix."""
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_start(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[START] Spawning" in result.stderr
        assert "pyright-langserver" in result.stderr

    def test_ready(self) -> None:
        """Test that ready state with PID is logged with [START] prefix."""
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_start(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[START] Ready" in result.stderr
        assert "PID" in result.stderr

    def test_already_running(self) -> None:
        """Test that error is shown when daemon is already running."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_start(["-l", "python"], mock_instance)

        assert result.exit_code == 1
        assert "Error: Daemon is already running." in result.stderr
        assert "[START]" not in result.stderr

    def test_explicit_language_no_detect(self) -> None:
        """Test that explicit language skips detection logging."""
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_start(["-l", "rust"], mock_instance)

        assert result.exit_code == 0
        assert "[START] Detected language:" not in result.stderr


# =============================================================================
# STOP Command Log Output Tests
# =============================================================================


class TestStopLogOutput:
    """Tests for STOP command log output."""

    def test_stopping(self) -> None:
        """Test that stopping message is logged with [STOP] prefix."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_stop(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[STOP] Stopping daemon..." in result.stderr

    def test_stopped(self) -> None:
        """Test that stopped confirmation is logged with [STOP] prefix."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_stop(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[STOP] Daemon stopped" in result.stderr

    def test_not_running(self) -> None:
        """Test graceful handling when daemon is not running."""
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_stop(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[STOP] Daemon is not running." in result.stderr


# =============================================================================
# RESTART Command Log Output Tests
# =============================================================================


class TestRestartLogOutput:
    """Tests for RESTART command log output."""

    def test_restarting(self) -> None:
        """Test that restart message is logged with [RESTART] prefix."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_restart(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[RESTART] Restarting daemon..." in result.stderr

    def test_stopping_existing(self) -> None:
        """Test that stopping existing daemon is logged with [RESTART] prefix."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_restart(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[RESTART] Stopping existing daemon..." in result.stderr

    def test_starting(self) -> None:
        """Test that start message is logged with [RESTART] prefix."""
        mock_instance = _create_mock_manager(is_running=True)
        mock_instance._lsp_server_name = "pyright-langserver"

        result = _invoke_restart(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[RESTART] Starting" in result.stderr
        assert "pyright-langserver" in result.stderr

    def test_restarted(self) -> None:
        """Test that restarted confirmation with PID is logged with [RESTART] prefix."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_restart(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[RESTART] Daemon restarted" in result.stderr
        assert "PID" in result.stderr


# =============================================================================
# Error Case Tests
# =============================================================================


class TestErrorCases:
    """Tests for error case handling."""

    def test_start_error_already_running(self) -> None:
        """Test start when daemon is running shows error."""
        mock_instance = _create_mock_manager(is_running=True)

        result = _invoke_start(["-l", "python"], mock_instance)

        assert result.exit_code == 1
        assert "Error:" in result.stderr

    def test_stop_graceful_not_running(self) -> None:
        """Test stop when not running is graceful (not an error)."""
        mock_instance = _create_mock_manager(is_running=False)

        result = _invoke_stop(["-l", "python"], mock_instance)

        assert result.exit_code == 0
        assert "[STOP]" in result.stderr
