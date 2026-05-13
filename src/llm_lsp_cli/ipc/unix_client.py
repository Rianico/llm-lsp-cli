# pyright: reportExplicitAny=false
# pyright: reportAny=false
"""UNIX socket client for CLI to daemon communication.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Literal, overload, override

from llm_lsp_cli.lsp.types import (
    CompletionItem,
    DocumentSymbol,
    Hover,
    Location,
    PrepareRenameResult,
    SymbolInformation,
    WorkspaceEdit,
)

from .method_registry import MethodName
from .models import (
    CompletionParams,
    DaemonStatusResult,
    EmptyParams,
    PingResult,
    ReferenceParams,
    RenameParams,
    ShutdownResult,
    TextDocumentPositionParams,
    WorkspaceSymbolParams,
)
from .protocol import (
    ERROR_INTERNAL_ERROR,
    JSONRPCResponse,
    build_request,
    parse_message,
)


class UNIXClient:
    """Async client for UNIX socket communication."""

    socket_path: Path
    timeout: float
    _request_id: int
    _pending: dict[int, asyncio.Future[Any]]

    def __init__(self, socket_path: str | Path, timeout: float = 30.0):
        self.socket_path = Path(socket_path)
        self.timeout = timeout
        self._request_id = 0
        self._pending = {}

    # ========================================================================
    # @overload declarations for compile-time type safety
    # ========================================================================

    @overload
    async def request(
        self,
        method: Literal["ping"],
        params: EmptyParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> PingResult: ...

    @overload
    async def request(
        self,
        method: Literal["shutdown"],
        params: EmptyParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> ShutdownResult: ...

    @overload
    async def request(
        self,
        method: Literal["status"],
        params: EmptyParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> DaemonStatusResult: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/definition"],
        params: TextDocumentPositionParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> list[Location]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/hover"],
        params: TextDocumentPositionParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> Hover | None: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/documentSymbol"],
        params: TextDocumentPositionParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> list[DocumentSymbol]: ...

    @overload
    async def request(
        self,
        method: Literal["workspace/symbol"],
        params: WorkspaceSymbolParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> list[SymbolInformation]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/prepareRename"],
        params: TextDocumentPositionParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> PrepareRenameResult: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/rename"],
        params: RenameParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> WorkspaceEdit: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/references"],
        params: ReferenceParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> list[Location]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/completion"],
        params: CompletionParams,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> list[CompletionItem] | None: ...

    # Fallback overload for unknown methods - type error (unreachable)
    @overload
    async def request(
        self,
        method: MethodName,
        params: object,
        reader: asyncio.StreamReader | None = None,
        writer: asyncio.StreamWriter | None = None,
    ) -> object: ...

    # ========================================================================
    # Generic implementation (fallback for dynamic method calls)
    # ========================================================================

    async def request(
        self,
        method: str,
        params: Any,
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

        # Build and send request - convert Pydantic model to dict
        if hasattr(params, "model_dump"):
            params_dict = params.model_dump(mode="json", by_alias=True)
        else:
            params_dict = params

        request = build_request(method, params_dict, request_id)

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

            _ = self._pending.pop(request_id, None)

    async def connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Connect to the UNIX socket."""
        if not self.socket_path.exists():
            raise FileNotFoundError(
                f"Socket not found: {self.socket_path}\n"
                + "Is the daemon running? Start it with: llm-lsp-cli start"
            )

        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(str(self.socket_path)),
            timeout=self.timeout,
        )
        return reader, writer

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
                _ = future.cancel()
        self._pending.clear()


class RPCError(Exception):
    """RPC error from server."""

    code: int
    message: str
    data: object

    def __init__(self, code: int, message: str, data: object = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

    @override
    def __str__(self) -> str:
        return f"RPC Error {self.code}: {self.message}"
