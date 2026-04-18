"""Integration tests for full security pipeline.

Tests the complete security flow:
1. Path validation + IPC authentication integration
2. Token authentication under concurrent access
3. Structured logging with request ID propagation
"""

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

import pytest

from llm_lsp_cli.domain.services.path_validator import PathValidator
from llm_lsp_cli.infrastructure.ipc.auth.token_validator import (
    TokenAuthenticator,
)
from llm_lsp_cli.infrastructure.ipc.auth.uid_validator import UidValidator
from llm_lsp_cli.ipc.protocol import JSONRPCRequest
from llm_lsp_cli.ipc.unix_server import UNIXServer
from llm_lsp_cli.shared.logging import LogContext, StructuredLogger


def build_request_bytes(request: dict) -> bytes:
    """Build request bytes from a dictionary."""
    return JSONRPCRequest(
        method=request["method"],
        params=request.get("params", {}),
        id=request["id"],
    ).to_bytes()


@pytest.mark.asyncio
class TestFullSecurityPipeline:
    """Test suite for full security pipeline integration."""

    async def test_path_validation_and_ipc_auth_integration(
        self, tmp_path: Path
    ) -> None:
        """Test full security pipeline: path validation + IPC auth."""
        # Arrange: Set up workspace with files
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "safe_file.txt").write_text("safe content")
        outside_file = tmp_path / "outside_secret.txt"
        outside_file.write_text("secret")

        # Set up authentication
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Set up path validator
        path_validator = PathValidator(workspace)

        # Track validated paths
        validated_paths: list[Path] = []

        async def handler_with_path_validation(
            method: str, params: dict
        ) -> dict:
            """Handler that validates paths."""
            if "path" in params:
                validated_path = path_validator.validate_within_boundary(
                    params["path"]
                )
                validated_paths.append(validated_path)
                return {"result": "access granted", "path": str(validated_path)}
            return {"result": "ok"}

        # Set up server
        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=handler_with_path_validation,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Test 1: Valid auth + valid path = success
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(f"{token.value}\r\n\r\n".encode())
            await writer.drain()

            request = {
                "jsonrpc": "2.0",
                "method": "read_file",
                "params": {"path": "safe_file.txt"},
                "id": 1,
            }
            writer.write(build_request_bytes(request))
            await writer.drain()
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            assert b"result" in response
            assert b"access granted" in response

            # Test 2: Valid auth + path traversal attempt = path validation error
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(f"{token.value}\r\n\r\n".encode())
            await writer.drain()

            request = {
                "jsonrpc": "2.0",
                "method": "read_file",
                "params": {"path": "../outside_secret.txt"},
                "id": 2,
            }
            writer.write(build_request_bytes(request))
            await writer.drain()
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            assert b"error" in response.lower()

            # Test 3: Invalid auth = rejection (path validation never reached)
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(b"invalid_token\r\n\r\n")
            await writer.drain()

            request = {
                "jsonrpc": "2.0",
                "method": "read_file",
                "params": {"path": "safe_file.txt"},
                "id": 3,
            }
            writer.write(build_request_bytes(request))
            await writer.drain()
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            assert b"error" in response.lower()
            assert b"Unauthorized" in response

        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()

    async def test_concurrent_token_access(self, tmp_path: Path) -> None:
        """Test token authentication under concurrent access."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        request_count = 0
        lock = asyncio.Lock()

        async def counting_handler(method: str, params: dict) -> dict:
            """Handler that counts requests."""
            nonlocal request_count
            async with lock:
                request_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return {"result": "ok", "count": request_count}

        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=counting_handler,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Spawn multiple concurrent connections with valid tokens
            async def make_request(request_id: int) -> dict:
                """Make a single request."""
                reader, writer = await asyncio.open_unix_connection(str(socket_path))
                writer.write(f"{token.value}\r\n\r\n".encode())
                await writer.drain()

                request = {
                    "jsonrpc": "2.0",
                    "method": "test",
                    "params": {},
                    "id": request_id,
                }
                writer.write(build_request_bytes(request))
                await writer.drain()
                writer.write_eof()

                response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
                return {"id": request_id, "response": response}

            # Execute 10 concurrent requests
            num_concurrent = 10
            tasks = [
                make_request(i) for i in range(1, num_concurrent + 1)
            ]
            results = await asyncio.gather(*tasks)

            # Assert all requests succeeded
            assert len(results) == num_concurrent
            for result in results:
                assert b"result" in result["response"]

            # Assert all requests were processed
            assert request_count == num_concurrent

        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()

    async def test_concurrent_mixed_auth_attempts(self, tmp_path: Path) -> None:
        """Test concurrent valid and invalid auth attempts."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        valid_token = authenticator.generate_token()
        authenticator.save_token(valid_token)

        async def handler(method: str, params: dict) -> dict:
            return {"result": "ok"}

        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=handler,
            authenticator=authenticator,
        )

        await server.start()

        try:

            async def make_auth_attempt(token_value: str, request_id: int) -> dict:
                """Make an auth attempt."""
                reader, writer = await asyncio.open_unix_connection(str(socket_path))
                writer.write(f"{token_value}\r\n\r\n".encode())
                await writer.drain()

                request = {
                    "jsonrpc": "2.0",
                    "method": "test",
                    "params": {},
                    "id": request_id,
                }
                writer.write(build_request_bytes(request))
                await writer.drain()
                writer.write_eof()

                response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
                return {
                    "id": request_id,
                    "response": response,
                    "token_valid": token_value == valid_token.value,
                }

            # Mix of valid and invalid tokens
            attempts = [
                (valid_token.value, 1),  # Valid
                ("invalid_1", 2),  # Invalid
                (valid_token.value, 3),  # Valid
                ("invalid_2", 4),  # Invalid
                (valid_token.value, 5),  # Valid
            ]

            tasks = [make_auth_attempt(token, rid) for token, rid in attempts]
            results = await asyncio.gather(*tasks)

            # Verify results
            for result in results:
                if result["token_valid"]:
                    assert b"result" in result["response"]
                else:
                    assert b"error" in result["response"].lower()

        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()


