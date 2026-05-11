# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""JSON-RPC 2.0 protocol definitions for IPC communication.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


def serialize_for_json(obj: object) -> object:
    """Convert Pydantic models and nested structures to JSON-serializable types.

    This is the designated serialization boundary for IPC communication.
    Per ADR-0024: This module is allowed to use Any for dynamic JSON handling.

    Args:
        obj: Object to convert (can be Pydantic model, list, dict, or primitive)

    Returns:
        JSON-serializable version of the object
    """
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        result: dict[str, object] = {}
        for k, v in obj.items():
            if isinstance(k, str):
                result[k] = serialize_for_json(v)
        return result
    return obj


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request."""

    method: str
    params: dict[str, Any]
    id: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
            "id": self.id,
        }

    def to_bytes(self) -> bytes:
        """Serialize to bytes with Content-Length header."""
        body = json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        return header + body

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JSONRPCRequest":
        """Create from dictionary."""
        return cls(
            method=data["method"],
            params=data.get("params", {}),
            id=data["id"],
        )


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response."""

    result: object
    id: int
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        if self.error is not None:
            return {
                "jsonrpc": "2.0",
                "error": self.error,
                "id": self.id,
            }
        return {
            "jsonrpc": "2.0",
            "result": self.result,
            "id": self.id,
        }

    def to_bytes(self) -> bytes:
        """Serialize to bytes with Content-Length header."""
        body = json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        return header + body

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JSONRPCResponse":
        """Create from dictionary."""
        return cls(
            result=data.get("result"),
            id=data["id"],
            error=data.get("error"),
        )


@dataclass
class JSONRPCNotification:
    """JSON-RPC 2.0 notification (no response expected)."""

    method: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
        }

    def to_bytes(self) -> bytes:
        """Serialize to bytes with Content-Length header."""
        body = json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        return header + body


def build_request(method: str, params: dict[str, Any], request_id: int) -> JSONRPCRequest:
    """Build a JSON-RPC request."""
    return JSONRPCRequest(method=method, params=params, id=request_id)


def build_response(result: object, request_id: int) -> JSONRPCResponse:
    """Build a JSON-RPC response.

    Serializes Pydantic models to dict for JSON compatibility.
    """
    serialized = serialize_for_json(result)
    return JSONRPCResponse(result=serialized, id=request_id)


def build_error(code: int, message: str, request_id: int, data: object = None) -> JSONRPCResponse:
    """Build a JSON-RPC error response."""
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        error["data"] = data
    return JSONRPCResponse(result=None, id=request_id, error=error)


def parse_message(data: bytes) -> tuple[dict[str, Any] | None, bytes]:
    """
    Parse JSON-RPC message from bytes.

    Returns:
        tuple: (parsed_dict, remaining_bytes)

    Returns (None, data) if message is incomplete.
    """
    # Look for Content-Length header
    header_end = data.find(b"\r\n\r\n")
    if header_end == -1:
        return None, data

    header = data[:header_end].decode("utf-8")
    body_start = header_end + 4

    # Parse Content-Length
    content_length = None
    for line in header.split("\r\n"):
        if line.startswith("Content-Length: "):
            try:
                content_length = int(line.split(": ")[1])
            except (ValueError, IndexError):
                raise ValueError(f"Invalid Content-Length header: {line}") from None

    if content_length is None:
        raise ValueError("Missing Content-Length header")

    # Check if we have the full body
    body_end = body_start + content_length
    if len(data) < body_end:
        return None, data

    # Parse body
    body = data[body_start:body_end]
    remaining = data[body_end:]

    try:
        parsed = json.loads(body.decode("utf-8"))
        return parsed, remaining
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON body: {e}") from e


# JSON-RPC error codes
ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL_ERROR = -32603
