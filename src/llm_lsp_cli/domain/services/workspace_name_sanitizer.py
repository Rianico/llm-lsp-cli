"""Workspace name sanitization service."""

from __future__ import annotations

import re

from ..exceptions import NameValidationError


class WorkspaceNameSanitizer:
    """Sanitizes workspace names for use in file paths.

    This service prevents dangerous characters, empty strings,
    and extremely long names from being used in file paths.

    Design: Pure functions with no side effects (immutability).
    """

    DEFAULT_MAX_LENGTH = 255
    _MULTI_UNDERSCORE_PATTERN = re.compile(r"_+")

    def __init__(self, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        """Initialize the sanitizer with a maximum length constraint.

        Args:
            max_length: Maximum allowed length for sanitized names.
        """
        self._max_length = max_length

    def sanitize(self, name: str) -> str:
        """Sanitize a workspace name for safe use in file paths.

        Args:
            name: The workspace name to sanitize.

        Returns:
            A sanitized name with dangerous characters removed/replaced.

        Raises:
            NameValidationError: If the name is empty, contains null bytes,
                or cannot be sanitized.
        """
        if not name:
            raise NameValidationError("Workspace name cannot be empty")

        if "\x00" in name:
            raise NameValidationError(
                f"Workspace name contains null byte: {repr(name)}"
            )

        result = name.strip().lower()
        result = result.replace("/", "_").replace("\\", "_").replace(" ", "_")
        result = self._MULTI_UNDERSCORE_PATTERN.sub("_", result)
        result = result.strip("_")

        if not result:
            raise NameValidationError(
                f"Workspace name becomes empty after sanitization: {repr(name)}"
            )

        if len(result) > self._max_length:
            result = result[: self._max_length]

        return result
