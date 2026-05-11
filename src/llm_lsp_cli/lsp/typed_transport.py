"""Typed LSP transport wrapper with Pydantic validation.

This module provides a typed wrapper around the raw LSP transport that validates
all responses using Pydantic models before returning them to callers.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

from . import types as lsp
from .transport import StdioTransport

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    # Handler types for notification/request callbacks
    NotificationHandler = Callable[[dict[str, object]], None] | Callable[
        [dict[str, object]], Coroutine[object, object, None]
    ]
    RequestHandler = Callable[[dict[str, object]], object] | Callable[
        [dict[str, object]], Coroutine[object, object, object]
    ]

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


class TypedLSPTransport:
    """Typed wrapper around StdioTransport with Pydantic validation.

    This class wraps a raw LSP transport and provides typed methods that:
    1. Accept typed params (dict[str, object])
    2. Delegate to the underlying transport
    3. Validate responses using Pydantic models
    4. Return typed Pydantic model instances

    This eliminates the need for cast() calls in client code.

    Can be initialized in two ways:
    1. With an existing StdioTransport: TypedLSPTransport(transport)
    2. With creation parameters: TypedLSPTransport(command=..., args=..., ...)
    """

    def __init__(
        self,
        transport: StdioTransport | None = None,
        *,
        command: str | None = None,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        trace: bool = False,
    ) -> None:
        """Initialize typed transport wrapper.

        Args:
            transport: The underlying raw LSP transport (optional)
            command: LSP server command (if creating transport internally)
            args: LSP server arguments (if creating transport internally)
            cwd: Working directory for LSP server
            env: Environment variables for LSP server
            trace: Enable trace logging

        Either `transport` or `command` must be provided.
        """
        if transport is not None:
            self._transport: StdioTransport = transport
        elif command is not None:
            self._transport = StdioTransport(
                command=command,
                args=args or [],
                cwd=cwd,
                env=env,
                trace=trace,
            )
        else:
            raise ValueError("Either transport or command must be provided")

    def _get_timeout(self, timeout: float | None) -> float:
        """Resolve timeout value, using default if None."""
        return timeout if timeout is not None else _DEFAULT_TIMEOUT

    async def send_initialize(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.InitializeResult:
        """Send initialize request and validate response.

        Args:
            params: Initialize parameters
            timeout: Optional timeout in seconds

        Returns:
            Validated InitializeResult

        Raises:
            ValidationError: If response doesn't match InitializeResult schema
        """
        result: object = await self._transport.send_request(
            "initialize", params, timeout=self._get_timeout(timeout)
        )
        return lsp.InitializeResult.model_validate(result)

    async def send_hover(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.Hover | None:
        """Send textDocument/hover request and validate response.

        Args:
            params: Hover parameters
            timeout: Optional timeout in seconds

        Returns:
            Validated Hover or None if server returns null
        """
        result: object = await self._transport.send_request(
            "textDocument/hover", params, timeout=self._get_timeout(timeout)
        )
        if result is None:
            return None
        return lsp.Hover.model_validate(result)

    async def send_definition(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> list[lsp.Location]:
        """Send textDocument/definition request and validate response.

        Args:
            params: Definition parameters
            timeout: Optional timeout in seconds

        Returns:
            List of validated Locations
        """
        result: object = await self._transport.send_request(
            "textDocument/definition", params, timeout=self._get_timeout(timeout)
        )
        return self._validate_location_list(result)

    async def send_references(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> list[lsp.Location]:
        """Send textDocument/references request and validate response.

        Args:
            params: References parameters
            timeout: Optional timeout in seconds

        Returns:
            List of validated Locations
        """
        result: object = await self._transport.send_request(
            "textDocument/references", params, timeout=self._get_timeout(timeout)
        )
        return self._validate_location_list(result)

    async def send_completion(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.CompletionList | list[lsp.CompletionItem]:
        """Send textDocument/completion request and validate response.

        Args:
            params: Completion parameters
            timeout: Optional timeout in seconds

        Returns:
            CompletionList or list of CompletionItems
        """
        result: object = await self._transport.send_request(
            "textDocument/completion", params, timeout=self._get_timeout(timeout)
        )
        if result is None:
            return []

        # Response can be CompletionList or list[CompletionItem]
        if isinstance(result, list):
            items: list[lsp.CompletionItem] = []
            for item in cast(list[object], result):
                items.append(lsp.CompletionItem.model_validate(item))
            return items

        return lsp.CompletionList.model_validate(result)

    async def send_document_symbol(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> list[lsp.DocumentSymbol | lsp.SymbolInformation]:
        """Send textDocument/documentSymbol request and validate response.

        Args:
            params: Document symbol parameters
            timeout: Optional timeout in seconds

        Returns:
            List of DocumentSymbols or SymbolInformation
        """
        result: object = await self._transport.send_request(
            "textDocument/documentSymbol", params, timeout=self._get_timeout(timeout)
        )
        if result is None or not isinstance(result, list):
            return []

        # Response can be list[DocumentSymbol] or list[SymbolInformation]
        # We validate as DocumentSymbol first (more common for Python)
        validated: list[lsp.DocumentSymbol | lsp.SymbolInformation] = []
        for item in cast(list[object], result):
            try:
                validated.append(lsp.DocumentSymbol.model_validate(item))
            except ValidationError:
                # Fall back to SymbolInformation
                validated.append(lsp.SymbolInformation.model_validate(item))
        return validated

    async def send_workspace_symbol(
        self,
        params: Mapping[str, object],
        timeout: float | None = None,
    ) -> list[lsp.SymbolInformation]:
        """Send workspace/symbol request and validate response.

        Args:
            params: Workspace symbol parameters
            timeout: Optional timeout in seconds

        Returns:
            List of SymbolInformation
        """
        result: object = await self._transport.send_request(
            "workspace/symbol", params, timeout=self._get_timeout(timeout)
        )
        if result is None or not isinstance(result, list):
            return []
        symbols: list[lsp.SymbolInformation] = []
        for item in cast(list[object], result):
            symbols.append(lsp.SymbolInformation.model_validate(item))
        return symbols

    async def send_prepare_call_hierarchy(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> list[lsp.CallHierarchyItem]:
        """Send textDocument/prepareCallHierarchy request and validate response.

        Args:
            params: Prepare call hierarchy parameters
            timeout: Optional timeout in seconds

        Returns:
            List of CallHierarchyItems
        """
        result: object = await self._transport.send_request(
            "textDocument/prepareCallHierarchy",
            params,
            timeout=self._get_timeout(timeout),
        )
        if result is None or not isinstance(result, list):
            return []
        items: list[lsp.CallHierarchyItem] = []
        for item in cast(list[object], result):
            items.append(lsp.CallHierarchyItem.model_validate(item))
        return items

    async def send_incoming_calls(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> list[lsp.CallHierarchyIncomingCall]:
        """Send callHierarchy/incomingCalls request and validate response.

        Args:
            params: Incoming calls parameters
            timeout: Optional timeout in seconds

        Returns:
            List of CallHierarchyIncomingCall
        """
        result: object = await self._transport.send_request(
            "callHierarchy/incomingCalls",
            params,
            timeout=self._get_timeout(timeout),
        )
        if result is None or not isinstance(result, list):
            return []
        calls: list[lsp.CallHierarchyIncomingCall] = []
        for item in cast(list[object], result):
            calls.append(lsp.CallHierarchyIncomingCall.model_validate(item))
        return calls

    async def send_outgoing_calls(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> list[lsp.CallHierarchyOutgoingCall]:
        """Send callHierarchy/outgoingCalls request and validate response.

        Args:
            params: Outgoing calls parameters
            timeout: Optional timeout in seconds

        Returns:
            List of CallHierarchyOutgoingCall
        """
        result: object = await self._transport.send_request(
            "callHierarchy/outgoingCalls",
            params,
            timeout=self._get_timeout(timeout),
        )
        if result is None or not isinstance(result, list):
            return []
        calls: list[lsp.CallHierarchyOutgoingCall] = []
        for item in cast(list[object], result):
            calls.append(lsp.CallHierarchyOutgoingCall.model_validate(item))
        return calls

    async def send_diagnostic(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.DocumentDiagnosticReport:
        """Send textDocument/diagnostic request and validate response.

        Args:
            params: Diagnostic parameters (textDocument, previousResultId)
            timeout: Optional timeout in seconds

        Returns:
            Validated DocumentDiagnosticReport
        """
        result: object = await self._transport.send_request(
            "textDocument/diagnostic",
            params,
            timeout=self._get_timeout(timeout),
        )
        return lsp.DocumentDiagnosticReport.model_validate(result)

    async def send_workspace_diagnostic(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.WorkspaceDiagnosticReport:
        """Send workspace/diagnostic request and validate response.

        Args:
            params: Workspace diagnostic parameters
            timeout: Optional timeout in seconds

        Returns:
            Validated WorkspaceDiagnosticReport
        """
        result: object = await self._transport.send_request(
            "workspace/diagnostic",
            params,
            timeout=self._get_timeout(timeout),
        )
        return lsp.WorkspaceDiagnosticReport.model_validate(result)

    async def send_prepare_rename(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.PrepareRenameResult | lsp.Range | None:
        """Send textDocument/prepareRename request and validate response.

        Args:
            params: Prepare rename parameters (textDocument, position)
            timeout: Optional timeout in seconds

        Returns:
            PrepareRenameResult, Range, or None if rename is not allowed at position
        """
        result: object = await self._transport.send_request(
            "textDocument/prepareRename",
            params,
            timeout=self._get_timeout(timeout),
        )
        if result is None:
            return None
        # Response can be Range or PrepareRenameResult (with placeholder)
        # Range has 'start' and 'end' fields at top level
        if isinstance(result, dict):
            if "start" in result and "end" in result and "range" not in result:
                return lsp.Range.model_validate(result)
            # PrepareRenameResult has 'range' and optional 'placeholder'
            return lsp.PrepareRenameResult.model_validate(result)
        return None

    async def send_rename(
        self,
        params: dict[str, object],
        timeout: float | None = None,
    ) -> lsp.WorkspaceEdit | None:
        """Send textDocument/rename request.

        Args:
            params: Rename parameters (textDocument, position, newName)
            timeout: Optional timeout in seconds

        Returns:
            WorkspaceEdit with changes, or None if no changes
        """
        result: object = await self._transport.send_request(
            "textDocument/rename",
            params,
            timeout=self._get_timeout(timeout),
        )
        if result is None:
            return None
        if isinstance(result, dict):
            return lsp.WorkspaceEdit.model_validate(result)
        return None

    async def send_shutdown(
        self,
        timeout: float | None = None,
    ) -> None:
        """Send shutdown request.

        Args:
            timeout: Optional timeout in seconds
        """
        _ = await self._transport.send_request(
            "shutdown",
            None,
            timeout=self._get_timeout(timeout),
        )

    @staticmethod
    def _validate_location_list(result: object) -> list[lsp.Location]:
        """Validate a Location list response.

        Handles both Location[] and LocationLink responses.

        Args:
            result: Raw response from transport

        Returns:
            List of validated Locations
        """
        if result is None:
            return []

        if isinstance(result, list):
            locations: list[lsp.Location] = []
            for item in cast(list[object], result):
                # Handle LocationLink (has targetUri) vs Location (has uri)
                if isinstance(item, dict) and "targetUri" in item:
                    # Convert LocationLink to Location
                    link = lsp.LocationLink.model_validate(item)
                    locations.append(
                        lsp.Location(
                            uri=link.target_uri,
                            range=link.target_range,
                        )
                    )
                else:
                    locations.append(lsp.Location.model_validate(item))
            return locations

        # Single Location (shouldn't happen but handle gracefully)
        if isinstance(result, dict):
            return [lsp.Location.model_validate(result)]

        return []

    # =========================================================================
    # Delegate methods - pass through to underlying transport
    # =========================================================================

    async def send_notification(
        self, method: str, params: Mapping[str, object] | None = None
    ) -> None:
        """Send a notification (no response expected).

        Delegates to underlying transport.

        Args:
            method: LSP method name
            params: Optional notification parameters
        """
        await self._transport.send_notification(method, params)

    async def send_request_fire_and_forget(
        self, method: str, params: Mapping[str, object] | None = None
    ) -> None:
        """Send a request without waiting for response (fire-and-forget).

        Delegates to underlying transport.

        Args:
            method: LSP method name
            params: Optional request parameters
        """
        await self._transport.send_request_fire_and_forget(method, params)

    async def send_request(
        self, method: str, params: Mapping[str, object] | None = None, timeout: float = 30.0
    ) -> object:
        """Send a request and wait for response.

        WARNING: This method bypasses Pydantic validation and returns untyped
        responses. Prefer typed methods like send_initialize(), send_hover(), etc.
        for type-safe access to LSP responses.

        Delegates to underlying transport.

        Args:
            method: LSP method name
            params: Optional request parameters
            timeout: Timeout in seconds

        Returns:
            Raw response object from LSP server (unvalidated)
        """
        return await self._transport.send_request(method, params, timeout)

    async def start(self) -> None:
        """Start the underlying transport.

        Delegates to underlying transport.
        """
        await self._transport.start()

    async def stop(self) -> None:
        """Stop the underlying transport.

        Delegates to underlying transport.
        """
        await self._transport.stop()

    def on_notification(self, method: str, handler: "NotificationHandler") -> None:
        """Register a notification handler.

        Delegates to underlying transport.

        Args:
            method: LSP method name
            handler: Handler function (sync or async)
        """
        self._transport.on_notification(method, handler)

    def on_request(self, method: str, handler: "RequestHandler") -> None:
        """Register a server->client request handler.

        Delegates to underlying transport.

        Args:
            method: LSP method name
            handler: Handler function (sync or async)
        """
        self._transport.on_request(method, handler)
