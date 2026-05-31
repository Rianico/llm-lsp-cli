"""Typed request gateway for IPC communication with the daemon.

This module provides the TypedRequestGateway class which is the single
source of truth for method overloads, response unwrapping, and Pydantic
validation.
"""

from __future__ import annotations

from typing import Literal, cast, overload

from pydantic import BaseModel, TypeAdapter

from llm_lsp_cli.daemon import RESPONSE_KEYS
from llm_lsp_cli.ipc.cli_params import (
    DaemonFileParams,
    DaemonPositionParams,
    DaemonRenameParams,
    DaemonSymbolQueryParams,
    DaemonWorkspaceParams,
)
from llm_lsp_cli.ipc.method_registry import MethodName
from llm_lsp_cli.ipc.models import EmptyParams
from llm_lsp_cli.lsp.types import (
    CallHierarchyIncomingCall,
    CallHierarchyOutgoingCall,
    CompletionItem,
    DocumentSymbol,
    Hover,
    Location,
    PrepareRenameResult,
    SymbolInformation,
    WorkspaceEdit,
)

# Result type registry for response validation.
# Maps method name to (single_model | list_model, is_optional).
_SINGLE_ITEM_TYPES: dict[str, type[BaseModel]] = {
    "textDocument/hover": Hover,
    "textDocument/prepareRename": PrepareRenameResult,
    "textDocument/rename": WorkspaceEdit,
}

_LIST_ITEM_TYPES: dict[str, type[BaseModel]] = {
    "textDocument/definition": Location,
    "textDocument/references": Location,
    "textDocument/completion": CompletionItem,
    "textDocument/documentSymbol": DocumentSymbol,
    "workspace/symbol": SymbolInformation,
    "callHierarchy/incomingCalls": CallHierarchyIncomingCall,
    "callHierarchy/outgoingCalls": CallHierarchyOutgoingCall,
}

# Methods where None is a valid result (not an error)
_OPTIONAL_RESULT_METHODS: frozenset[str] = frozenset({
    "textDocument/hover",
    "textDocument/completion",
})


class TypedRequestGateway:
    """Async gateway for typed IPC requests to the daemon.

    Owns the full request pipeline:
    1. Extract workspace/language from params
    2. Serialize params to wire format
    3. Delegate to DaemonClient (auto-start + transport)
    4. Unwrap response using RESPONSE_KEYS
    5. Validate with Pydantic models
    6. Return typed results

    This is the single source of truth for method overloads.
    """

    def __init__(self, workspace_path: str, language: str) -> None:
        from llm_lsp_cli.daemon_client import DaemonClient

        self._workspace_path = workspace_path
        self._language = language
        self._client = DaemonClient(
            workspace_path=workspace_path,
            language=language,
        )

    # ====================================================================
    # @overload declarations (single source of truth)
    # ====================================================================

    @overload
    async def request(
        self,
        method: Literal["ping"],
        params: EmptyParams,
    ) -> object: ...

    @overload
    async def request(
        self,
        method: Literal["shutdown"],
        params: EmptyParams,
    ) -> object: ...

    @overload
    async def request(
        self,
        method: Literal["status"],
        params: EmptyParams,
    ) -> object: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/definition"],
        params: DaemonPositionParams,
    ) -> list[Location]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/hover"],
        params: DaemonPositionParams,
    ) -> Hover | None: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/documentSymbol"],
        params: DaemonFileParams,
    ) -> list[DocumentSymbol]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/completion"],
        params: DaemonPositionParams,
    ) -> list[CompletionItem] | None: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/references"],
        params: DaemonPositionParams,
    ) -> list[Location]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/prepareRename"],
        params: DaemonPositionParams,
    ) -> PrepareRenameResult: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/rename"],
        params: DaemonRenameParams,
    ) -> WorkspaceEdit: ...

    @overload
    async def request(
        self,
        method: Literal["workspace/symbol"],
        params: DaemonSymbolQueryParams,
    ) -> list[SymbolInformation]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/diagnostic"],
        params: DaemonFileParams,
    ) -> dict[str, object]: ...

    @overload
    async def request(
        self,
        method: Literal["workspace/diagnostic"],
        params: DaemonWorkspaceParams,
    ) -> dict[str, object]: ...

    @overload
    async def request(
        self,
        method: Literal["callHierarchy/incomingCalls"],
        params: DaemonPositionParams,
    ) -> list[CallHierarchyIncomingCall]: ...

    @overload
    async def request(
        self,
        method: Literal["callHierarchy/outgoingCalls"],
        params: DaemonPositionParams,
    ) -> list[CallHierarchyOutgoingCall]: ...

    @overload
    async def request(
        self,
        method: Literal["textDocument/didChange"],
        params: DaemonFileParams,
    ) -> None: ...

    @overload
    async def request(
        self,
        method: str,
        params: object,
    ) -> object: ...

    # ====================================================================
    # Implementation
    # ====================================================================

    async def request(
        self,
        method: str,
        params: object,
    ) -> object:
        """Send a typed request and return a validated response."""
        # Serialize params
        serialized = self._serialize_params(params)

        # Delegate to DaemonClient (handles auto-start + transport)
        raw_result = await self._client.request(
            cast(MethodName, method), serialized
        )

        # didChange is acknowledgment-only
        if method == "textDocument/didChange":
            return None

        # Diagnostics return raw dicts
        if method in ("textDocument/diagnostic", "workspace/diagnostic"):
            return raw_result

        # Unwrap and validate
        if isinstance(raw_result, dict):
            return self._unwrap_and_validate(method, raw_result)

        return raw_result

    async def notify(self, method: str, params: dict[str, object]) -> None:
        """Send a notification (no response expected)."""
        await self._client.notify(method, params)

    async def close(self) -> None:
        """Clean up resources."""
        await self._client.close()

    # ====================================================================
    # Internal helpers
    # ====================================================================

    @staticmethod
    def _serialize_params(params: object) -> dict[str, object]:
        """Serialize params to wire format."""
        if isinstance(params, BaseModel):
            return params.model_dump(mode="json", by_alias=True)
        if isinstance(params, dict):
            return params
        return {}

    @staticmethod
    def _unwrap_and_validate(method: str, result: dict[str, object]) -> object:
        """Unwrap response dict and validate with Pydantic."""
        response_key = RESPONSE_KEYS.get(method, "result")
        inner_value = result.get(response_key)

        if inner_value is None:
            if method in _OPTIONAL_RESULT_METHODS:
                return None
            return inner_value

        # Single-item returns
        if method in _SINGLE_ITEM_TYPES:
            model_type = _SINGLE_ITEM_TYPES[method]
            return TypeAdapter(model_type).validate_python(inner_value)

        # List returns
        if method in _LIST_ITEM_TYPES:
            if not isinstance(inner_value, list):
                return inner_value
            model_type = _LIST_ITEM_TYPES[method]
            return TypeAdapter(list[model_type]).validate_python(inner_value)  # type: ignore[valid-type]

        # Unknown method - return as-is
        return inner_value
