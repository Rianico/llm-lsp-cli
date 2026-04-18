"""Configuration infrastructure exceptions."""

from __future__ import annotations


class ConfigError(Exception):
    """Base exception for configuration errors."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    def __init__(self, path: str) -> None:
        super().__init__(f"Configuration file not found: {path}")


class ConfigParseError(ConfigError):
    """Raised when configuration file cannot be parsed."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Failed to parse configuration {path}: {reason}")


class ConfigValidationError(ConfigError):
    """Raised when configuration fails schema validation."""

    def __init__(self, path: str, errors: list[str]) -> None:
        error_str = "; ".join(errors)
        super().__init__(f"Configuration validation failed for {path}: {error_str}")


class ConfigDirectoryError(ConfigError):
    """Raised when configuration directory cannot be created."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Failed to create configuration directory {path}: {reason}")


class ConfigWriteError(ConfigError):
    """Raised when configuration cannot be written."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Failed to write configuration {path}: {reason}")
