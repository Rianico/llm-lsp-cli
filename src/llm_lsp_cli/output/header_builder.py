"""Alert header builder for LSP commands.

This module provides the CommandInfo dataclass and build_alert_header function
for generating alert headers in TEXT output.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandInfo:
    """Information about an LSP command for header generation.

    Attributes:
        server_name: The display name of the LSP server
        command_name: The name of the LSP command (e.g., 'diagnostics')
        file_path: The file path for file-level commands, None for workspace-level
    """

    server_name: str
    command_name: str
    file_path: str | None


def build_alert_header(info: CommandInfo) -> str:
    """Build an alert header for an LSP command.

    Format:
    - File-level: '<Server>: <command> of <file>'
    - Workspace-level: '<Server>: <command>'

    Args:
        info: CommandInfo containing server name, command, and optional file path

    Returns:
        The formatted header string
    """
    if info.file_path:
        return f"{info.server_name}: {info.command_name} of {info.file_path}"
    else:
        return f"{info.server_name}: {info.command_name}"
