"""Tests for socket path length validation."""

import pytest
from pathlib import Path

from llm_lsp_cli.daemon import DaemonManager


class TestSocketPathLengthValidation:
    """Tests for socket path length validation in DaemonManager.start()."""

    def test_socket_path_too_long_raises_error(self, tmp_path: Path) -> None:
        """Test that DaemonManager.start() raises error for socket path >= 100 chars."""
        # Create a workspace with a very long path name
        # We need to create a path that when combined with the runtime directory
        # and socket filename exceeds 100 characters
        long_workspace_name = "a" * 80  # Very long workspace name
        long_workspace = tmp_path / long_workspace_name
        long_workspace.mkdir(parents=True, exist_ok=True)

        manager = DaemonManager(
            workspace_path=str(long_workspace),
            language="python",
        )

        # Socket path should be too long
        socket_path_str = str(manager.socket_path)
        assert len(socket_path_str) >= 100, f"Socket path ({len(socket_path_str)} chars) should be >= 100"

        # start() should raise RuntimeError about socket path length
        with pytest.raises(RuntimeError, match="Socket path too long"):
            manager.start()

    def test_socket_path_flat_structure_correct(self, tmp_path: Path) -> None:
        """Test that socket paths use flat directory structure.

        Verifies the flat structure: {workspace}/.llm-lsp-cli/{server}.sock
        """
        # Create a workspace
        workspace = tmp_path / "test-workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        manager = DaemonManager(
            workspace_path=str(workspace),
            language="python",
        )

        # Socket path should use flat structure
        socket_path_str = str(manager.socket_path)
        assert socket_path_str.endswith(".llm-lsp-cli/basedpyright-langserver.sock")
        assert "test-workspace" in socket_path_str
