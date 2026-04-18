"""Tests for WorkspacePath value object."""

from pathlib import Path

import pytest

from llm_lsp_cli.domain.exceptions import PathValidationError
from llm_lsp_cli.domain.value_objects.workspace_path import WorkspacePath


class TestWorkspacePathValidatesExistence:
    """WorkspacePath rejects non-existent paths."""

    def test_workspace_path_validates_existence(self, temp_dir: Path) -> None:
        """WorkspacePath rejects non-existent paths."""
        non_existent = temp_dir / "does_not_exist"
        with pytest.raises(PathValidationError):
            WorkspacePath(non_existent)


class TestWorkspacePathResolvesToAbsolute:
    """WorkspacePath normalizes to absolute path."""

    def test_workspace_path_resolves_to_absolute(self, temp_dir: Path) -> None:
        """WorkspacePath normalizes to absolute path."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)
        assert ws_path.path.is_absolute()
        assert ws_path.path == workspace.resolve()


class TestResolveChildAllowsValidPaths:
    """resolve_child allows paths within workspace."""

    def test_resolve_child_allows_valid_paths(self, temp_dir: Path) -> None:
        """resolve_child allows paths within workspace."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        (workspace / "subdir").mkdir()
        ws_path = WorkspacePath(workspace)

        child = ws_path.resolve_child("subdir/file.py")
        assert child.is_absolute()
        assert str(child).startswith(str(workspace.resolve()))


class TestResolveChildPreventsTraversal:
    """resolve_child blocks path traversal attacks."""

    def test_resolve_child_prevents_traversal(self, temp_dir: Path) -> None:
        """resolve_child blocks path traversal attacks."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        other = temp_dir / "other"
        other.mkdir()
        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("../other/secret.txt")


class TestResolveChildDetectsSymlinkEscape:
    """resolve_child detects symlink-based workspace escape."""

    def test_resolve_child_detects_symlink_escape(self, temp_dir: Path) -> None:
        """resolve_child detects symlink-based workspace escape."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        outside = temp_dir / "outside"
        outside.mkdir()
        (workspace / "escape").symlink_to(outside)
        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("escape/secret.txt")
