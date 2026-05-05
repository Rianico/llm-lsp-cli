# pyright: reportUnannotatedClassAttribute=false
# pyright: reportAny=false
"""UID-based validation for strict mode IPC authentication.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct

logger = logging.getLogger(__name__)


class UidValidator:
    """Validates user IDs for IPC peer authentication.

    This service provides UID-based authentication for strict mode
    IPC communication, validating that the connecting peer has the
    same user ID as the daemon process.

    Design: Optional strict mode for deployment flexibility.
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the UID validator.

        Args:
            strict_mode: If True, UID validation is enforced.
        """
        self._strict_mode = strict_mode
        self._current_uid = self._get_current_uid()

    @staticmethod
    def _get_current_uid() -> int:
        """Get the current process user ID."""
        import os

        return os.getuid()

    def validate(self, peer_uid: int) -> bool:
        """Validate that a peer UID matches the current user.

        Args:
            peer_uid: The peer's user ID to validate.

        Returns:
            True if the UID matches, False otherwise.
        """
        return peer_uid == self._current_uid

    def should_validate(self) -> bool:
        """Check if UID validation should be performed.

        Returns:
            True if strict mode is enabled, False otherwise.
        """
        return self._strict_mode

    @staticmethod
    def get_peer_uid_from_writer(writer: asyncio.StreamWriter) -> int | None:
        """Get the peer UID from a StreamWriter.

        Args:
            writer: The asyncio StreamWriter to extract peer UID from.

        Returns:
            The peer UID if available, None otherwise.
        """
        try:
            transport = writer.transport
            if transport is None:
                return None

            sock = transport.get_extra_info("socket")
            if sock is None:
                return None

            peer_creds = sock.getsockopt(
                socket.SOL_SOCKET,
                getattr(socket, "SO_PEERCRED", 0),
            )
            uid: int
            uid, _, _ = struct.unpack("iii", peer_creds[:12])
            return uid
        except Exception:
            logger.debug("Could not retrieve peer UID")
            return None
