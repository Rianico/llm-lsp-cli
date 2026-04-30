"""LSP server validation with stderr alerts and GitHub URL hints.

This module validates LSP server executables and provides helpful
error messages with installation URLs for known language servers.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import typer

from llm_lsp_cli.infrastructure.config.exceptions import (
    ServerNotFoundError as BaseServerNotFoundError,
)

# =============================================================================
# Exceptions
# =============================================================================


class ServerNotFoundError(BaseServerNotFoundError):
    """Raised when LSP server executable cannot be found.

    Extended to support stderr alert printing before the exception is raised.
    """

    pass


class ServerValidationError(Exception):
    """Raised when server command validation fails (e.g., empty command)."""

    pass


# =============================================================================
# GitHub URL Mapping
# =============================================================================

# Maps LSP server commands to their GitHub installation URLs
# Extracted from DEFAULT_CONFIG comments in defaults.py
SERVER_INSTALL_URLS: dict[str, str] = {
    "basedpyright-langserver": "https://github.com/DetachHead/basedpyright",
    "pyright-langserver": "https://github.com/microsoft/pyright",
    "typescript-language-server": "https://github.com/typescript-language-server/typescript-language-server",
    "rust-analyzer": "https://github.com/rust-lang/rust-analyzer",
    "gopls": "https://github.com/golang/tools/tree/master/gopls",
    "jdtls": "https://github.com/eclipse-jdtls/eclipse.jdt.ls",
    "clangd": "https://github.com/llvm/llvm-project/tree/main/clang-tools-extra/clangd",
    "ccls": "https://github.com/MaskRay/ccls",
    "OmniSharp": "https://github.com/OmniSharp/omnisharp-roslyn",
    "csharp-ls": "https://github.com/razzmatazz/csharp-language-server",
}


# =============================================================================
# Public API
# =============================================================================


def validate_server_installed(
    command: str,
    language: str | None = None,  # noqa: ARG001
    *,
    is_custom_path: bool = False,
) -> str:
    """Validate that LSP server executable exists and is executable.

    Args:
        command: Server command or path to validate
        language: Language identifier (used for context, not currently used)
        is_custom_path: True if this is a user-specified custom path

    Returns:
        Resolved absolute path to the executable

    Raises:
        ServerValidationError: If command is empty or invalid
        ServerNotFoundError: If executable cannot be found or is not executable
    """
    # Validate command is not empty
    if not command or not command.strip():
        raise ServerValidationError("Server command is empty")

    # Determine if this looks like a path (vs a simple command name)
    expanded = _expand_path(command)
    is_path_like = _is_path_like(command, expanded)

    if is_path_like:
        # Validate as a file path
        return _validate_path(expanded, command, is_custom_path)
    else:
        # Validate via PATH lookup
        return _validate_path_lookup(command, is_custom_path)


def get_install_url(command: str) -> str | None:
    """Get the GitHub installation URL for a known LSP server.

    Args:
        command: Server command name

    Returns:
        GitHub URL if known, None otherwise
    """
    return SERVER_INSTALL_URLS.get(command)


def print_server_not_found_alert(
    command: str,
    *,
    is_custom: bool = False,
    reason: str | None = None,
) -> None:
    """Print an alert to stderr about missing server.

    Args:
        command: The server command or path that was not found
        is_custom: True if this was a user-specified custom path
        reason: Optional reason for the failure (e.g., "not executable")
    """
    if is_custom:
        # Custom path: show error without GitHub URL
        message = f"Custom server path not found: {command}"
        if reason:
            message += f"\n  Reason: {reason}"
        message += "\n  Hint: Check that the path is correct and the file is executable."
    else:
        # Default server: show error with GitHub URL
        message = f"LSP server not found: {command}"
        if reason:
            message += f"\n  Reason: {reason}"

        install_url = get_install_url(command)
        if install_url:
            message += f"\n  Install from: {install_url}"
        else:
            message += (
                "\n  Hint: Install the language server or use --lang-server-path."
            )

    typer.secho(message, fg=typer.colors.RED, err=True)


# =============================================================================
# Private Implementation
# =============================================================================


def _expand_path(command: str) -> str:
    """Expand tilde and environment variables in path."""
    expanded = os.path.expandvars(command)
    expanded = os.path.expanduser(expanded)
    return expanded


def _is_path_like(original: str, expanded: str) -> bool:
    """Determine if command should be treated as a path (vs PATH lookup)."""
    if os.path.isabs(expanded):
        return True
    if "/" in original:
        return True
    return original.startswith(".") or original.startswith("..")


def _validate_path(expanded: str, original: str, is_custom: bool) -> str:
    """Validate a file path exists and is executable.

    Raises with alert printed to stderr if validation fails.
    """
    path = Path(expanded)

    if not path.exists():
        print_server_not_found_alert(original, is_custom=is_custom)
        raise ServerNotFoundError(original, resolved_path=expanded)

    if not path.is_file():
        print_server_not_found_alert(original, is_custom=is_custom, reason="Not a file")
        raise ServerNotFoundError(original, resolved_path=expanded)

    if not os.access(path, os.X_OK):
        print_server_not_found_alert(
            original,
            is_custom=is_custom,
            reason="File exists but is not executable (chmod +x required)",
        )
        raise ServerNotFoundError(original, resolved_path=expanded)

    return str(path.resolve())


def _validate_path_lookup(command: str, is_custom: bool) -> str:
    """Validate command exists in PATH.

    Raises with alert printed to stderr if validation fails.
    """
    resolved = shutil.which(command)

    if resolved:
        return resolved

    print_server_not_found_alert(command, is_custom=is_custom)
    raise ServerNotFoundError(command)
