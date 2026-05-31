"""Tests for daemon cleanup of unhealthy socket directories."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from llm_lsp_cli.daemon import cleanup_unhealthy_sockets


class TestCleanupUnhealthySockets:
    """Test cleanup removes unhealthy socket directories."""

    def test_removes_unhealthy_socket_dir(self, tmp_path: Path) -> None:
        """Should remove socket directory with no responding daemon."""
        # Create a fake socket directory
        socket_base = tmp_path / "llm-lsp-cli"
        socket_base.mkdir()
        socket_dir = socket_base / "project_abc12345"
        socket_dir.mkdir()
        (socket_dir / "pyright.sock").touch()

        # Mock no daemon running
        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_manager_class.return_value = mock_manager

            cleaned = cleanup_unhealthy_sockets(str(socket_base))

        assert len(cleaned) == 1
        assert not socket_dir.exists()

    def test_preserves_healthy_socket_dir(self, tmp_path: Path) -> None:
        """Should preserve socket directory with healthy daemon."""
        socket_base = tmp_path / "llm-lsp-cli"
        socket_base.mkdir()
        socket_dir = socket_base / "project_abc12345"
        socket_dir.mkdir()
        (socket_dir / "pyright.sock").touch()

        # Mock healthy ping response - need to mock at the import location inside the function
        mock_client = MagicMock()
        mock_client.request.return_value = {"status": "healthy", "daemon": True, "lsp_server": True}

        with patch("llm_lsp_cli.ipc.UNIXClient", return_value=mock_client) as mock_unix:
            # Also mock asyncio.run to return the response directly
            with patch("llm_lsp_cli.daemon.asyncio.run", return_value={"status": "healthy", "daemon": True, "lsp_server": True}):
                cleaned = cleanup_unhealthy_sockets(str(socket_base))

        assert len(cleaned) == 0
        assert socket_dir.exists()

    def test_removes_daemon_running_but_unhealthy(self, tmp_path: Path) -> None:
        """Should remove socket directory when daemon is running but unhealthy."""
        socket_base = tmp_path / "llm-lsp-cli"
        socket_base.mkdir()
        socket_dir = socket_base / "project_abc12345"
        socket_dir.mkdir()
        (socket_dir / "pyright.sock").touch()

        # Mock daemon running but unhealthy
        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = True
            mock_manager._check_health.return_value = False
            mock_manager_class.return_value = mock_manager

            cleaned = cleanup_unhealthy_sockets(str(socket_base))

        assert len(cleaned) == 1
        assert not socket_dir.exists()

    def test_returns_cleaned_directories(self, tmp_path: Path) -> None:
        """Should return list of cleaned directory paths."""
        socket_base = tmp_path / "llm-lsp-cli"
        socket_base.mkdir()
        socket_dir = socket_base / "project_abc12345"
        socket_dir.mkdir()

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.is_running.return_value = False
            mock_manager_class.return_value = mock_manager

            cleaned = cleanup_unhealthy_sockets(str(socket_base))

        assert isinstance(cleaned, list)
        assert all(isinstance(p, Path) for p in cleaned)
