"""Tests for UidValidator infrastructure component."""

import os

from llm_lsp_cli.infrastructure.ipc.auth.uid_validator import UidValidator


class TestUidValidator:
    """Test suite for UidValidator."""

    def test_uid_validator_current_user(self) -> None:
        """UidValidator retrieves current user UID correctly."""
        # Arrange
        validator = UidValidator()

        # Assert
        assert validator.validate(os.getuid())

    def test_uid_validator_matches_os(self) -> None:
        """UidValidator validates UID correctly."""
        # Arrange
        validator = UidValidator()

        # Act
        is_same = validator.validate(os.getuid())

        # Assert
        assert is_same

    def test_uid_validator_different_uid(self) -> None:
        """UidValidator rejects different UIDs."""
        # Arrange
        validator = UidValidator()
        current_uid = os.getuid()
        different_uid = current_uid + 1

        # Act
        is_same = validator.validate(different_uid)

        # Assert
        assert not is_same

    def test_uid_validator_strict_mode(self) -> None:
        """UidValidator supports strict mode configuration."""
        # Arrange
        validator_strict = UidValidator(strict_mode=True)
        validator_lenient = UidValidator(strict_mode=False)

        # Assert
        assert validator_strict.should_validate()
        assert not validator_lenient.should_validate()
