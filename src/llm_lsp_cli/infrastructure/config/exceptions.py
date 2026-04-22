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


class ServerPathValidationError(ConfigError):
    """Raised when server command contains invalid shell metacharacters."""

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(
            f"Invalid server command: {command}\n"
            f"Reason: {reason}\n"
            f"Shell metacharacters (;|&$`() are not allowed."
        )


class ServerNotFoundError(ConfigError):
    """Raised when LSP server executable cannot be found or is not executable."""

    def __init__(self, command: str, resolved_path: str | None = None) -> None:
        import os

        # Sanitize resolved path - only show basename, not full path structure
        if resolved_path:
            safe_path = os.path.basename(resolved_path)
            super().__init__(
                f"LSP server executable not found: {command}\n\n"
                f"Attempted path: {safe_path}\n"  # Only basename
                f"Causes:\n"
                f"  - File does not exist at specified path\n"
                f"  - File exists but is not executable (chmod +x required)\n"
                f"  - Environment variable not set\n\n"
                f"Hint: Install the language server or specify a valid path in config.yaml"
            )
        else:
            # Handle empty command case
            if not command or not command.strip():
                super().__init__(
                    f"LSP server command is empty.\n\n"
                    f"Hint: Specify a valid server command in config.yaml"
                )
            else:
                super().__init__(
                    f"LSP server executable not found: {command}\n\n"
                    f"Hint: Install the language server or ensure it's in PATH, "
                    f"or specify a valid absolute path in config.yaml"
                )
