"""Tests for PathValidator domain service."""

from pathlib import Path

import pytest

from llm_lsp_cli.domain.exceptions import PathValidationError
from llm_lsp_cli.domain.services.path_validator import PathValidator


class TestPathValidator:
    """Test suite for PathValidator."""

    def test_validator_blocks_traversal(self, tmp_path: Path) -> None:
        """PathValidator blocks path traversal attempts."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        validator = PathValidator(workspace)

        # Act & Assert
        with pytest.raises(PathValidationError):
            validator.validate_within_boundary("../etc/passwd")

        with pytest.raises(PathValidationError):
            validator.validate_within_boundary("subdir/../../etc/passwd")

    def test_validator_blocks_symlink_escape(self, tmp_path: Path) -> None:
        """PathValidator blocks symlink escape attempts."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        symlink = workspace / "escape"
        symlink.symlink_to(outside)

        validator = PathValidator(workspace)

        # Act & Assert
        with pytest.raises(PathValidationError):
            validator.validate_within_boundary("escape/secret.txt")

    def test_validator_allows_valid_paths(self, tmp_path: Path) -> None:
        """PathValidator allows valid paths within workspace."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        subdir = workspace / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("test")

        validator = PathValidator(workspace)

        # Act
        result1 = validator.validate_within_boundary("file.txt")
        result2 = validator.validate_within_boundary("subdir/file.txt")

        # Assert
        assert result1 == workspace / "file.txt"
        assert result2 == subdir / "file.txt"

    def test_validator_handles_nonexistent_workspace(self, tmp_path: Path) -> None:
        """PathValidator rejects non-existent workspace."""
        # Arrange
        nonexistent = tmp_path / "does_not_exist"

        # Act & Assert
        with pytest.raises(PathValidationError):
            PathValidator(nonexistent)

    def test_validator_handles_absolute_paths(self, tmp_path: Path) -> None:
        """PathValidator handles absolute paths by resolving them."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        validator = PathValidator(workspace)

        # Act & Assert - absolute path outside workspace
        with pytest.raises(PathValidationError):
            validator.validate_within_boundary("/etc/passwd")

        # Act - absolute path inside workspace (via symlink resolution)
        internal_file = workspace / "test.txt"
        internal_file.write_text("test")

        # Assert
        result = validator.validate_within_boundary(str(internal_file))
        assert result == internal_file

    def test_validator_handles_null_bytes(self, tmp_path: Path) -> None:
        """PathValidator handles null bytes in paths safely."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        validator = PathValidator(workspace)

        # Act & Assert
        with pytest.raises(PathValidationError):
            validator.validate_within_boundary("file\x00.txt")
