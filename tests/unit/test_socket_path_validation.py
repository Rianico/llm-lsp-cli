"""Tests for socket path length validation."""

import pytest
from pathlib import Path
from unittest.mock import patch

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

    def test_socket_path_acceptable_length(self, tmp_path: Path) -> None:
        """Test that DaemonManager.start() allows socket path < 100 chars.

        Uses a mocked short temp directory to avoid macOS long temp path issues.
        """
        # Create a workspace with a short path name
        short_workspace = tmp_path / "short-ws"
        short_workspace.mkdir(parents=True, exist_ok=True)

        # Mock the runtime directory to use a short path
        with patch('llm_lsp_cli.config.path_builder.XdgPaths.get') as mock_get:
            mock_paths = type('MockPaths', (), {
                'runtime_dir': Path('/tmp/test'),
                'config_dir': tmp_path / 'config',
                'state_dir': tmp_path / 'state',
            })()
            mock_get.return_value = mock_paths

            manager = DaemonManager(
                workspace_path=str(short_workspace),
                language="python",
            )

            # Socket path should be acceptable (< 100 chars)
            socket_path_str = str(manager.socket_path)
            assert len(socket_path_str) < 100, f"Socket path ({len(socket_path_str)} chars) should be < 100"
