"""Unit tests for daemon signal handling and cleanup."""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.daemon import (
    DaemonManager,
    run_daemon,
)

# Import will fail until implemented - this is expected in RED phase
try:
    from llm_lsp_cli.daemon import cleanup_runtime_files
except ImportError:
    # Define stub for RED phase - tests will fail with AttributeError
    def cleanup_runtime_files(
        socket_path: Path,
        pid_file: Path,
        workspace: str,
        language: str,
    ) -> None:
        del socket_path, pid_file, workspace, language  # Suppress unused warnings
        raise AttributeError("cleanup_runtime_files not implemented yet")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def mock_server() -> AsyncMock:
    """Mock UNIXServer for run_daemon tests."""
    server = AsyncMock()
    server.start = AsyncMock()
    server.stop = AsyncMock()
    return server


@pytest.fixture
def capture_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Configure caplog to capture daemon logger output."""
    caplog.set_level(logging.DEBUG, logger="llm-lsp-cli.daemon")
    return caplog


# =============================================================================
# Cycle 1: cleanup_runtime_files() - Basic Functionality
# =============================================================================


class TestCleanupRuntimeFiles:
    """Tests for the standalone cleanup_runtime_files() function."""

    def test_cleanup_removes_existing_files(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """cleanup_runtime_files() removes socket and PID files when they exist."""
        # Arrange
        socket_path = tmp_path / "test.sock"
        pid_file = tmp_path / "daemon.pid"
        socket_path.touch()
        pid_file.touch()

        assert socket_path.exists()
        assert pid_file.exists()

        # Act
        with caplog.at_level(logging.INFO):
            cleanup_runtime_files(
                socket_path=socket_path,
                pid_file=pid_file,
                workspace="test-workspace",
                language="python",
            )

        # Assert
        assert not socket_path.exists(), "Socket file should be removed"
        assert not pid_file.exists(), "PID file should be removed"

        # Verify logging
        assert "[CLEANUP] Cleaning runtime files" in caplog.text
        assert "workspace=test-workspace" in caplog.text
        assert "language=python" in caplog.text
        assert "[CLEANUP] Cleanup complete" in caplog.text

    def test_cleanup_idempotent(self, tmp_path: Path) -> None:
        """cleanup_runtime_files() is safe to call multiple times."""
        # Arrange
        socket_path = tmp_path / "test.sock"
        pid_file = tmp_path / "daemon.pid"
        socket_path.touch()
        pid_file.touch()

        # First call - removes files
        cleanup_runtime_files(socket_path, pid_file, "test", "python")

        # Assert files removed
        assert not socket_path.exists()
        assert not pid_file.exists()

        # Act - Second call should not raise
        cleanup_runtime_files(socket_path, pid_file, "test", "python")

        # Assert - Test passes if no exception raised
        # Files should still not exist (no recreation)
        assert not socket_path.exists()
        assert not pid_file.exists()

    def test_cleanup_missing_files(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """cleanup_runtime_files() handles already-deleted files without errors."""
        # Arrange - paths that don't exist
        socket_path = tmp_path / "nonexistent.sock"
        pid_file = tmp_path / "nonexistent.pid"

        # Act - should not raise any exception
        with caplog.at_level(logging.DEBUG):
            cleanup_runtime_files(socket_path, pid_file, "test", "python")

        # Assert - logging should indicate files were already absent
        assert "Socket already absent" in caplog.text
        assert "PID file already absent" in caplog.text

    def test_cleanup_logs_permission_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """cleanup_runtime_files() logs OSError but continues with other file."""
        # Arrange
        socket_path = tmp_path / "test.sock"
        pid_file = tmp_path / "daemon.pid"
        socket_path.touch()
        pid_file.touch()

        # Make socket unreadable to trigger OSError on unlink
        # Note: This may not work on all systems; alternative is to mock unlink
        socket_path.chmod(0o000)

        with caplog.at_level(logging.ERROR):
            cleanup_runtime_files(socket_path, pid_file, "test", "python")

        # Assert - should log error for socket but still clean PID
        # On some systems (macOS), chmod may not prevent unlink as root
        assert "Failed to remove socket" in caplog.text or not socket_path.exists()
        assert not pid_file.exists(), "PID file should still be cleaned despite socket error"

        # Reset permissions for cleanup (only if file still exists)
        if socket_path.exists():
            socket_path.chmod(0o644)


# =============================================================================
# Cycle 5-8: run_daemon() Signal Handling Tests
# =============================================================================


class TestRunDaemonSignalHandling:
    """Tests for signal handler registration in run_daemon()."""

    @pytest.mark.asyncio
    async def test_run_daemon_registers_signal_handlers(
        self, tmp_path: Path, mock_server: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """run_daemon() registers handlers for SIGTERM, SIGINT, and SIGQUIT."""
        # Arrange
        socket_path = tmp_path / "test.sock"

        with (
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_server),
            patch("llm_lsp_cli.daemon.asyncio.get_event_loop") as mock_loop_getter,
        ):
            mock_loop = MagicMock()
            mock_loop_getter.return_value = mock_loop

            # Create shutdown event that never triggers (for controlled test)
            shutdown_event = MagicMock()
            shutdown_event.wait = AsyncMock(side_effect=asyncio.CancelledError())

            with (
                caplog.at_level(logging.INFO),
                patch("llm_lsp_cli.daemon.asyncio.Event", return_value=shutdown_event),
                pytest.raises(asyncio.CancelledError),
            ):
                await run_daemon(
                    socket_path=str(socket_path),
                    workspace_path=str(tmp_path),
                    language="python",
                )

            # Verify add_signal_handler was called 3 times (once per signal)
            signal_handler_calls = list(mock_loop.add_signal_handler.call_args_list)
            assert len(signal_handler_calls) == 3, "Should register 3 signal handlers"

            # Verify signal registration is logged
            assert "Registered signal handlers" in caplog.text

    @pytest.mark.asyncio
    async def test_run_daemon_cleanup_on_normal_exit(
        self, tmp_path: Path, mock_server: AsyncMock
    ) -> None:
        """run_daemon() calls cleanup_runtime_files() in finally block on normal shutdown."""
        # Arrange
        socket_path = tmp_path / "test.sock"
        pid_file = tmp_path / "daemon.pid"
        pid_file.touch()

        with (
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_server),
            patch("llm_lsp_cli.daemon.cleanup_runtime_files") as mock_cleanup,
            patch("llm_lsp_cli.daemon.asyncio.get_event_loop") as mock_loop_getter,
        ):
            mock_loop = MagicMock()
            mock_loop_getter.return_value = mock_loop

            # Mock signal handler registration
            mock_loop.add_signal_handler = MagicMock()

            # Create shutdown event that triggers immediately
            shutdown_event = MagicMock()
            shutdown_event.wait = AsyncMock()  # Returns immediately

            with patch("llm_lsp_cli.daemon.asyncio.Event", return_value=shutdown_event):
                # Simulate normal shutdown: server.start then wait, then stop
                mock_server.start = AsyncMock()

                await run_daemon(
                    socket_path=str(socket_path),
                    workspace_path=str(tmp_path),
                    language="python",
                    pid_file=pid_file,
                )

            # Assert - cleanup called with correct arguments
            mock_cleanup.assert_called_once()
            call_kwargs = mock_cleanup.call_args.kwargs
            assert call_kwargs["workspace"] == tmp_path.name
            assert call_kwargs["language"] == "python"

    @pytest.mark.asyncio
    async def test_run_daemon_cleanup_on_exception(
        self, tmp_path: Path, mock_server: AsyncMock
    ) -> None:
        """run_daemon() calls cleanup_runtime_files() even if exception occurs."""
        # Arrange
        socket_path = tmp_path / "test.sock"
        pid_file = tmp_path / "daemon.pid"

        with (
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_server),
            patch("llm_lsp_cli.daemon.cleanup_runtime_files") as mock_cleanup,
            patch("llm_lsp_cli.daemon.asyncio.get_event_loop") as mock_loop_getter,
        ):
            mock_loop = MagicMock()
            mock_loop_getter.return_value = mock_loop
            mock_loop.add_signal_handler = MagicMock()

            # Simulate exception during server.start()
            mock_server.start = AsyncMock(side_effect=RuntimeError("Server failed"))

            with pytest.raises(RuntimeError):
                await run_daemon(
                    socket_path=str(socket_path),
                    workspace_path=str(tmp_path),
                    language="python",
                    pid_file=pid_file,
                )

            # Assert - cleanup called despite exception
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_daemon_handles_cancelled_error(
        self, tmp_path: Path, mock_server: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """run_daemon() logs asyncio.CancelledError before re-raising."""
        # Arrange
        socket_path = tmp_path / "test.sock"

        with (
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_server),
            patch("llm_lsp_cli.daemon.cleanup_runtime_files"),
            patch("llm_lsp_cli.daemon.asyncio.get_event_loop") as mock_loop_getter,
        ):
            mock_loop = MagicMock()
            mock_loop_getter.return_value = mock_loop
            mock_loop.add_signal_handler = MagicMock()

            # Simulate task cancellation
            mock_server.start = AsyncMock(side_effect=asyncio.CancelledError())

            with caplog.at_level(logging.INFO):
                with pytest.raises(asyncio.CancelledError):
                    await run_daemon(
                        socket_path=str(socket_path),
                        workspace_path=str(tmp_path),
                        language="python",
                        pid_file=tmp_path / "daemon.pid",
                    )

                # Assert - cancellation logged
                assert "cancelled" in caplog.text.lower() or "[ASYNC]" in caplog.text


# =============================================================================
# Cycle 9-10: DaemonManager Integration Tests
# =============================================================================


class TestDaemonManagerIntegration:
    """Integration tests for DaemonManager signal handling."""

    def test_daemon_manager_start_exists(self) -> None:
        """DaemonManager.start() method exists and is callable."""
        # Arrange
        manager = DaemonManager(
            workspace_path="/test/workspace",
            language="python",
        )

        # Assert - method exists
        assert hasattr(manager, "start")
        assert callable(manager.start)

    def test_daemon_manager_stop_logs_signal_operations(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """DaemonManager.stop() logs all signal operations."""
        # Arrange
        manager = DaemonManager(
            workspace_path=str(tmp_path),
            language="python",
        )

        # Create fake PID file (process doesn't exist, testing stale detection)
        manager.pid_file.parent.mkdir(parents=True, exist_ok=True)
        manager.pid_file.write_text("99999")  # Fake PID

        with caplog.at_level(logging.WARNING):
            manager.stop()

        # Assert - stale PID detected and cleaned
        assert "Stale PID" in caplog.text or "not running" in caplog.text.lower()
