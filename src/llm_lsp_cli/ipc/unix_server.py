"""UNIX socket server for daemon to handle CLI requests."""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

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
    ):
        self.socket_path = Path(socket_path)
        self.request_handler = request_handler
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
        """
        buffer = b""
        try:
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
