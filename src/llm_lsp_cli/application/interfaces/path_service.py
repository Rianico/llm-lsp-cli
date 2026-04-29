"""Path service protocol interface."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PathServicePort(Protocol):
    """Protocol for path building operations.

    This protocol defines the interface for constructing standard
    runtime file paths (socket, PID, log files).
    """

    @staticmethod
    def build_socket_path(
        workspace_path: str, language: str, lsp_server_name: str | None = None
    ) -> Path:
        """Build the socket file path.

        Args:
            workspace_path: The workspace directory path.
            language: The language identifier.
            lsp_server_name: Optional LSP server name override.

        Returns:
            Absolute Path to the socket file.
        """
        ...

    @staticmethod
    def build_pid_file(
        workspace_path: str, language: str, lsp_server_name: str | None = None
    ) -> Path:
        """Build the PID file path.

        Args:
            workspace_path: The workspace directory path.
            language: The language identifier.
            lsp_server_name: Optional LSP server name override.

        Returns:
            Absolute Path to the PID file.
        """
        ...

    @staticmethod
    def build_log_file(
        workspace_path: str, language: str, lsp_server_name: str | None = None
    ) -> Path:
        """Build the log file path.

        Args:
            workspace_path: The workspace directory path.
            language: The language identifier.
            lsp_server_name: Optional LSP server name override.

        Returns:
            Absolute Path to the log file.
        """
        ...
