"""Token-based authentication for IPC communication."""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuthToken:
    """Represents an authentication token.

    Frozen dataclass ensures immutability to prevent token tampering.

    Attributes:
        value: The plaintext token value.
    """

    value: str


class TokenAuthenticator:
    """Provides token-based authentication for IPC communication.

    This service generates cryptographically secure tokens, manages
    token file storage with secure permissions, and validates tokens
    using timing-safe comparison to prevent timing attacks.

    Design: Immutability for AuthToken, secure defaults for file permissions.
    """

    TOKEN_FILE = "auth_token"
    TOKEN_LENGTH = 32  # Minimum token length in bytes

    def __init__(self, token_dir: Path) -> None:
        """Initialize the authenticator with a token directory.

        Args:
            token_dir: Directory for storing the token file.
        """
        self._token_dir = token_dir
        self._token_dir.mkdir(parents=True, exist_ok=True)

    def generate_token(self) -> AuthToken:
        """Generate a cryptographically secure authentication token.

        Returns:
            An AuthToken containing the plaintext value.
        """
        token_value = secrets.token_hex(self.TOKEN_LENGTH)
        return AuthToken(value=token_value)

    def save_token(self, token: AuthToken) -> Path:
        """Save a token to the token file with secure permissions.

        Args:
            token: The AuthToken to save.

        Returns:
            The path to the token file.
        """
        token_path = self._token_dir / self.TOKEN_FILE

        # Write token value to file
        token_path.write_text(token.value)

        # Set secure permissions (owner read/write only)
        token_path.chmod(0o600)

        return token_path

    def validate(self, token_value: str) -> bool:
        """Validate a token value against the stored token.

        Uses timing-safe comparison to prevent timing attacks.

        Args:
            token_value: The plaintext token value to validate.

        Returns:
            True if the token is valid, False otherwise.
        """
        if not token_value:
            return False

        token_path = self._token_dir / self.TOKEN_FILE

        if not token_path.exists():
            return False

        stored_token = token_path.read_text()

        # Use timing-safe comparison
        return hmac.compare_digest(stored_token, token_value)

    def load_token(self) -> AuthToken | None:
        """Load the token from the token file.

        Returns:
            An AuthToken if the file exists, None otherwise.
        """
        token_path = self._token_dir / self.TOKEN_FILE

        if not token_path.exists():
            return None

        token_value = token_path.read_text()
        return AuthToken(value=token_value)
