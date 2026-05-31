"""Tests for daemon start with health check."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from llm_lsp_cli.daemon import DaemonManager


class TestStartWithHealthCheck:
    """Test daemon start checks health before starting."""

    @patch.object(DaemonManager, "_check_health", return_value=True)
    @patch.object(DaemonManager, "is_running", return_value=True)
    def test_start_skips_when_healthy(
        self,
        mock_is_running: MagicMock,
        mock_check_health: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should skip start when daemon is already running and healthy."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()

        manager = DaemonManager(str(workspace), "python")

        # start() should return without raising when healthy
        manager.start()

        # Health check should have been called
        mock_check_health.assert_called_once()

    @patch.object(DaemonManager, "_check_health", return_value=False)
    @patch.object(DaemonManager, "is_running", return_value=True)
    @patch.object(DaemonManager, "stop")
    def test_start_restarts_when_unhealthy(
        self,
        mock_stop: MagicMock,
        mock_is_running: MagicMock,
        mock_check_health: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should stop daemon when running but unhealthy."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()

        manager = DaemonManager(str(workspace), "python")

        # Mock the actual start process to avoid daemon context
        with patch("llm_lsp_cli.daemon.DaemonContext"):
            with patch("llm_lsp_cli.daemon.asyncio.run"):
                try:
                    manager.start()
                except Exception:
                    pass  # May fail due to mock, but stop() should be called

        # stop() should have been called when unhealthy
        mock_stop.assert_called_once()

    @patch.object(DaemonManager, "is_running", return_value=False)
    def test_start_when_not_running(
        self,
        mock_is_running: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Should start normally when daemon is not running."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()

        manager = DaemonManager(str(workspace), "python")

        # Mock the actual start process
        with patch("llm_lsp_cli.daemon.DaemonContext"):
            with patch("llm_lsp_cli.daemon.asyncio.run"):
                try:
                    manager.start()
                except Exception:
                    pass  # May fail due to mock

        # is_running should have been called
        mock_is_running.assert_called()
