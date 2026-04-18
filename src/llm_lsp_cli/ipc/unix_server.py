"""UNIX socket server for daemon to handle CLI requests."""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from ..infrastructure.ipc.auth.token_validator import TokenAuthenticator
from ..infrastructure.ipc.auth.uid_validator import UidValidator
from .protocol import (
    ERROR_INTERNAL_ERROR,
    ERROR_PARSE_ERROR,
    build_error,
    build_response,
    parse_message,
)

logger = logging.getLogger(__name__)


class UNIXServer:
    """Async UNIX socket server for handling CLI requests."""

    def __init__(
        self,
        socket_path: str | Path,
        request_handler: Callable[[str, dict[str, Any]], Awaitable[Any]],
        authenticator: TokenAuthenticator | None = None,
        uid_validator: UidValidator | None = None,
    ):
        self.socket_path = Path(socket_path)
        self.request_handler = request_handler
        self.authenticator = authenticator
        self.uid_validator = uid_validator
        self._server: asyncio.AbstractServer | None = None
        self._clients: set[asyncio.Task[Any]] = set()

    async def start(self) -> None:
        """Start the UNIX socket server."""
        # Remove existing socket file
        if self.socket_path.exists():
            self.socket_path.unlink()

        # Ensure parent directory exists
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Start server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            str(self.socket_path),
        )

    async def stop(self) -> None:
        """Stop the UNIX socket server."""
        # Close all client connections
        for task in self._clients:
            task.cancel()

        if self._clients:
            await asyncio.gather(*self._clients, return_exceptions=True)
            self._clients.clear()

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Remove socket file
        if self.socket_path.exists():
            self.socket_path.unlink()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a client connection.

        Logs exceptions for debugging instead of silently swallowing them.
        Re-raises CancelledError to allow proper task cancellation.
        Requires authentication token before processing requests.
        """
        buffer = b""

        try:
            # First, read and validate authentication token
            if self.authenticator is not None:
                # Read token line (token followed by \r\n\r\n)
                try:
                    token_line = await asyncio.wait_for(
                        reader.readuntil(b"\r\n\r\n"), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Authentication timeout: no token received")
                    return
                except asyncio.IncompleteReadError:
                    logger.warning("Authentication failed: incomplete token")
                    return

                token_value = token_line.decode("utf-8").strip()

                if not self.authenticator.validate(token_value):
                    # Log authentication failure
                    logger.warning(
                        "Authentication failed: invalid or missing token"
                    )
                    # Send error response and close connection
                    error_response = build_error(
                        code=ERROR_INTERNAL_ERROR,
                        message="Unauthorized: invalid or missing token",
                        request_id=0,
                    )
                    writer.write(error_response.to_bytes())
                    await writer.drain()
                    return

                logger.debug("Client authenticated successfully")

            # Validate UID if strict mode is enabled
            if self.uid_validator is not None and self.uid_validator.should_validate():
                # Get peer UID from socket using UidValidator helper
                peer_uid = UidValidator.get_peer_uid_from_writer(writer)
                if peer_uid is not None and not self.uid_validator.validate(peer_uid):
                    logger.warning(
                        f"UID validation failed: peer UID {peer_uid} does not match"
                    )
                    error_response = build_error(
                        code=ERROR_INTERNAL_ERROR,
                        message="Unauthorized: UID mismatch",
                        request_id=0,
                    )
                    writer.write(error_response.to_bytes())
                    await writer.drain()
                    return

            # Process messages
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break

                buffer += chunk

                # Process complete messages
                while buffer:
                    parsed, buffer = parse_message(buffer)
                    if parsed is None:
                        break

                    await self._process_message(parsed, reader, writer)

        except asyncio.CancelledError:
            # Re-raise CancelledError - don't swallow it
            raise
        except asyncio.IncompleteReadError:
            # Expected during normal client disconnect - log at DEBUG
            logger.debug("Client disconnected (IncompleteReadError)")
        except asyncio.TimeoutError:
            logger.debug("Client connection timeout")
        except Exception:
            # Log exception with traceback for debugging
            logger.exception("Error handling client connection")
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def _process_message(
        self,
        data: dict[str, Any],
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process a parsed JSON-RPC message."""
        try:
            if "method" not in data:
                raise ValueError("Missing 'method' field")

            method = data["method"]
            params = data.get("params", {})
            request_id = data.get("id")

            # Check if it's a notification (no id)
            if request_id is None:
                # Notifications don't get responses
                await self._handle_notification(method, params)
                return

            # Handle request
            try:
                result = await self.request_handler(method, params)
                response = build_response(result, request_id)
            except Exception as e:
                response = build_error(
                    code=ERROR_INTERNAL_ERROR,
                    message=str(e),
                    request_id=request_id,
                )

            # Send response
            writer.write(response.to_bytes())
            await writer.drain()

        except ValueError as e:
            # Parse error
            if "id" in data:
                response = build_error(
                    code=ERROR_PARSE_ERROR,
                    message=str(e),
                    request_id=data["id"],
                )
                writer.write(response.to_bytes())
                await writer.drain()

        except Exception as e:
            # Internal error
            if "id" in data:
                response = build_error(
                    code=ERROR_INTERNAL_ERROR,
                    message=str(e),
                    request_id=data["id"],
                )
                writer.write(response.to_bytes())
                await writer.drain()

    async def _handle_notification(self, method: str, params: dict[str, Any]) -> None:
        """Handle a notification (no response)."""
        # For now, just log notifications
        pass
