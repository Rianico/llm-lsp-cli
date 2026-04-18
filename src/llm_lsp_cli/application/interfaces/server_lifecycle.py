"""Server lifecycle protocol interface."""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class ServerStatus(str, Enum):
    """Server lifecycle status enumeration."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ServerLifecyclePort(Protocol):
    """Protocol for server lifecycle management.

    This protocol defines the interface for starting, stopping,
    and checking the status of an LSP server.
    """

    async def start_server(self) -> bool:
        """Start the LSP server.

        Returns:
            True if server started successfully, False otherwise.
        """
        ...

    async def stop_server(self) -> bool:
        """Stop the LSP server.

        Returns:
            True if server stopped successfully, False otherwise.
        """
        ...

    async def get_status(self) -> ServerStatus:
        """Get the current server status.

        Returns:
            Current ServerStatus enum value.
        """
        ...

    async def restart_server(self) -> bool:
        """Restart the LSP server.

        Returns:
            True if server restarted successfully, False otherwise.
        """
        ...
