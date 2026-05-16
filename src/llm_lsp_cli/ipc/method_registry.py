"""Method type registry for IPC communication.

This module provides a registry that maps IPC method names to their
parameter and result types. This enables compile-time type checking
via @overload decorators and runtime validation via Pydantic models.

Usage:
    from llm_lsp_cli.ipc.method_registry import METHOD_TYPES, MethodName

    # Get types for a method
    params_type, result_type = METHOD_TYPES["ping"]

    # Use MethodName for type-safe method names
    def request(method: MethodName, params: BaseModel) -> BaseModel:
        ...
"""

from __future__ import annotations

from typing import Literal

from llm_lsp_cli.lsp.types import (
    CompletionItem,
    DocumentSymbol,
    Hover,
    Location,
    PrepareRenameResult,
    SymbolInformation,
    WorkspaceEdit,
)

from .models import (
    CompletionParams,
    DaemonStatusResult,
    DocumentSymbolParams,
    EmptyParams,
    PingResult,
    ReferenceParams,
    RenameParams,
    ShutdownResult,
    TextDocumentPositionParams,
    WorkspaceSymbolParams,
)

# MethodName Literal type for compile-time method name checking
type MethodName = Literal[
    "ping",
    "shutdown",
    "status",
    "textDocument/definition",
    "textDocument/hover",
    "textDocument/documentSymbol",
    "textDocument/completion",
    "workspace/symbol",
    "textDocument/prepareRename",
    "textDocument/rename",
    "textDocument/references",
]

# Type alias for method type pairs
# The result type can be a BaseModel subclass, a union type (Hover | None),
# or a generic alias (list[Location]). Using object allows all these cases.
type MethodTypePair = tuple[type[object], object]

# Registry mapping method names to (params_type, result_type)
# Note: result_type may be a generic like list[Location] which is represented
# at runtime as list. Type checkers understand the full type.
METHOD_TYPES: dict[MethodName, MethodTypePair] = {
    # Daemon control methods
    "ping": (EmptyParams, PingResult),
    "shutdown": (EmptyParams, ShutdownResult),
    "status": (EmptyParams, DaemonStatusResult),
    # LSP textDocument methods
    "textDocument/definition": (TextDocumentPositionParams, list[Location]),
    "textDocument/hover": (TextDocumentPositionParams, Hover | None),
    "textDocument/documentSymbol": (DocumentSymbolParams, list[DocumentSymbol]),
    "textDocument/completion": (CompletionParams, list[CompletionItem] | None),
    "textDocument/prepareRename": (TextDocumentPositionParams, PrepareRenameResult),
    "textDocument/rename": (RenameParams, WorkspaceEdit),
    "textDocument/references": (ReferenceParams, list[Location]),
    # LSP workspace methods
    "workspace/symbol": (WorkspaceSymbolParams, list[SymbolInformation]),
}


def get_params_type(method: MethodName) -> type[object]:
    """Get the parameter type for a method.

    Args:
        method: The IPC method name

    Returns:
        The Pydantic model class for the method's parameters
    """
    params_type, _ = METHOD_TYPES[method]
    return params_type


def get_result_type(method: MethodName) -> object:
    """Get the result type for a method.

    Args:
        method: The IPC method name

    Returns:
        The type for the method's result (may be a BaseModel subclass,
        a union type like Hover | None, or a generic alias like list[Location])
    """
    _, result_type = METHOD_TYPES[method]
    return result_type
