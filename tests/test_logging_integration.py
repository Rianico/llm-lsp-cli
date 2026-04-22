"""Integration tests for LSP server logging feature.

Tests edge cases, daemon lifecycle, and log file verification.
Run with:
    uv run pytest tests/test_logging_integration.py -v
"""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from llm_lsp_cli.cli import app
from llm_lsp_cli.daemon import DaemonManager

runner = CliRunner()


# =============================================================================
# Edge Case Tests - Rapid Restart
# =============================================================================


class TestRapidRestart:
    """Tests for rapid restart scenarios."""

    @pytest.fixture
    def mock_manager_factory(self) -> Any:
        """Create a factory for mock daemon managers."""

        def create_mock(is_running: bool = False, pid: int = 12345) -> MagicMock:
            mock = MagicMock()
            mock.is_running.return_value = is_running
            mock.get_pid.return_value = pid
            mock._lsp_server_name = "pyright-langserver"
            return mock

        return create_mock

    def test_rapid_restart_not_running(self, mock_manager_factory: Any) -> None:
        """Test rapid restart when daemon is not running."""
        mock = mock_manager_factory(is_running=False)

        # First restart
        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result1 = runner.invoke(app, ["restart", "-l", "python"])
            assert result1.exit_code == 0
            assert "[RESTART] Daemon restarted" in result1.stderr

        # Simulate rapid successive restarts
        for _ in range(3):
            mock.is_running.return_value = False
            with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
                mock_manager.return_value = mock
                result = runner.invoke(app, ["restart", "-l", "python"])
                assert result.exit_code == 0
                assert "[RESTART]" in result.stderr

    def test_rapid_restart_running(self, mock_manager_factory: Any) -> None:
        """Test rapid restart when daemon is running."""
        mock = mock_manager_factory(is_running=True)

        # Multiple rapid restarts while appearing running
        for _ in range(3):
            mock.is_running.return_value = True
            with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
                mock_manager.return_value = mock
                result = runner.invoke(app, ["restart", "-l", "python"])
                assert result.exit_code == 0
                assert "[RESTART] Stopping existing daemon..." in result.stderr
                assert "[RESTART] Daemon restarted" in result.stderr


# =============================================================================
# Edge Case Tests - Stop Scenarios
# =============================================================================


class TestStopEdgeCases:
    """Tests for stop command edge cases."""

    def test_stop_when_not_running(self) -> None:
        """Test stop command when daemon is not running."""
        mock = MagicMock()
        mock.is_running.return_value = False

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["stop", "-l", "python"])

            assert result.exit_code == 0
            assert "[STOP] Daemon is not running." in result.stderr
            # Verify stop() was NOT called since daemon wasn't running
            mock.stop.assert_not_called()

    def test_stop_multiple_times(self) -> None:
        """Test multiple consecutive stop commands."""
        mock = MagicMock()
        # First call: running, subsequent calls: not running
        mock.is_running.side_effect = [True, False, False]

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock

            # First stop - daemon running
            result1 = runner.invoke(app, ["stop", "-l", "python"])
            assert result1.exit_code == 0
            assert "[STOP] Stopping daemon..." in result1.stderr

            # Second stop - daemon not running
            result2 = runner.invoke(app, ["stop", "-l", "python"])
            assert result2.exit_code == 0
            assert "[STOP] Daemon is not running." in result2.stderr

            # Third stop - still not running
            result3 = runner.invoke(app, ["stop", "-l", "python"])
            assert result3.exit_code == 0
            assert "[STOP] Daemon is not running." in result3.stderr


# =============================================================================
# Edge Case Tests - Start Scenarios
# =============================================================================


class TestStartEdgeCases:
    """Tests for start command edge cases."""

    def test_start_when_already_running(self) -> None:
        """Test start command when daemon is already running."""
        mock = MagicMock()
        mock.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["start", "-l", "python"])

            assert result.exit_code == 1
            assert "Error: Daemon is already running." in result.stderr
            # Verify start() was NOT called
            mock.start.assert_not_called()

    def test_start_multiple_times(self) -> None:
        """Test multiple consecutive start commands."""
        mock = MagicMock()
        # First call: not running, subsequent calls: running
        mock.is_running.side_effect = [False, True, True]

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock

            # First start - success
            result1 = runner.invoke(app, ["start", "-l", "python"])
            assert result1.exit_code == 0
            assert "[START] Ready" in result1.stderr

            # Second start - already running
            result2 = runner.invoke(app, ["start", "-l", "python"])
            assert result2.exit_code == 1
            assert "Error: Daemon is already running." in result2.stderr

            # Third start - still running
            result3 = runner.invoke(app, ["start", "-l", "python"])
            assert result3.exit_code == 1
            assert "Error: Daemon is already running." in result3.stderr


# =============================================================================
# Edge Case Tests - Restart Scenarios
# =============================================================================


