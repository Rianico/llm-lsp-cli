"""IPC transport protocol interface."""

from __future__ import annotations

from typing import Protocol


class IpcTransportPort(Protocol):
    """Protocol for IPC transport communication.

    This protocol defines the interface for sending and receiving
    messages over an IPC transport (e.g., UNIX domain socket).
    """

    async def send(self, message: dict[str, object] | bytes) -> bool:
        """Send a message over the transport.

        Args:
            message: The message to send, either as a dict or raw bytes.

        Returns:
            True if message was sent successfully, False otherwise.
        """
        ...

    async def receive(self) -> dict[str, object] | bytes | None:
        """Receive a message from the transport.

        Returns:
            The received message, or None if no message available.
        """
        ...

    async def close(self) -> None:
        """Close the transport connection.

        This method should clean up any resources associated with
        the transport.
        """
        ...
