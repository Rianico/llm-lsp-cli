"""Tests for TokenAuthenticator infrastructure component."""

import hmac
import stat
from pathlib import Path
from unittest.mock import patch

from llm_lsp_cli.infrastructure.ipc.auth.token_validator import AuthToken, TokenAuthenticator


class TestTokenAuthenticator:
    """Test suite for TokenAuthenticator."""

    def test_token_generation(self, tmp_path: Path) -> None:
        """TokenAuthenticator generates cryptographically secure tokens."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)

        # Act
        token = authenticator.generate_token()

        # Assert
        assert isinstance(token, AuthToken)
        assert len(token.value) >= 32  # Minimum token length

    def test_token_validation_success(self, tmp_path: Path) -> None:
        """TokenAuthenticator validates correct tokens."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Act
        is_valid = authenticator.validate(token.value)

        # Assert
        assert is_valid

    def test_token_validation_failure(self, tmp_path: Path) -> None:
        """TokenAuthenticator rejects invalid tokens."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Act & Assert
        assert not authenticator.validate("invalid_token")
        assert not authenticator.validate("")
        assert not authenticator.validate(token.value[:-1])  # Truncated

    def test_token_file_permissions(self, tmp_path: Path) -> None:
        """TokenAuthenticator creates token file with 0o600 permissions."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()

        # Act
        token_path = authenticator.save_token(token)

        # Assert
        mode = token_path.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_token_load_from_file(self, tmp_path: Path) -> None:
        """TokenAuthenticator loads tokens from file."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        original_token = authenticator.generate_token()
        authenticator.save_token(original_token)

        # Act
        loaded_token = authenticator.load_token()

        # Assert
        assert loaded_token is not None
        assert loaded_token.value == original_token.value

    def test_token_timing_safe_comparison(self, tmp_path: Path) -> None:
        """TokenAuthenticator uses timing-safe comparison."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Act: Verify hmac.compare_digest is used (implementation detail)
        with patch("hmac.compare_digest", wraps=hmac.compare_digest) as mock_compare:
            authenticator.validate(token.value)

        # Assert
        mock_compare.assert_called_once()
