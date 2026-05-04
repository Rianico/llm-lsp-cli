"""Tests for uri_to_absolute_path utility consolidation (Issue 2a)."""

from pathlib import Path

import pytest


class TestUriToAbsolutePathExport:
    """Test that uri_to_absolute_path is exported from utils.uri module."""

    def test_uri_to_absolute_path_exported(self) -> None:
        """Verify uri_to_absolute_path is exported from utils.uri."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        assert callable(uri_to_absolute_path)

    def test_uri_module_has_function(self) -> None:
        """Verify module has the main function available."""
        import llm_lsp_cli.utils.uri as uri_module

        assert hasattr(uri_module, "uri_to_absolute_path")


class TestUriToAbsolutePathBehavior:
    """Test suite for consolidated URI-to-absolute-path utility."""

    def test_basic_file_uri(self, tmp_path: Path) -> None:
        """Convert simple file URI to absolute path."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("")

        uri = (workspace / "src" / "main.py").as_uri()
        result = uri_to_absolute_path(uri, workspace)

        # Now returns absolute path
        assert Path(result).is_absolute()
        assert result == str((workspace / "src" / "main.py").resolve())

    def test_non_file_uri_returns_as_is(self, tmp_path: Path) -> None:
        """Non-file URIs should be returned unchanged."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        uri = "https://example.com/file.py"
        result = uri_to_absolute_path(uri, tmp_path)

        assert result == "https://example.com/file.py"

    def test_file_outside_workspace_returns_absolute(self, tmp_path: Path) -> None:
        """Files outside workspace return absolute path."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        other = tmp_path / "other"
        other.mkdir()
        (other / "external.py").write_text("")

        uri = (other / "external.py").as_uri()
        result = uri_to_absolute_path(uri, workspace)

        # Should return absolute path
        assert Path(result).is_absolute()
        assert "external.py" in result

    def test_nested_absolute_path(self, tmp_path: Path) -> None:
        """Deeply nested paths handled correctly."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        nested = workspace / "a" / "b" / "c" / "d"
        nested.mkdir(parents=True)
        (nested / "deep.py").write_text("")

        uri = (nested / "deep.py").as_uri()
        result = uri_to_absolute_path(uri, workspace)

        # Now returns absolute path
        assert Path(result).is_absolute()
        assert result == str((nested / "deep.py").resolve())

    def test_workspace_root_file(self, tmp_path: Path) -> None:
        """File directly in workspace root."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "root.py").write_text("")

        uri = (workspace / "root.py").as_uri()
        result = uri_to_absolute_path(uri, workspace)

        # Now returns absolute path
        assert Path(result).is_absolute()
        assert result == str((workspace / "root.py").resolve())

    def test_uri_with_special_characters(self, tmp_path: Path) -> None:
        """URIs with encoded special characters."""
        from llm_lsp_cli.utils.uri import uri_to_absolute_path

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # File with space in name
        file_path = workspace / "file with spaces.py"
        file_path.write_text("")

        uri = file_path.as_uri()  # Will encode spaces as %20
        result = uri_to_absolute_path(uri, workspace)

        # Result should contain decoded name
        assert "file with spaces.py" in result
