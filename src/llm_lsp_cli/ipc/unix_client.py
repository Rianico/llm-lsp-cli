# pyright: reportUnannotatedClassAttribute=false
# pyright: reportExplicitAny=false
# pyright: reportAny=false
"""UNIX socket client for CLI to daemon communication.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

import asyncio
from pathlib import Path
from typing import Any

from .protocol import (
    ERROR_INTERNAL_ERROR,
    JSONRPCResponse,
    build_request,
    parse_message,
)


class UNIXClient:
    """Async client for UNIX socket communication."""

    def __init__(self, socket_path: str | Path, timeout: float = 30.0):
        self.socket_path = Path(socket_path)
        self.timeout = timeout
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[Any]] = {}

    async def connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Connect to the UNIX socket."""
        if not self.socket_path.exists():
            raise FileNotFoundError(
                f"Socket not found: {self.socket_path}\n"
                "Is the daemon running? Start it with: llm-lsp-cli start"
            )

        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(str(self.socket_path)),
            timeout=self.timeout,
        )
        return reader, writer

    async def request(
        self,
        method: str,
        params: dict[str, Any],
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> Any:
        """
        Send a request and wait for response.

        If reader/writer not provided, creates a new connection.
        """
        self._request_id += 1
        request_id = self._request_id

        # Create future for response
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending[request_id] = future

        # Build and send request
        request = build_request(method, params, request_id)

        close_connection = False
        if reader is None or writer is None:
            reader, writer = await self.connect()
            close_connection = True

        try:
            writer.write(request.to_bytes())
            await writer.drain()

            # Read response
            response_data = await self._read_response(reader)

            if response_data is None:
                raise RuntimeError("No response from server")

            response = JSONRPCResponse.from_dict(response_data)

            if response.error:
                raise RPCError(
                    code=response.error.get("code", ERROR_INTERNAL_ERROR),
                    message=response.error.get("message", "Unknown error"),
                    data=response.error.get("data"),
                )

            return response.result

        finally:
            if close_connection and writer:
                writer.close()
                await writer.wait_closed()

            self._pending.pop(request_id, None)

    async def _read_response(self, reader: asyncio.StreamReader) -> dict[str, Any] | None:
        """Read and parse a response from the socket."""
        data = b""
        while True:
            chunk = await asyncio.wait_for(
                reader.read(4096),
                timeout=self.timeout,
            )
            if not chunk:
                break
            data += chunk

            # Try to parse
            try:
                parsed, _ = parse_message(data)
                if parsed is not None:
                    return parsed
            except ValueError:
                continue

        return None

    async def notify(
        self,
        method: str,
        params: dict[str, Any],
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> None:
        """Send a notification (no response expected)."""
        from .protocol import JSONRPCNotification

        notification = JSONRPCNotification(method=method, params=params)

        close_connection = False
        if reader is None or writer is None:
            reader, writer = await self.connect()
            close_connection = True

        try:
            writer.write(notification.to_bytes())
            await writer.drain()
        finally:
            if close_connection and writer:
                writer.close()
                await writer.wait_closed()

    async def close(self) -> None:
        """Clean up pending requests."""
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()


class RPCError(Exception):
    """RPC error from server."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

    def __str__(self) -> str:
        return f"RPC Error {self.code}: {self.message}"
