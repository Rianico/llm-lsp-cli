"""Tests for UNIXServer authentication integration."""

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

import pytest

from llm_lsp_cli.infrastructure.ipc.auth.token_validator import TokenAuthenticator
from llm_lsp_cli.infrastructure.ipc.auth.uid_validator import UidValidator
from llm_lsp_cli.ipc.protocol import JSONRPCRequest
from llm_lsp_cli.ipc.unix_server import UNIXServer


def build_request_bytes(request: dict) -> bytes:
    """Build request bytes from a dictionary."""
    return JSONRPCRequest(
        method=request["method"],
        params=request.get("params", {}),
        id=request["id"],
    ).to_bytes()


async def mock_request_handler(method: str, params: dict) -> dict:
    """Mock request handler for testing."""
    return {"result": "ok"}


@pytest.mark.asyncio
class TestUNIXServerAuth:
    """Test suite for UNIXServer authentication."""

    async def test_server_rejects_invalid_token(self, tmp_path: Path) -> None:
        """UNIXServer rejects connections with invalid tokens."""
        # Arrange - use short unique names to avoid UNIX socket path limits
        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()

        authenticator = TokenAuthenticator(token_dir)
        authenticator.generate_token()  # Generate but don't use this token

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=mock_request_handler,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Act & Assert: Connect with invalid token
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(b"invalid_token\r\n\r\n")
            await writer.drain()

            response = await reader.read(4096)
            # Should receive error response
            assert b"error" in response.lower() or len(response) == 0
        finally:
            await server.stop()
            # Cleanup socket file
            if socket_path.exists():
                socket_path.unlink()

    async def test_server_accepts_valid_token(self, tmp_path: Path) -> None:
        """UNIXServer accepts connections with valid tokens."""
        # Arrange - use short unique names
        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()

        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        received_messages = []

        async def capture_handler(method: str, params: dict) -> dict:
            received_messages.append((method, params))
            return {"result": "ok", "method": method}

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=capture_handler,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Act: Connect with valid token and send request
            reader, writer = await asyncio.open_unix_connection(str(socket_path))

            # Send token first
            writer.write(f"{token.value}\r\n\r\n".encode())
            await writer.drain()

            # Send JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "method": "test",
                "params": {},
                "id": 1,
            }
            request_bytes = build_request_bytes(request)
            writer.write(request_bytes)
            await writer.drain()

            # Close write side to signal end of request
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)

            # Assert
            assert b"result" in response
            assert len(received_messages) == 1
            assert received_messages[0][0] == "test"
        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()

    async def test_server_validates_peer_uid(self, tmp_path: Path) -> None:
        """UNIXServer validates peer UID when configured."""
        # Arrange - use short unique names
        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()

        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        uid_validator = UidValidator(strict_mode=True)

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=mock_request_handler,
            authenticator=authenticator,
            uid_validator=uid_validator,
        )

        await server.start()

        try:
            # Act: Connect (current user should match)
            reader, writer = await asyncio.open_unix_connection(str(socket_path))

            # Send token
            writer.write(f"{token.value}\r\n\r\n".encode())
            await writer.drain()

            # Send request
            request = {"jsonrpc": "2.0", "method": "test", "params": {}, "id": 1}
            writer.write(build_request_bytes(request))
            await writer.drain()

            # Signal end of request
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)

            # Assert: Should succeed for same user
            assert b"result" in response or b"error" not in response.lower()
        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()

    async def test_server_missing_token(self, tmp_path: Path) -> None:
        """UNIXServer rejects connections without tokens."""
        # Arrange - use short unique names
        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()

        authenticator = TokenAuthenticator(token_dir)
        authenticator.generate_token()

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=mock_request_handler,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Act: Connect without sending token
            reader, writer = await asyncio.open_unix_connection(str(socket_path))

            # Send request without authentication (server should reject before processing)
            request = {"jsonrpc": "2.0", "method": "test", "params": {}, "id": 1}
            writer.write(build_request_bytes(request))
            await writer.drain()

            # Signal end of request
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)

            # Assert
            assert b"error" in response.lower() or b"Unauthorized" in response
        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()

    async def test_server_authentication_logs_failures(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """UNIXServer logs authentication failures."""
        # Arrange - use short unique names
        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()

        authenticator = TokenAuthenticator(token_dir)
        authenticator.generate_token()

        caplog.set_level(logging.WARNING)

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=mock_request_handler,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Act: Connect with invalid token
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(b"invalid_token\r\n\r\n")
            await writer.drain()

            await reader.read(4096)  # Wait for response
        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()

        # Assert
        assert "authentication" in caplog.text.lower() or "unauthorized" in caplog.text.lower()
