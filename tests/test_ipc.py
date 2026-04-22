"""Tests for IPC protocol and communication."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest

from llm_lsp_cli.ipc.protocol import (
    ERROR_INTERNAL_ERROR,
    ERROR_METHOD_NOT_FOUND,
    JSONRPCRequest,
    JSONRPCResponse,
    build_error,
    build_request,
    build_response,
    parse_message,
)
from llm_lsp_cli.ipc.unix_client import RPCError, UNIXClient
from llm_lsp_cli.ipc.unix_server import UNIXServer


class TestJSONRPCRequest:
    """Tests for JSONRPCRequest."""

    def test_to_dict(self) -> None:
        """Test request serialization to dict."""
        req = JSONRPCRequest(method="test", params={"key": "value"}, id=1)
        d = req.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"key": "value"},
            "id": 1,
        }

    def test_to_bytes(self) -> None:
        """Test request serialization to bytes."""
        req = JSONRPCRequest(method="test", params={}, id=1)
        data = req.to_bytes()
        assert b"Content-Length:" in data
        assert b"\r\n\r\n" in data
        assert b'"method":"test"' in data

    def test_from_dict(self) -> None:
        """Test request deserialization."""
        d = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"key": "value"},
            "id": 1,
        }
        req = JSONRPCRequest.from_dict(d)
        assert req.method == "test"
        assert req.params == {"key": "value"}
        assert req.id == 1


class TestJSONRPCResponse:
    """Tests for JSONRPCResponse."""

    def test_success_to_dict(self) -> None:
        """Test success response serialization."""
        resp = JSONRPCResponse(result={"data": "value"}, id=1)
        d = resp.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "result": {"data": "value"},
            "id": 1,
        }

    def test_error_to_dict(self) -> None:
        """Test error response serialization."""
        resp = JSONRPCResponse(
            result=None,
            id=1,
            error={"code": -32601, "message": "Method not found"},
        )
        d = resp.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": 1,
        }
        assert "result" not in d

    def test_to_bytes(self) -> None:
        """Test response serialization to bytes."""
        resp = JSONRPCResponse(result={"data": "value"}, id=1)
        data = resp.to_bytes()
        assert b"Content-Length:" in data
        assert b'"result"' in data


class TestBuildFunctions:
    """Tests for builder functions."""

    def test_build_request(self) -> None:
        """Test build_request function."""
        req = build_request("method", {"param": 1}, 42)
        assert req.method == "method"
        assert req.params == {"param": 1}
        assert req.id == 42

    def test_build_response(self) -> None:
        """Test build_response function."""
        resp = build_response({"result": "data"}, 42)
        assert resp.result == {"result": "data"}
        assert resp.id == 42
        assert resp.error is None

    def test_build_error(self) -> None:
        """Test build_error function."""
        resp = build_error(
            code=ERROR_METHOD_NOT_FOUND,
            message="Method not found",
            request_id=42,
        )
        assert resp.error is not None
        assert resp.error["code"] == ERROR_METHOD_NOT_FOUND
        assert resp.error["message"] == "Method not found"
        assert resp.id == 42

    def test_build_error_with_data(self) -> None:
        """Test build_error with data field."""
        resp = build_error(
            code=ERROR_INTERNAL_ERROR,
            message="Internal error",
            request_id=42,
            data={"detail": "something"},
        )
        assert resp.error is not None
        assert resp.error["data"] == {"detail": "something"}


class TestParseMessage:
    """Tests for message parsing."""

    def test_parse_complete_message(self) -> None:
        """Test parsing a complete message."""
        req = JSONRPCRequest(method="test", params={}, id=1)
        data = req.to_bytes()
        parsed, remaining = parse_message(data)
        assert parsed is not None
        assert parsed["method"] == "test"
        assert remaining == b""

    def test_parse_incomplete_header(self) -> None:
        """Test parsing incomplete header."""
        data = b"Content-Length: 100\r\n"
        parsed, remaining = parse_message(data)
        assert parsed is None
        assert remaining == data

    def test_parse_incomplete_body(self) -> None:
        """Test parsing incomplete body."""
        data = b"Content-Length: 100\r\n\r\n"
        parsed, remaining = parse_message(data)
        assert parsed is None
        assert remaining == data

    def test_parse_with_remaining_data(self) -> None:
        """Test parsing with extra data after message."""
        req = JSONRPCRequest(method="test", params={}, id=1)
        data = req.to_bytes() + b"extra data"
        parsed, remaining = parse_message(data)
        assert parsed is not None
        assert remaining == b"extra data"

    def test_parse_invalid_content_length(self) -> None:
        """Test parsing with invalid Content-Length."""
        data = b"Content-Length: abc\r\n\r\n"
        with pytest.raises(ValueError, match="Invalid Content-Length"):
            parse_message(data)

    def test_parse_missing_content_length(self) -> None:
        """Test parsing without Content-Length header."""
        data = b"\r\n\r\n{}"
        with pytest.raises(ValueError, match="Missing Content-Length"):
            parse_message(data)


class TestUNIXClientServer:
    """Integration tests for UNIX client and server."""

    @pytest.fixture
    def socket_path(self, temp_dir: Path) -> Path:
        """Create a temporary socket path."""
        return temp_dir / "test.sock"

    @pytest.fixture
    async def server(self, socket_path: Path) -> AsyncGenerator[UNIXServer, None]:
        """Create and start a test server."""

        async def handler(method: str, params: dict[str, Any]) -> Any:
            if method == "echo":
                return {"method": method, "params": params}
            elif method == "error":
                raise ValueError("Test error")
            else:
                return "ok"

        server = UNIXServer(str(socket_path), handler)
        await server.start()
        yield server
        await server.stop()

    @pytest.mark.asyncio
    async def test_request_response(self, socket_path: Path, server: UNIXServer) -> None:
        """Test basic request-response cycle."""
        client = UNIXClient(str(socket_path))
        result = await client.request("echo", {"key": "value"})
        assert result == {"method": "echo", "params": {"key": "value"}}

    @pytest.mark.asyncio
    async def test_request_unknown_method(self, socket_path: Path, server: UNIXServer) -> None:
        """Test request with unknown method."""
        client = UNIXClient(str(socket_path))
        result = await client.request("unknown", {})
        assert result == "ok"  # Default handler returns "ok"

    @pytest.mark.asyncio
    async def test_request_error(self, socket_path: Path, server: UNIXServer) -> None:
        """Test request that causes server error."""
        client = UNIXClient(str(socket_path))
        with pytest.raises(RPCError, match="Test error"):
            await client.request("error", {})

    @pytest.mark.asyncio
    async def test_connection_refused_socket_not_exists(self, temp_dir: Path) -> None:
        """Test connection fails when socket doesn't exist."""
        client = UNIXClient(str(temp_dir / "nonexistent.sock"))
        with pytest.raises(FileNotFoundError):
            await client.request("test", {})

    @pytest.mark.asyncio
    async def test_multiple_requests(self, socket_path: Path, server: UNIXServer) -> None:
        """Test multiple sequential requests."""
        client = UNIXClient(str(socket_path))

        for i in range(5):
            result = await client.request("echo", {"count": i})
            assert result["params"]["count"] == i