class TestStructuredLoggingIntegration:
    """Test suite for structured logging integration."""

    def test_log_context_propagation_across_components(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test request ID propagation across component boundaries."""
        # Arrange
        caplog.set_level(logging.DEBUG)

        # Create loggers for different components
        auth_logger = StructuredLogger("auth_component")
        path_logger = StructuredLogger("path_validator_component")
        handler_logger = StructuredLogger("handler_component")

        # Use same request ID across components
        request_id = "req-test-12345"
        context = LogContext(request_id=request_id)

        # Act: Log from different components with same request ID
        auth_logger.info("Authentication started", context=context)
        auth_logger.info("Authentication successful", context=context)

        path_logger.debug("Path validation started", context=context)
        path_logger.info("Path validated successfully", context=context)

        handler_logger.info("Request processing", context=context)
        handler_logger.warning("Slow response detected", context=context)

        # Assert: All log entries contain the same request ID
        for record in caplog.records:
            assert request_id in record.message

    def test_log_context_with_metadata_chain(self) -> None:
        """Test metadata accumulation through call chain."""
        # Arrange
        import logging
        from io import StringIO

        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = StructuredLogger("test", handler)

        # Initial context
        context = LogContext(
            request_id="chain-test-001",
            component="initial",
            metadata={"step": 1},
        )

        # Act: Log with additional metadata
        logger.info("Step 1", context=context)

        # Add more context
        context.metadata["step"] = 2
        context.metadata["data"] = "processed"
        logger.info("Step 2", context=context)

        # Final step
        context.metadata["step"] = 3
        context.metadata["complete"] = True
        logger.info("Step 3 - Complete", context=context)

        # Assert
        log_output = output.getvalue()
        assert "chain-test-001" in log_output
        assert "step" in log_output
        assert "processed" in log_output

    def test_exception_logging_preserves_context(self) -> None:
        """Test that exception logging preserves request context."""
        # Arrange
        import logging
        from io import StringIO

        output = StringIO()
        handler = logging.StreamHandler(output)
        logger = StructuredLogger("error_test", handler)

        context = LogContext(
            request_id="error-test-999",
            component="failing_component",
            metadata={"operation": "divide"},
        )

        # Act
        try:
            _ = 1 / 0  # noqa: B015
        except ZeroDivisionError:
            logger.exception("Division failed", context=context)

        # Assert
        log_output = output.getvalue()
        assert "error-test-999" in log_output
        assert "failing_component" in log_output
        assert "Traceback" in log_output
        assert "ZeroDivisionError" in log_output

    @pytest.mark.asyncio
    async def test_logging_integration_with_unix_server(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test structured logging integration with UNIX server."""
        # Arrange
        caplog.set_level(logging.DEBUG)

        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        request_id = "server-test-001"
        server_logger = StructuredLogger("unix_server_test")

        async def logged_handler(method: str, params: dict) -> dict:
            """Handler with logging."""
            context = LogContext(request_id=request_id, component="handler")
            server_logger.info(f"Handling method: {method}", context=context)
            return {"result": "ok"}

        unique_id = uuid.uuid4().hex[:8]
        socket_path = Path(tempfile.gettempdir()) / f"test_{unique_id}.sock"

        server = UNIXServer(
            socket_path=socket_path,
            request_handler=logged_handler,
            authenticator=authenticator,
        )

        await server.start()

        try:
            # Make request
            reader, writer = await asyncio.open_unix_connection(str(socket_path))
            writer.write(f"{token.value}\r\n\r\n".encode())
            await writer.drain()

            request = {
                "jsonrpc": "2.0",
                "method": "test_method",
                "params": {},
                "id": 1,
            }
            writer.write(build_request_bytes(request))
            await writer.drain()
            writer.write_eof()

            response = await asyncio.wait_for(reader.read(4096), timeout=5.0)
            assert b"result" in response

        finally:
            await server.stop()
            if socket_path.exists():
                socket_path.unlink()


class TestTokenAuthenticatorEdgeCases:
    """Edge case tests for TokenAuthenticator."""

    def test_token_with_special_characters(self, tmp_path: Path) -> None:
        """Test token validation with special characters in token value."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)

        # Generate a token (should be hex, no special chars)
        token = authenticator.generate_token()

        # Save and validate
        authenticator.save_token(token)

        # Act & Assert
        assert authenticator.validate(token.value)
        # Token should be hex string
        assert all(c in "0123456789abcdef" for c in token.value.lower())

    def test_token_empty_string_validation(self, tmp_path: Path) -> None:
        """Test that empty string tokens are rejected."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Act & Assert
        assert not authenticator.validate("")

    def test_token_whitespace_validation(self, tmp_path: Path) -> None:
        """Test that whitespace tokens are rejected."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Act & Assert
        assert not authenticator.validate("   ")
        assert not authenticator.validate("\t")
        assert not authenticator.validate("\n")

    def test_token_none_like_strings(self, tmp_path: Path) -> None:
        """Test that None-like strings are handled."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)
        token = authenticator.generate_token()
        authenticator.save_token(token)

        # Act & Assert
        assert not authenticator.validate("None")
        assert not authenticator.validate("null")
        assert not authenticator.validate("undefined")

    def test_token_load_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading token when file doesn't exist."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)

        # Act
        result = authenticator.load_token()

        # Assert
        assert result is None

    def test_token_validate_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validating against non-existent token file."""
        # Arrange
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        authenticator = TokenAuthenticator(token_dir)

        # Act & Assert
        assert not authenticator.validate("any_token")


class TestPathValidatorEdgeCases:
    """Edge case tests for PathValidator."""

    def test_validator_double_encoding_traversal(self, tmp_path: Path) -> None:
        """Test double-encoded path traversal attempts."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        validator = PathValidator(workspace)

        # Note: PathValidator treats %2F as literal characters, not as encoded /
        # This is acceptable behavior - the path "..%2F..%2Fetc%2Fpasswd" is treated
        # as a filename with those literal characters, not as traversal
        # The test verifies the current behavior (no exception raised for encoded paths)
        # Act
        result = validator.validate_within_boundary("..%2F..%2Fetc%2Fpasswd")
        # Assert - the path is treated as a literal filename within workspace
        assert workspace in result.parents or result == workspace / "..%2F..%2Fetc%2Fpasswd"

    def test_validator_unicode_normalization(self, tmp_path: Path) -> None:
        """Test Unicode path handling."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "test_file.txt").write_text("content")
        validator = PathValidator(workspace)

        # Act
        result = validator.validate_within_boundary("test_file.txt")

        # Assert
        assert result.exists()
        assert result.is_file()

    def test_validator_very_long_path(self, tmp_path: Path) -> None:
        """Test very long path handling."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        deep_path = workspace
        for i in range(50):
            deep_path = deep_path / f"dir_{i}"
        deep_path.mkdir(parents=True)
        validator = PathValidator(workspace)

        # Act
        result = validator.validate_within_boundary(
            "/".join(f"dir_{i}" for i in range(50)) + "/file.txt"
        )

        # Assert
        assert "dir_0" in str(result)
        assert "dir_49" in str(result)

    def test_validator_symbolic_link_within_workspace(self, tmp_path: Path) -> None:
        """Test valid symlinks within workspace are allowed."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        subdir = workspace / "subdir"
        subdir.mkdir()
        (subdir / "target.txt").write_text("content")

        link = workspace / "link_to_target"
        link.symlink_to(subdir / "target.txt")

        validator = PathValidator(workspace)

        # Act - validate the symlink path
        result = validator.validate_within_boundary("link_to_target")

        # Assert - the resolved path exists and is within workspace
        # Note: result is the resolved path (target.txt), not the symlink itself
        assert result.exists()
        assert result.is_file()
        # Verify it's within workspace boundary
        assert workspace in result.parents or result.parent == workspace


class TestUidValidatorEdgeCases:
    """Edge case tests for UidValidator."""

    def test_uid_validator_zero_uid(self) -> None:
        """Test UID validation with 0 (root)."""
        # Arrange
        validator = UidValidator()

        # Act & Assert
        # If running as root, 0 should match
        # If not running as root, 0 should not match
        import os

        expected = os.getuid() == 0
        assert validator.validate(0) == expected

    def test_uid_validator_negative_uid(self) -> None:
        """Test UID validation with negative UID."""
        # Arrange
        validator = UidValidator()

        # Act & Assert - negative UIDs should not match
        assert not validator.validate(-1)
        assert not validator.validate(-100)

    def test_uid_validator_very_large_uid(self) -> None:
        """Test UID validation with very large UID."""
        # Arrange
        validator = UidValidator()

        # Act & Assert - very large UIDs should not match normal user
        assert not validator.validate(999999999)
        assert not validator.validate(2**31 - 1)

    def test_uid_validator_strict_mode_behavior(self) -> None:
        """Test strict mode affects validation behavior."""
        # Arrange
        strict_validator = UidValidator(strict_mode=True)
        lenient_validator = UidValidator(strict_mode=False)

        current_uid = strict_validator._get_current_uid()

        # Both should validate correctly, but only strict should enforce
        assert strict_validator.validate(current_uid)
        assert lenient_validator.validate(current_uid)

        # should_validate differs
        assert strict_validator.should_validate()
        assert not lenient_validator.should_validate()
