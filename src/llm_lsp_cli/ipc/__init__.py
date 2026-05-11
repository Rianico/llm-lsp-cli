"""IPC communication module for llm-lsp-cli."""

from .cli_params import (
    DaemonFileParams,
    DaemonPositionParams,
    DaemonRenameParams,
    DaemonSymbolQueryParams,
    DaemonWorkspaceParams,
)
from .method_registry import (
    METHOD_TYPES,
    MethodName,
    MethodTypePair,
    get_params_type,
    get_result_type,
)
from .models import (
    CompletionContext,
    CompletionParams,
    DaemonStatusResult,
    DefinitionParams,
    DocumentSymbolParams,
    EmptyParams,
    HoverParams,
    PingResult,
    Position,
    PrepareRenameParams,
    ReferenceContext,
    ReferenceParams,
    RenameParams,
    ShutdownResult,
    TextDocumentIdentifier,
    TextDocumentPositionParams,
    WorkspaceSymbolParams,
)
from .protocol import (
    ERROR_INTERNAL_ERROR,
    ERROR_INVALID_PARAMS,
    ERROR_INVALID_REQUEST,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE_ERROR,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    build_error,
    build_request,
    build_response,
    parse_message,
)
from .unix_client import RPCError, UNIXClient
from .unix_server import UNIXServer

__all__ = [
    # Protocol types
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCNotification",
    "build_request",
    "build_response",
    "build_error",
    "parse_message",
    "ERROR_PARSE_ERROR",
    "ERROR_INVALID_REQUEST",
    "ERROR_METHOD_NOT_FOUND",
    "ERROR_INVALID_PARAMS",
    "ERROR_INTERNAL_ERROR",
    # Client/Server
    "UNIXClient",
    "RPCError",
    "UNIXServer",
    # Method registry
    "METHOD_TYPES",
    "MethodName",
    "MethodTypePair",
    "get_params_type",
    "get_result_type",
    # Daemon RPC param models (CLI-to-daemon flat camelCase)
    "DaemonPositionParams",
    "DaemonFileParams",
    "DaemonWorkspaceParams",
    "DaemonRenameParams",
    "DaemonSymbolQueryParams",
    # Parameter models (LSP-style nested)
    "EmptyParams",
    "Position",
    "TextDocumentIdentifier",
    "TextDocumentPositionParams",
    "WorkspaceSymbolParams",
    "RenameParams",
    "DefinitionParams",
    "HoverParams",
    "DocumentSymbolParams",
    "CompletionContext",
    "CompletionParams",
    "ReferenceContext",
    "ReferenceParams",
    "PrepareRenameParams",
    # Result models
    "PingResult",
    "ShutdownResult",
    "DaemonStatusResult",
]