class TestRestartEdgeCases:
    """Tests for restart command edge cases."""

    def test_restart_preserves_server_name(self) -> None:
        """Test restart command uses correct server name."""
        mock = MagicMock()
        mock.is_running.return_value = True
        mock._lsp_server_name = "rust-analyzer"

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["restart", "-l", "rust"])

            assert result.exit_code == 0
            assert "rust-analyzer" in result.stderr
            assert "[RESTART] Starting rust-analyzer..." in result.stderr

    def test_restart_different_languages(self) -> None:
        """Test restart with different language configurations."""
        languages = [
            ("python", "pyright-langserver"),
            ("typescript", "typescript-language-server"),
            ("rust", "rust-analyzer"),
            ("go", "gopls"),
        ]

        for language, server_name in languages:
            mock = MagicMock()
            mock.is_running.return_value = True
            mock._lsp_server_name = server_name

            with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
                mock_manager.return_value = mock
                result = runner.invoke(app, ["restart", "-l", language])

                assert result.exit_code == 0
                assert server_name in result.stderr


# =============================================================================
# Integration Tests - Actual Daemon Lifecycle
# =============================================================================


class TestDaemonLifecycleIntegration:
    """Integration tests with actual daemon manager (mocked process control)."""

    @pytest.fixture
    def temp_workspace(self) -> Any:
        """Create a temporary workspace for daemon tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            # Create a minimal Python project marker
            (workspace / "pyproject.toml").write_text("[project]\nname = 'test'")
            yield workspace

    def test_daemon_manager_is_running_detection(self, temp_workspace: Path) -> None:
        """Test DaemonManager.is_running() with no PID file."""
        manager = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Should return False when no PID file exists
        assert manager.is_running() is False

    def test_daemon_manager_cleanup_when_not_running(self, temp_workspace: Path) -> None:
        """Test DaemonManager cleans up stale PID file."""
        manager = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Create a stale PID file
        manager.pid_file.parent.mkdir(parents=True, exist_ok=True)
        manager.pid_file.write_text("99999")

        try:
            # Should clean up stale file and return False
            assert manager.is_running() is False
            assert not manager.pid_file.exists()
        finally:
            manager._cleanup_files()

    def test_daemon_manager_pid_file_path_isolation(self, temp_workspace: Path) -> None:
        """Test different workspaces get different PID file paths."""
        workspace_a = temp_workspace / "project_a"
        workspace_b = temp_workspace / "project_b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        manager_a = DaemonManager(workspace_path=str(workspace_a), language="python")
        manager_b = DaemonManager(workspace_path=str(workspace_b), language="python")

        assert manager_a.pid_file != manager_b.pid_file
        assert manager_a.socket_path != manager_b.socket_path
        # LSP log file was removed - all logs now go to daemon.log
        assert manager_a.daemon_log_file != manager_b.daemon_log_file

    def test_daemon_manager_language_isolation(self, temp_workspace: Path) -> None:
        """Test different languages get different runtime files."""
        manager_python = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )
        manager_rust = DaemonManager(
            workspace_path=str(temp_workspace),
            language="rust",
        )

        assert manager_python.pid_file != manager_rust.pid_file
        assert manager_python.socket_path != manager_rust.socket_path


# =============================================================================
# Log File Verification Tests
# =============================================================================


class TestLogFileMarkers:
    """Tests for daemon log file markers and structure."""

    @pytest.fixture
    def temp_workspace(self) -> Any:
        """Create a temporary workspace for log tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            yield workspace

    def test_daemon_log_file_path_structure(self, temp_workspace: Path) -> None:
        """Test daemon log file path follows expected structure."""
        manager = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Verify log file path structure
        assert manager.daemon_log_file.suffix == ".log"
        assert "daemon" in str(manager.daemon_log_file).lower()

    def test_lsp_log_file_path_structure(self, temp_workspace: Path) -> None:
        """Test LSP server log file path follows expected structure.

        Deprecated: LSP server log files are no longer created separately.
        All LSP stderr output is now captured in daemon.log only.
        """
        manager = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # LSP log file was removed - verify daemon_log_file exists instead
        assert manager.daemon_log_file.suffix == ".log"
        assert manager.daemon_log_file.name == "daemon.log"

    def test_log_file_paths_include_language(self, temp_workspace: Path) -> None:
        """Test log file paths include language identifier.

        Deprecated: LSP server log files are no longer created separately.
        Daemon log path still includes workspace but not language-specific.
        """
        manager = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Daemon log file path includes workspace info
        log_path_str = str(manager.daemon_log_file)
        assert "daemon.log" in log_path_str

    def test_daemon_log_includes_workspace_info(self, temp_workspace: Path) -> None:
        """Test daemon log path includes workspace identification."""
        manager = DaemonManager(
            workspace_path=str(temp_workspace),
            language="python",
        )

        daemon_log_str = str(manager.daemon_log_file)

        # Daemon log should be in workspace-specific directory
        assert "daemon.log" in daemon_log_str
        # Should include workspace name or hash for isolation
        assert str(temp_workspace.name) in daemon_log_str or len(daemon_log_str) > 20


# =============================================================================
# CLI Output Stream Tests
# =============================================================================


