"""Tests for daemon status display showing socket path and workspace symlink."""

import os
from pathlib import Path

from llm_lsp_cli.config.path_builder import RuntimePathBuilder


class TestStatusDisplayPaths:
    """Test that status display includes both socket path and workspace symlink."""

    def test_socket_path_in_status(self) -> None:
        """Status should include socket path under /tmp."""
        workspace = "/Users/me/my-project"
        socket_path = RuntimePathBuilder.build_socket_path(workspace, "python")
        assert f"/tmp/llm-lsp-cli-{os.getuid()}/" in str(socket_path)

    def test_workspace_socket_symlink_path(self) -> None:
        """Status should include workspace symlink path."""
        workspace = "/Users/me/my-project"
        expected_symlink = Path(workspace) / ".llm-lsp-cli" / "socket"
        assert str(expected_symlink) == "/Users/me/my-project/.llm-lsp-cli/socket"

    def test_workspace_log_path(self) -> None:
        """Status should include workspace log directory."""
        workspace = "/Users/me/my-project"
        log_path = RuntimePathBuilder.build_daemon_log_path(workspace, "python")
        assert ".llm-lsp-cli" in str(log_path)
        assert "/tmp/" not in str(log_path)
