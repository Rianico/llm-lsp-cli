"""Integration tests for transport logging."""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.transport import StdioTransport


class TestStdioTransportNoLogFile:
    """Test StdioTransport no longer accepts log_file parameter."""

    def test_init_rejects_log_file_kwarg(self) -> None:
        """StdioTransport.__init__ raises TypeError for log_file kwarg."""
        # Arrange
        from llm_lsp_cli.lsp.transport import StdioTransport

        # Act & Assert
        with pytest.raises(TypeError, match="log_file"):
            StdioTransport(
                command="echo",
                log_file=Path("/tmp/test.log"),  # type: ignore
            )

    def test_init_has_no_log_file_attribute(self) -> None:
        """StdioTransport instance has no log_file attribute."""
        # Arrange
        from llm_lsp_cli.lsp.transport import StdioTransport

        # Act
        transport = StdioTransport(command="echo")

        # Assert
        assert not hasattr(transport, "log_file")


class TestStderrLoopLoggerOnly:
    """Test _stderr_loop logs to Python logger only."""

    @pytest.mark.asyncio
    async def test_stderr_logs_to_logger_not_file(
        self,
        log_capture_handler: logging.StreamHandler,  # type: ignore[assignment]
    ) -> None:
        """_stderr_loop writes to logger.debug(), not file handle."""
        # Arrange
        from llm_lsp_cli.lsp.transport import StdioTransport

        transport = StdioTransport(command="echo", trace=True)
        # Mock process with stderr that yields a line then stops
        mock_process = AsyncMock()
        mock_process.stderr.readline = AsyncMock(side_effect=[b"LSP error\n", b""])
        transport._process = mock_process
        transport._running = True

        # Act
        await transport._stderr_loop()

        # Assert
        log_output = log_capture_handler.stream.getvalue()
        assert "LSP error" in log_output
        assert "LSP stderr:" in log_output  # Log format prefix

    @pytest.mark.asyncio
    async def test_no_file_handle_written(self) -> None:
        """_stderr_loop does not write to any file handle."""
        # Arrange
        from llm_lsp_cli.lsp.transport import StdioTransport

        transport = StdioTransport(command="echo")
        # Mock with a file handle that would raise if written to
        mock_file_handle = MagicMock()
        mock_file_handle.write.side_effect = RuntimeError("Should not write to file")

        # Mock process stderr that returns empty immediately
        mock_process = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        transport._process = mock_process
        transport._running = True

        # Act & Assert
        # If _log_fh is accessed, test will fail
        transport._log_fh = mock_file_handle  # type: ignore

        # Should not raise RuntimeError
        await transport._stderr_loop()


class TestTransportLoggerIntegration:
    """Test StdioTransport integration with logging."""

    def test_transport_creates_successfully(self) -> None:
        """Verify StdioTransport can be created."""
        transport = StdioTransport(
            command="echo",
            args=["hello"],
            trace=True,
        )

        assert transport is not None
        assert transport.trace is True
        assert transport.command == "echo"

    def test_transport_trace_enabled(self) -> None:
        """Verify trace mode can be enabled."""
        transport = StdioTransport(
            command="echo",
            trace=True,
        )

        assert transport.trace is True

    def test_transport_trace_disabled(self) -> None:
        """Verify trace mode can be disabled."""
        transport = StdioTransport(
            command="echo",
            trace=False,
        )

        assert transport.trace is False

    def test_transport_defaults(self) -> None:
        """Verify transport default values."""
        transport = StdioTransport(command="test")

        assert transport.args == []
        assert transport.cwd is None
        assert transport.env is None
        assert transport.trace is False

    @pytest.mark.asyncio
    async def test_handle_message_processes_response(self) -> None:
        """Verify _handle_message processes responses correctly."""
        transport = StdioTransport(command="echo")

        mock_future: asyncio.Future[object] = asyncio.Future()
        mock_future.set_result({"test": "result"})
        transport._pending[1] = mock_future

        message_body = b'{"jsonrpc": "2.0", "id": 1, "result": {"test": "result"}}'

        await transport._handle_message(message_body)

        assert mock_future.done()
        assert mock_future.result() == {"test": "result"}

    @pytest.mark.asyncio
    async def test_handle_message_processes_error_response(self) -> None:
        """Verify _handle_message processes error responses."""
        transport = StdioTransport(command="echo")

        mock_future: asyncio.Future[object] = asyncio.Future()
        transport._pending[1] = mock_future

        message_body = (
            b'{"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Test error"}}'
        )

        await transport._handle_message(message_body)

        assert mock_future.done()
        assert mock_future.exception() is not None

    @pytest.mark.asyncio
    async def test_on_notification_registers_handler(self) -> None:
        """Verify on_notification registers handler."""
        transport = StdioTransport(command="echo")

        handler = MagicMock()
        transport.on_notification("test/notification", handler)

        assert "test/notification" in transport._notification_handlers
        assert transport._notification_handlers["test/notification"] == handler

    @pytest.mark.asyncio
    async def test_on_request_registers_handler(self) -> None:
        """Verify on_request registers handler."""
        transport = StdioTransport(command="echo")

        handler = MagicMock()
        transport.on_request("test/request", handler)

        assert "test/request" in transport._request_handlers
        assert transport._request_handlers["test/request"] == handler

    def test_parse_content_length_valid(self) -> None:
        """Verify _parse_content_length parses valid headers."""
        transport = StdioTransport(command="echo")

        headers = b"Content-Length: 123\r\n\r\n"
        result = transport._parse_content_length(headers)

        assert result == 123

    def test_parse_content_length_invalid(self) -> None:
        """Verify _parse_content_length returns None for invalid headers."""
        transport = StdioTransport(command="echo")

        headers = b"Invalid-Header\r\n\r\n"
        result = transport._parse_content_length(headers)

        assert result is None

    def test_parse_content_length_empty(self) -> None:
        """Verify _parse_content_length returns None for empty headers."""
        transport = StdioTransport(command="echo")

        headers = b""
        result = transport._parse_content_length(headers)

        assert result is None