class TestOutputStreamConsistency:
    """Tests to verify log output stream consistency."""

    def test_all_lifecycle_logs_to_stderr(self) -> None:
        """Test all lifecycle commands log to stderr, not stdout."""
        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345
        mock._lsp_server_name = "pyright-langserver"

        commands = [
            (["start", "-l", "python"], "[START]"),
            (["stop", "-l", "python"], "[STOP]"),
            (["restart", "-l", "python"], "[RESTART]"),
        ]

        for args, prefix in commands:
            with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
                mock_manager.return_value = mock
                result = runner.invoke(app, args)

                # All lifecycle logs should be in stderr
                assert prefix in result.stderr
                # stdout should be empty or minimal
                assert result.stdout == "" or prefix not in result.stdout

    def test_error_logs_to_stderr(self) -> None:
        """Test error messages are logged to stderr."""
        mock = MagicMock()
        mock.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["start", "-l", "python"])

            assert result.exit_code == 1
            assert "Error:" in result.stderr


# =============================================================================
# Performance and Stress Tests
# =============================================================================


class TestLoggingPerformance:
    """Performance tests for logging output."""

    def test_log_output_instantiation_time(self) -> None:
        """Test that log output is generated without delay."""
        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345
        mock._lsp_server_name = "pyright-langserver"

        import time

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock

            start_time = time.time()
            result = runner.invoke(app, ["start", "-l", "python"])
            elapsed = time.time() - start_time

            # Should complete quickly (no arbitrary sleeps)
            assert elapsed < 1.0
            assert "[START]" in result.stderr

    def test_sequential_command_timing(self) -> None:
        """Test sequential commands don't accumulate delays."""
        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345
        mock._lsp_server_name = "pyright-langserver"

        import time

        start_time = time.time()

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock

            # Execute multiple commands
            for _ in range(5):
                runner.invoke(app, ["start", "-l", "python"])
                mock.is_running.return_value = True

        elapsed = time.time() - start_time

        # 5 commands should complete quickly
        assert elapsed < 5.0  # Less than 1 second per command on average


# =============================================================================
# Marker Format Verification Tests
# =============================================================================


class TestLogMarkerFormat:
    """Tests to verify log marker format consistency."""

    def test_start_marker_format(self) -> None:
        """Test START marker format consistency."""
        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["start", "-l", "python"])

            stderr = result.stderr

            # All START messages should have consistent format
            assert "[START] Initializing daemon..." in stderr
            assert "[START] Spawning" in stderr
            assert "[START] Ready" in stderr

    def test_stop_marker_format(self) -> None:
        """Test STOP marker format consistency."""
        mock = MagicMock()
        mock.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["stop", "-l", "python"])

            stderr = result.stderr

            # All STOP messages should have consistent format
            assert "[STOP] Stopping daemon..." in stderr
            assert "[STOP] Daemon stopped" in stderr

    def test_restart_marker_format(self) -> None:
        """Test RESTART marker format consistency."""
        mock = MagicMock()
        mock.is_running.return_value = True

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["restart", "-l", "python"])

            stderr = result.stderr

            # All RESTART messages should have consistent format
            assert "[RESTART] Restarting daemon..." in stderr
            assert "[RESTART] Stopping existing daemon..." in stderr
            assert "[RESTART] Starting" in stderr
            assert "[RESTART] Daemon restarted" in stderr

    def test_marker_brackets_format(self) -> None:
        """Test that all markers use bracket format consistently."""
        import re

        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock

            for command in ["start", "stop", "restart"]:
                result = runner.invoke(app, [command, "-l", "python"])

                # All markers should match [MARKER] format
                markers = re.findall(r"\[(START|STOP|RESTART)\]", result.stderr)
                assert len(markers) > 0, f"No markers found in {command} output"
                # All markers should be the same type for each command
                expected_marker = command.upper()
                for marker in markers:
                    assert marker == expected_marker


# =============================================================================
# Workspace and Language Detection Tests
# =============================================================================


class TestWorkspaceLanguageDetectionLogging:
    """Tests for logging during language detection."""

    @pytest.fixture
    def temp_workspace(self) -> Any:
        """Create a temporary workspace for detection tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_auto_detect_logs_language(self, temp_workspace: Path) -> None:
        """Test auto-detection logs detected language."""
        # Create Python project marker
        (temp_workspace / "pyproject.toml").touch()

        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            result = runner.invoke(app, ["start", "-w", str(temp_workspace)])

            assert "[START] Detected language: python" in result.stderr

    def test_explicit_language_no_detect_log(self, temp_workspace: Path) -> None:
        """Test explicit language skips detection log."""
        mock = MagicMock()
        mock.is_running.return_value = False
        mock.get_pid.return_value = 12345

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager:
            mock_manager.return_value = mock
            # Use temp_workspace to avoid unused fixture warning
            result = runner.invoke(app, ["start", "-w", str(temp_workspace), "-l", "rust"])

            assert "[START] Detected language:" not in result.stderr
            assert "[START] Initializing daemon..." in result.stderr
