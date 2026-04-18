"""Tests for daemon isolation with workspace-specific paths."""

from pathlib import Path
from unittest.mock import patch

import pytest

from llm_lsp_cli.config.manager import ConfigManager


class TestDaemonIsolation:
    """Tests for workspace-specific daemon isolation."""

    def test_build_socket_path_isolation(self, temp_dir: Path) -> None:
        """Test socket paths are isolated per workspace."""
        workspace_a = temp_dir / "project-a"
        workspace_b = temp_dir / "project-b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        socket_a = ConfigManager.build_socket_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        socket_b = ConfigManager.build_socket_path(
            workspace_path=str(workspace_b),
            language="python",
        )

        # Different workspaces should have different socket paths
        assert socket_a != socket_b
        # Both should be in their respective .llm-lsp-cli directories
        assert "project-a" in str(socket_a)
        assert "project-b" in str(socket_b)

    def test_build_pid_file_path_isolation(self, temp_dir: Path) -> None:
        """Test PID file paths are isolated per workspace."""
        workspace_a = temp_dir / "project-a"
        workspace_b = temp_dir / "project-b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        pid_a = ConfigManager.build_pid_file_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        pid_b = ConfigManager.build_pid_file_path(
            workspace_path=str(workspace_b),
            language="python",
        )

        assert pid_a != pid_b
        assert pid_a.suffix == ".pid"
        assert pid_b.suffix == ".pid"

    def test_build_log_file_path_isolation(self, temp_dir: Path) -> None:
        """Test log file paths are isolated per workspace."""
        workspace_a = temp_dir / "project-a"
        workspace_b = temp_dir / "project-b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        log_a = ConfigManager.build_log_file_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        log_b = ConfigManager.build_log_file_path(
            workspace_path=str(workspace_b),
            language="python",
        )

        assert log_a != log_b
        assert log_a.suffix == ".log"
        assert log_b.suffix == ".log"

    def test_same_workspace_same_language_same_path(self, temp_dir: Path) -> None:
        """Test same workspace + language produces consistent paths."""
        workspace = temp_dir / "my-project"
        workspace.mkdir()

        socket1 = ConfigManager.build_socket_path(
            workspace_path=str(workspace),
            language="python",
        )
        socket2 = ConfigManager.build_socket_path(
            workspace_path=str(workspace),
            language="python",
        )

        assert socket1 == socket2

    def test_same_workspace_different_language_different_path(self, temp_dir: Path) -> None:
        """Test same workspace with different languages produces different paths."""
        workspace = temp_dir / "my-project"
        workspace.mkdir()

        python_socket = ConfigManager.build_socket_path(
            workspace_path=str(workspace),
            language="python",
        )
        typescript_socket = ConfigManager.build_socket_path(
            workspace_path=str(workspace),
            language="typescript",
        )

        assert python_socket != typescript_socket
        # Socket names should use server command names from config
        assert python_socket.name.endswith(".sock")
        assert typescript_socket.name == "typescript-language-server.sock"

    def test_path_structure_includes_llm_lsp_cli(self, temp_dir: Path) -> None:
        """Test path structure includes .llm-lsp-cli directory."""
        workspace = temp_dir / "test-project"
        workspace.mkdir()

        socket = ConfigManager.build_socket_path(
            workspace_path=str(workspace),
            language="python",
        )

        # Path structure: base/.llm-lsp-cli/{server}.sock
        assert "llm-lsp-cli" in str(socket)
        assert socket.suffix == ".sock"

    def test_build_daemon_log_path_isolation(self, temp_dir: Path) -> None:
        """Test daemon log paths are isolated per workspace."""
        workspace_a = temp_dir / "project-a"
        workspace_b = temp_dir / "project-b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        daemon_log_a = ConfigManager.build_daemon_log_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        daemon_log_b = ConfigManager.build_daemon_log_path(
            workspace_path=str(workspace_b),
            language="python",
        )

        assert daemon_log_a != daemon_log_b
        assert daemon_log_a.name == "daemon.log"
        assert daemon_log_b.name == "daemon.log"
        # Both should be in their respective .llm-lsp-cli directories
        assert "project-a" in str(daemon_log_a)
        assert "project-b" in str(daemon_log_b)

    def test_daemon_log_path_different_from_lsp_log_path(self, temp_dir: Path) -> None:
        """Test daemon log path is different from LSP server log path."""
        workspace = temp_dir / "my-project"
        workspace.mkdir()

        daemon_log = ConfigManager.build_daemon_log_path(
            workspace_path=str(workspace),
            language="python",
        )
        lsp_log = ConfigManager.build_log_file_path(
            workspace_path=str(workspace),
            language="python",
        )

        assert daemon_log != lsp_log
        assert daemon_log.name == "daemon.log"
        assert lsp_log.name != "daemon.log"
        assert daemon_log.parent == lsp_log.parent

    def test_daemon_manager_has_daemon_log_file(self, temp_dir: Path) -> None:
        """Test DaemonManager has daemon_log_file attribute."""
        from llm_lsp_cli.daemon import DaemonManager

        workspace = temp_dir / "my-project"
        workspace.mkdir()

        manager = DaemonManager(workspace_path=str(workspace), language="python")

        assert hasattr(manager, "daemon_log_file")
        assert manager.daemon_log_file.name == "daemon.log"
        assert manager.log_file.name != "daemon.log"
        assert manager.log_file.name.endswith(".log")


class TestDaemonManagerIsolation:
    """Tests for DaemonManager using isolated paths."""

    @pytest.mark.asyncio
    async def test_request_handler_uses_workspace_path(self) -> None:
        """Test request handler passes workspace path to registry."""
        from llm_lsp_cli.daemon import RequestHandler

        handler = RequestHandler(workspace_path="/workspace/test-project", language="python")

        with patch.object(handler._registry, "request_definition") as mock_req:
            mock_req.return_value = []

            await handler.handle(
                "textDocument/definition",
                {
                    "workspacePath": "/workspace/test-project",
                    "filePath": "/workspace/test-project/main.py",
                    "line": 10,
                    "column": 5,
                },
            )

            mock_req.assert_awaited_once()
            call_args = mock_req.call_args
            assert call_args.kwargs["workspace_path"] == "/workspace/test-project"

    @pytest.mark.asyncio
    async def test_status_includes_workspace_info(self) -> None:
        """Test status response includes workspace information."""
        from llm_lsp_cli.daemon import RequestHandler

        handler = RequestHandler(workspace_path="/workspace/test-project", language="python")

        result = await handler.handle("status", {})

        assert "running" in result
        assert result["running"] is True
        assert result.get("workspace") == "/workspace/test-project"
        assert result.get("language") == "python"
