"""LSP server path resolution utility."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .exceptions import ServerNotFoundError, ServerPathValidationError


class ServerPathResolver:
    """Resolves LSP server executable paths from config commands.

    Supports:
    - Simple command names (PATH lookup via shutil.which)
    - Tilde expansion (~ and ~user)
    - Environment variable expansion ($VAR and ${VAR})
    - Absolute and relative paths

    Security:
    - Validates commands for shell metacharacters before expansion
    - Rejects commands containing: ; | & ` > < and $() substitution
    - Allows safe environment variable expansion ($VAR, ${VAR})
    """

    # Shell metacharacters that indicate injection attempts (always dangerous)
    DANGEROUS_METACHARACTERS = frozenset([';', '|', '&', '`', '>', '<'])

    @staticmethod
    def resolve(command: str) -> str:
        """Resolve command to absolute executable path.

        Algorithm:
        1. Validate command for shell metacharacters (BEFORE expansion)
        2. Expand ~ and environment variables
        3. Validate expanded command for shell metacharacters (defense in depth)
        4. If path-like (absolute or contains /), validate as executable file
        5. Otherwise, use shutil.which() for PATH lookup

        Args:
            command: Raw command string from config

        Returns:
            Absolute path to executable

        Raises:
            ServerPathValidationError: If command contains shell metacharacters
            ServerNotFoundError: If executable cannot be found or validated
        """
        # Validate BEFORE expansion
        ServerPathResolver._validate_command_safe(command)

        expanded = ServerPathResolver._expand_path(command)

        # Validate AFTER expansion (defense in depth)
        ServerPathResolver._validate_command_safe(expanded)

        if ServerPathResolver._is_path_like(command, expanded):
            return ServerPathResolver._validate_executable(expanded, command)

        # PATH lookup
        resolved = shutil.which(expanded)
        if resolved:
            return resolved

        raise ServerNotFoundError(command)

    @staticmethod
    def _validate_command_safe(command: str) -> None:
        """Validate command doesn't contain dangerous shell metacharacters.

        Allowed patterns:
        - $VAR and ${VAR} for environment variable expansion
        - ~ for tilde expansion
        - Normal path characters: alphanumeric, _, -, ., /

        Rejected patterns:
        - ; for command chaining
        - | for pipe
        - & for background execution
        - ` for backtick substitution
        - $() for command substitution
        - > < for redirects

        Args:
            command: Command string to validate

        Raises:
            ServerPathValidationError: If command contains dangerous metacharacters
        """
        if not command or not command.strip():
            raise ServerPathValidationError(
                command, "Command is empty or whitespace only"
            )

        # Check for command substitution $() first (before checking individual chars)
        if '$(' in command:
            raise ServerPathValidationError(
                command, "Contains command substitution: $()"
            )

        # Check for backtick substitution
        if '`' in command:
            raise ServerPathValidationError(
                command, "Contains backtick substitution"
            )

        # Check for other dangerous metacharacters
        for char in ServerPathResolver.DANGEROUS_METACHARACTERS:
            if char in command:
                raise ServerPathValidationError(
                    command, f"Contains shell metacharacter: {char!r}"
                )

    @staticmethod
    def _expand_path(command: str) -> str:
        """Expand tilde and environment variables.

        Args:
            command: Raw command string

        Returns:
            Expanded command string
        """
        # First expand environment variables
        expanded = os.path.expandvars(command)
        # Then expand tilde
        expanded = os.path.expanduser(expanded)
        return expanded

    @staticmethod
    def _is_path_like(original: str, expanded: str) -> bool:
        """Determine if command should be treated as a path.

        Args:
            original: Original command string
            expanded: Expanded command string

        Returns:
            True if command appears to be a path
        """
        # Absolute path
        if os.path.isabs(expanded):
            return True

        # Contains path separator (relative path or explicit path)
        if "/" in original:
            return True

        # Starts with . or .. (relative path)
        return original.startswith(".") or original.startswith("..")

    @staticmethod
    def _validate_executable(path: str, original_command: str) -> str:
        """Validate that path exists and is executable.

        Args:
            path: Expanded path to validate
            original_command: Original command for error messages

        Returns:
            Validated path

        Raises:
            ServerNotFoundError: If path doesn't exist or isn't executable
        """
        # Normalize path (remove trailing slashes, etc.)
        path_obj = Path(path).resolve()

        if not path_obj.exists():
            raise ServerNotFoundError(original_command, resolved_path=path)

        if not path_obj.is_file():
            raise ServerNotFoundError(original_command, resolved_path=path)

        if not os.access(path_obj, os.X_OK):
            raise ServerNotFoundError(original_command, resolved_path=path)

        return str(path_obj)
