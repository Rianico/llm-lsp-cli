"""Unit tests for path resolver module."""

from pathlib import Path

import pytest

from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute


@pytest.fixture
def workspace_root(temp_dir: Path) -> Path:
    """Create a fake workspace root."""
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()
    return temp_dir


class TestNormalizeUriToAbsolute:
    """Tests for normalize_uri_to_absolute function."""

    def test_inside_workspace(self, workspace_root: Path) -> None:
        """Verify absolute path resolution for files inside workspace."""
        uri = f"file://{workspace_root}/src/utils.py"
        result = normalize_uri_to_absolute(uri, workspace_root)
        # Now returns absolute path (resolve() for macOS /var -> /private/var)
        assert result == str((workspace_root / "src" / "utils.py").resolve())

    def test_outside_workspace(self, workspace_root: Path) -> None:
        """Return absolute path for files outside workspace."""
        uri = "file:///other/file.py"
        result = normalize_uri_to_absolute(uri, workspace_root)
        assert result == "/other/file.py"

    def test_non_file_uri(self, workspace_root: Path) -> None:
        """Return non-file URIs unchanged."""
        uri = "https://example.com/file.py"
        result = normalize_uri_to_absolute(uri, workspace_root)
        assert result == "https://example.com/file.py"

    def test_empty_uri(self, workspace_root: Path) -> None:
        """Handle empty URI gracefully."""
        result = normalize_uri_to_absolute("", workspace_root)
        assert result == ""

    def test_nested_workspace(self, workspace_root: Path) -> None:
        """Handle deeply nested paths."""
        (workspace_root / "src/deep/nested").mkdir(parents=True)
        uri = f"file://{workspace_root}/src/deep/nested/file.py"
        result = normalize_uri_to_absolute(uri, workspace_root)
        # Now returns absolute path (resolve() for macOS /var -> /private/var)
        assert result == str((workspace_root / "src" / "deep" / "nested" / "file.py").resolve())

    def test_workspace_with_trailing_slash(self, workspace_root: Path) -> None:
        """Handle workspace with trailing slash."""
        uri = f"file://{workspace_root}/src/utils.py"
        # Add trailing slash to workspace
        workspace_with_slash = Path(str(workspace_root) + "/")
        result = normalize_uri_to_absolute(uri, workspace_with_slash)
        # Now returns absolute path (resolve() for macOS /var -> /private/var)
        assert result == str((workspace_root / "src" / "utils.py").resolve())
