"""Tests for path resolution utilities in output/path_resolver.py.

This module tests the resolve_path_for_header_absolute function which handles both
file:// URIs and absolute paths for header display, always returning absolute paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestResolvePathForHeaderAbsolute:
    """Test resolve_path_for_header_absolute function."""

    def test_resolve_path_file_uri(self) -> None:
        """file:// URI is converted to absolute path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        result = resolve_path_for_header_absolute("file:///ws/src/main.py", "/ws")
        assert result == "/ws/src/main.py"

    def test_resolve_path_absolute_path(self) -> None:
        """Absolute path inside workspace is returned as absolute."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        result = resolve_path_for_header_absolute("/ws/src/main.py", "/ws")
        assert result == "/ws/src/main.py"

    def test_resolve_path_nested(self) -> None:
        """Nested path is converted correctly."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        result = resolve_path_for_header_absolute("/ws/src/deep/file.py", "/ws")
        assert result == "/ws/src/deep/file.py"

    def test_resolve_path_outside_workspace(self) -> None:
        """Path outside workspace returns absolute path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        result = resolve_path_for_header_absolute("/other/file.py", "/ws")
        assert result == "/other/file.py"

    def test_resolve_path_path_object(self) -> None:
        """Accepts Path object for file_path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        result = resolve_path_for_header_absolute(Path("/ws/src/main.py"), "/ws")
        assert result == "/ws/src/main.py"

    def test_resolve_path_workspace_path_object(self) -> None:
        """Accepts Path object for workspace_path."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        result = resolve_path_for_header_absolute("/ws/src/main.py", Path("/ws"))
        assert result == "/ws/src/main.py"

    def test_resolve_path_already_relative(self) -> None:
        """Already relative path is resolved to absolute."""
        from llm_lsp_cli.output.path_resolver import resolve_path_for_header_absolute

        # When input is already relative, resolve() makes it absolute from cwd
        result = resolve_path_for_header_absolute("src/main.py", "/ws")
        # Result will be absolute path from cwd resolution
        assert Path(result).is_absolute()
