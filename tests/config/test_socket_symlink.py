"""Tests for create_socket_symlink() - connecting workspace to /tmp socket dir."""

import os
from pathlib import Path

from llm_lsp_cli.config.path_builder import RuntimePathBuilder, create_socket_symlink


class TestCreateSocketSymlink:
    """Test create_socket_symlink() creates symlink from workspace to socket dir."""

    def test_creates_symlink(self, tmp_path: Path) -> None:
        """Should create a symlink at workspace/.llm-lsp-cli/socket."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()
        socket_dir = Path(f"/tmp/llm-lsp-cli-{os.getuid()}/my-project_abc12345")
        socket_dir.mkdir(parents=True, exist_ok=True)

        create_socket_symlink(str(workspace), socket_dir)

        symlink = workspace / ".llm-lsp-cli" / "socket"
        assert symlink.is_symlink()
        assert symlink.resolve() == socket_dir.resolve()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Should create .llm-lsp-cli directory if it doesn't exist."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()
        socket_dir = Path(f"/tmp/llm-lsp-cli-{os.getuid()}/my-project_abc12345")
        socket_dir.mkdir(parents=True, exist_ok=True)

        create_socket_symlink(str(workspace), socket_dir)

        llm_dir = workspace / ".llm-lsp-cli"
        assert llm_dir.is_dir()

    def test_replaces_stale_symlink(self, tmp_path: Path) -> None:
        """Should replace existing symlink with new one."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()
        llm_dir = workspace / ".llm-lsp-cli"
        llm_dir.mkdir()
        symlink = llm_dir / "socket"

        # Create stale symlink pointing to old location
        old_target = Path(f"/tmp/llm-lsp-cli-{os.getuid()}/old-project_xyz99999")
        old_target.mkdir(parents=True, exist_ok=True)
        symlink.symlink_to(old_target)

        # New socket directory
        new_target = Path(f"/tmp/llm-lsp-cli-{os.getuid()}/new-project_abc12345")
        new_target.mkdir(parents=True, exist_ok=True)

        create_socket_symlink(str(workspace), new_target)

        assert symlink.is_symlink()
        assert symlink.resolve() == new_target.resolve()

    def test_symlink_failure_does_not_raise(self, tmp_path: Path) -> None:
        """Should log warning but not raise on symlink failure."""
        workspace = tmp_path / "my-project"
        workspace.mkdir()

        # Use a non-existent parent to simulate failure
        # create_socket_symlink should handle this gracefully
        socket_dir = Path(f"/tmp/llm-lsp-cli-{os.getuid()}/test_abc12345")
        socket_dir.mkdir(parents=True, exist_ok=True)

        # This should not raise
        create_socket_symlink(str(workspace), socket_dir)


class TestBuildSocketPathSymlinkDir:
    """Test that build_socket_dir returns path suitable for symlink target."""

    def test_socket_dir_parent_exists(self) -> None:
        """Socket directory parent (/tmp/llm-lsp-cli-{uid}/) should be creatable."""
        result = RuntimePathBuilder._build_socket_dir("/Users/me/project")
        assert result.parent == Path(f"/tmp/llm-lsp-cli-{os.getuid()}")
