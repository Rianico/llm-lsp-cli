"""Tests for path resolution utilities in output/path_resolver.py.

This module tests the resolve_path_for_header function which handles both
file:// URIs and absolute paths for header display.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestResolvePathForHeader:
    """Test resolve_path_for_header function."""

    def test_resolve_path_file_uri(self) -> None:
        """file:// URI is converted to relative path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        result = resolve_path_for_header("file:///ws/src/main.py", "/ws")
        assert result == "src/main.py"

    def test_resolve_path_absolute_path(self) -> None:
        """Absolute path inside workspace is converted to relative path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        result = resolve_path_for_header("/ws/src/main.py", "/ws")
        assert result == "src/main.py"

    def test_resolve_path_nested(self) -> None:
        """Nested path is converted correctly."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        result = resolve_path_for_header("/ws/src/deep/file.py", "/ws")
        assert result == "src/deep/file.py"

    def test_resolve_path_outside_workspace(self) -> None:
        """Path outside workspace returns basename only."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        result = resolve_path_for_header("/other/file.py", "/ws")
        assert result == "file.py"

    def test_resolve_path_path_object(self) -> None:
        """Accepts Path object for file_path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        result = resolve_path_for_header(Path("/ws/src/main.py"), "/ws")
        assert result == "src/main.py"

    def test_resolve_path_workspace_path_object(self) -> None:
        """Accepts Path object for workspace_path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        result = resolve_path_for_header("/ws/src/main.py", Path("/ws"))
        assert result == "src/main.py"

    def test_resolve_path_already_relative(self) -> None:
        """Already relative path is returned as-is (may raise or return input)."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header

        # When input is already relative, relative_to will fail and return basename
        # Or it could return the input as-is - either behavior is acceptable
        result = resolve_path_for_header("src/main.py", "/ws")
        # Expected: either "main.py" (basename fallback) or "src/main.py" (passed through)
        # For this test, we expect it to return the path as-is or basename
        assert result in ("src/main.py", "main.py")
