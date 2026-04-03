"""IPC communication module for llm-lsp-cli."""

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
    "UNIXClient",
    "RPCError",
    "UNIXServer",
]
