"""Tests for socket path validation with /tmp-based socket paths."""

import os
from pathlib import Path

from llm_lsp_cli.daemon import DaemonManager


class TestSocketPathLengthValidation:
    """Tests for socket path handling with /tmp-based paths."""

    def test_long_workspace_path_produces_short_socket_path(self, tmp_path: Path) -> None:
        """Long workspace paths should produce short socket paths under /tmp."""
        long_workspace_name = "a" * 80
        long_workspace = tmp_path / long_workspace_name
        long_workspace.mkdir(parents=True, exist_ok=True)

        manager = DaemonManager(
            workspace_path=str(long_workspace),
            language="python",
        )

        # Socket path should now be short (under /tmp)
        socket_path_str = str(manager.socket_path)
        assert len(socket_path_str) < 100, (
            f"Socket path ({len(socket_path_str)} chars) should be < 100"
        )
        assert f"/tmp/llm-lsp-cli-{os.getuid()}/" in socket_path_str

    def test_socket_path_uses_tmp_directory(self, tmp_path: Path) -> None:
        """Socket paths should be under /tmp/llm-lsp-cli/."""
        workspace = tmp_path / "test-workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        manager = DaemonManager(
            workspace_path=str(workspace),
            language="python",
        )

        socket_path_str = str(manager.socket_path)
        assert f"/tmp/llm-lsp-cli-{os.getuid()}/" in socket_path_str
        assert socket_path_str.endswith(".sock")
