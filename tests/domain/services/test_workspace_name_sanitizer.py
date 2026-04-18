"""Tests for WorkspaceNameSanitizer domain service."""

import pytest

from llm_lsp_cli.domain.services.workspace_name_sanitizer import (
    NameValidationError,
    WorkspaceNameSanitizer,
)


class TestWorkspaceNameSanitizer:
    """Test suite for WorkspaceNameSanitizer."""

    def test_sanitizer_rejects_empty_string(self) -> None:
        """WorkspaceNameSanitizer rejects empty strings."""
        # Arrange
        sanitizer = WorkspaceNameSanitizer()

        # Act & Assert
        with pytest.raises(NameValidationError):
            sanitizer.sanitize("")

    def test_sanitizer_handles_null_bytes(self) -> None:
        """WorkspaceNameSanitizer rejects null bytes."""
        # Arrange
        sanitizer = WorkspaceNameSanitizer()

        # Act & Assert
        with pytest.raises(NameValidationError):
            sanitizer.sanitize("\x00test")

        with pytest.raises(NameValidationError):
            sanitizer.sanitize("test\x00")

    def test_sanitizer_replaces_path_separators(self) -> None:
        """WorkspaceNameSanitizer replaces path separators."""
        # Arrange
        sanitizer = WorkspaceNameSanitizer()

        # Act
        result1 = sanitizer.sanitize("foo/bar")
        result2 = sanitizer.sanitize("foo\\bar")

        # Assert
        assert result1 == "foo_bar"
        assert result2 == "foo_bar"

    def test_sanitizer_enforces_max_length(self) -> None:
        """WorkspaceNameSanitizer enforces maximum length."""
        # Arrange
        sanitizer = WorkspaceNameSanitizer(max_length=10)
        long_name = "a" * 50

        # Act
        result = sanitizer.sanitize(long_name)

        # Assert
        assert len(result) <= 10

    def test_sanitizer_normalizes_names(self) -> None:
        """WorkspaceNameSanitizer normalizes names correctly."""
        # Arrange
        sanitizer = WorkspaceNameSanitizer()

        # Act
        result1 = sanitizer.sanitize("  My Project  ")
        result2 = sanitizer.sanitize("My__Project")
        result3 = sanitizer.sanitize("My/Project")

        # Assert
        assert result1 == "my_project"
        assert result2 == "my_project"
        assert result3 == "my_project"
