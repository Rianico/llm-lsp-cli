"""Tests for RuntimePathBuilder._build_socket_dir() - socket path in /tmp."""

import os
from pathlib import Path

from llm_lsp_cli.config.path_builder import RuntimePathBuilder

_TMP_BASE = f"/tmp/llm-lsp-cli-{os.getuid()}"


class TestBuildSocketDir:
    """Test _build_socket_dir() produces paths under /tmp/llm-lsp-cli-{uid}/."""

    def test_socket_dir_under_tmp(self) -> None:
        """Socket directory should be under /tmp/llm-lsp-cli-{uid}/."""
        result = RuntimePathBuilder._build_socket_dir("/Users/me/my-project")
        assert str(result).startswith(f"{_TMP_BASE}/")

    def test_socket_dir_contains_sanitized_name(self) -> None:
        """Socket directory name should contain sanitized workspace name."""
        result = RuntimePathBuilder._build_socket_dir("/Users/me/my-project")
        dir_name = result.name
        assert dir_name.startswith("my-project_")

    def test_socket_dir_contains_hash(self) -> None:
        """Socket directory name should contain 8-char hash suffix."""
        result = RuntimePathBuilder._build_socket_dir("/Users/me/my-project")
        dir_name = result.name
        # Format: {sanitized}_{hash}
        parts = dir_name.split("_")
        assert len(parts) >= 2
        hash_part = parts[-1]
        assert len(hash_part) == 8
        # Should be hex characters
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_socket_dir_deterministic(self) -> None:
        """Same workspace path should produce same socket directory."""
        path = "/Users/me/my-project"
        result1 = RuntimePathBuilder._build_socket_dir(path)
        result2 = RuntimePathBuilder._build_socket_dir(path)
        assert result1 == result2

    def test_socket_dir_different_for_different_paths(self) -> None:
        """Different workspace paths should produce different socket directories."""
        result1 = RuntimePathBuilder._build_socket_dir("/Users/me/project-a")
        result2 = RuntimePathBuilder._build_socket_dir("/Users/me/project-b")
        assert result1 != result2

    def test_sanitized_name_max_20_chars(self) -> None:
        """Sanitized workspace name should be max 20 characters."""
        long_name = "a" * 50
        result = RuntimePathBuilder._build_socket_dir(f"/Users/me/{long_name}")
        dir_name = result.name
        # Extract sanitized part (before the last underscore + hash)
        sanitized = dir_name.rsplit("_", 1)[0]
        assert len(sanitized) <= 20

    def test_special_chars_replaced(self) -> None:
        """Special characters in workspace name should be replaced with _."""
        result = RuntimePathBuilder._build_socket_dir("/Users/me/my project@work!")
        dir_name = result.name
        sanitized = dir_name.rsplit("_", 1)[0]
        # Only alphanumeric, underscore, hyphen allowed
        assert all(c.isalnum() or c in "_-" for c in sanitized)

    def test_long_workspace_path_produces_short_socket_path(self) -> None:
        """Even very long workspace paths should produce socket paths <= 100 chars."""
        long_path = "/Users/zhengxk/development/ai/very-long-project-name-that-exceeds-normal-lengths/deeply/nested/subdirectory"
        result = RuntimePathBuilder._build_socket_dir(long_path)
        # The socket file path would be result / "{server}.sock"
        # Let's check the directory part is short enough
        socket_file = result / "pyright.sock"
        assert len(str(socket_file)) <= 100


class TestBuildSocketPathWithTmpDir:
    """Test build_socket_path() uses /tmp socket directory."""

    def test_build_socket_path_under_tmp(self) -> None:
        """build_socket_path should return path under /tmp/llm-lsp-cli-{uid}/."""
        result = RuntimePathBuilder.build_socket_path(
            workspace_path="/Users/me/my-project",
            language="python",
        )
        assert f"{_TMP_BASE}/" in str(result)

    def test_build_socket_path_ends_with_server_sock(self) -> None:
        """build_socket_path should end with {server_name}.sock."""
        result = RuntimePathBuilder.build_socket_path(
            workspace_path="/Users/me/my-project",
            language="python",
        )
        assert result.name.endswith(".sock")

    def test_build_socket_path_length_constraint(self) -> None:
        """build_socket_path should be <= 100 chars even for long workspaces."""
        long_path = "/Users/zhengxk/development/ai/very-long-project-name-that-exceeds-normal-lengths/deeply/nested/subdirectory"
        result = RuntimePathBuilder.build_socket_path(
            workspace_path=long_path,
            language="python",
        )
        assert len(str(result)) <= 100


class TestPidAndLogPathsUnchanged:
    """Test PID and log paths remain in workspace .llm-lsp-cli/."""

    def test_pid_file_in_workspace(self) -> None:
        """PID file should remain in workspace .llm-lsp-cli/."""
        workspace = "/Users/me/my-project"
        result = RuntimePathBuilder.build_pid_file_path(
            workspace_path=workspace,
            language="python",
        )
        assert ".llm-lsp-cli" in str(result)
        assert str(result).endswith(".pid")
        # Should NOT be under /tmp
        assert "/tmp/" not in str(result)

    def test_daemon_log_in_workspace(self) -> None:
        """Daemon log should remain in workspace .llm-lsp-cli/."""
        workspace = "/Users/me/my-project"
        result = RuntimePathBuilder.build_daemon_log_path(
            workspace_path=workspace,
            _language="python",
        )
        assert ".llm-lsp-cli" in str(result)
        assert result.name == "daemon.log"
        # Should NOT be under /tmp
        assert "/tmp/" not in str(result)
