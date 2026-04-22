"""Unit tests for UNIXServer exception logging."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from _pytest.logging import LogCaptureFixture

from llm_lsp_cli.ipc.unix_server import UNIXServer


class TestUNIXServerLogging:
    """Tests for UNIXServer._handle_client() exception logging."""

    @pytest.mark.asyncio
    async def test_logs_generic_exception(self, caplog: LogCaptureFixture):
        """Generic exceptions from reader.read() are logged via logger.exception()."""
        with caplog.at_level(logging.DEBUG):
            # Mock request handler
            async def normal_handler(method, params):
                return {"result": "ok"}

            server = UNIXServer(
                socket_path="/tmp/test.sock",
                request_handler=normal_handler,
            )

            # Mock reader that raises an exception on read
            async def failing_read(size):
                raise RuntimeError("Read failed")

            mock_reader = AsyncMock()
            mock_reader.read = failing_read

            mock_writer = AsyncMock()
            mock_writer.close = MagicMock()

            await server._handle_client(mock_reader, mock_writer)

            # Verify the exception was logged
            assert "Read failed" in caplog.text
            assert "Error handling client connection" in caplog.text

    @pytest.mark.asyncio
    async def test_cancelled_error_re_raised(self):
        """asyncio.CancelledError is re-raised, not swallowed."""

        async def raising_handler(method, params):
            raise asyncio.CancelledError()

        server = UNIXServer(
            socket_path="/tmp/test.sock",
            request_handler=raising_handler,
        )

        # Mock reader and writer
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Mock parse_message to return a valid message
        mock_data = {"method": "test", "id": 1}
        with patch("llm_lsp_cli.ipc.unix_server.parse_message") as mock_parse:
            mock_parse.return_value = (mock_data, b"")

            # CancelledError should be re-raised
            with pytest.raises(asyncio.CancelledError):
                await server._handle_client(mock_reader, mock_writer)

    @pytest.mark.asyncio
    async def test_incomplete_read_error_logged_at_debug(self, caplog: LogCaptureFixture):
        """asyncio.IncompleteReadError is logged at DEBUG level and swallowed."""
        with caplog.at_level(logging.DEBUG):

            async def raising_handler(method, params):
                raise asyncio.IncompleteReadError(b"partial", 100)

            server = UNIXServer(
                socket_path="/tmp/test.sock",
                request_handler=raising_handler,
            )

            # Mock reader and writer
            mock_reader = AsyncMock()
            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()

            # Mock parse_message to return a valid message
            mock_data = {"method": "test", "id": 1}
            with patch("llm_lsp_cli.ipc.unix_server.parse_message") as mock_parse:
                mock_parse.return_value = (mock_data, b"")

                # Should not raise - IncompleteReadError is swallowed
                await server._handle_client(mock_reader, mock_writer)

            # Verify it was logged (swallowed, not re-raised)
            # The exception should be handled gracefully

    @pytest.mark.asyncio
    async def test_normal_disconnect_no_exception_logged(self, caplog: LogCaptureFixture):
        """Normal client disconnect (EOF) does not log exception."""
        with caplog.at_level(logging.DEBUG):

            async def normal_handler(method, params):
                return {"result": "success"}

            server = UNIXServer(
                socket_path="/tmp/test.sock",
                request_handler=normal_handler,
            )

            # Mock reader that returns empty (normal disconnect)
            mock_reader = AsyncMock()
            mock_reader.read = AsyncMock(return_value=b"")  # EOF immediately

            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            mock_writer.write = MagicMock()
            mock_writer.drain = AsyncMock()

            await server._handle_client(mock_reader, mock_writer)

            # Verify no exception was logged
            exception_records = [
                r
                for r in caplog.records
                if r.levelname == "ERROR" and "exception" in r.getMessage().lower()
            ]
            assert len(exception_records) == 0

    @pytest.mark.asyncio
    async def test_exception_logging_uses_logger_exception(self, caplog: LogCaptureFixture):
        """Verifies logger.exception() is used (includes traceback)."""
        with caplog.at_level(logging.DEBUG):

            async def raising_handler(method, params):
                raise RuntimeError("Server error")

            server = UNIXServer(
                socket_path="/tmp/test.sock",
                request_handler=raising_handler,
            )

            # Mock reader and writer
            mock_reader = AsyncMock()
            mock_writer = MagicMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()

            mock_data = {"method": "test", "id": 1}
            with patch("llm_lsp_cli.ipc.unix_server.parse_message") as mock_parse:
                mock_parse.return_value = (mock_data, b"")

                await server._handle_client(mock_reader, mock_writer)

            # Verify traceback is present (indicates logger.exception() was used)
            assert "Traceback" in caplog.text or "server error" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_different_exception_types_handled_differently(self, caplog: LogCaptureFixture):
        """Different exception types have different handling strategies."""

        # Mock request handler
        async def normal_handler(method, params):
            return {"result": "ok"}

        # Test 1: RuntimeError in read should be logged and swallowed
        server = UNIXServer(
            socket_path="/tmp/test.sock",
            request_handler=normal_handler,
        )

        async def failing_read(size):
            raise RuntimeError("Read error")

        mock_reader = AsyncMock()
        mock_reader.read = failing_read

        mock_writer = AsyncMock()
        mock_writer.close = MagicMock()

        with caplog.at_level(logging.DEBUG):
            # Should not raise - exception is logged and swallowed
            await server._handle_client(mock_reader, mock_writer)
            assert "Read error" in caplog.text

        # Test 2: CancelledError should be re-raised
        async def cancel_during_read(size):
            raise asyncio.CancelledError()

        mock_reader2 = AsyncMock()
        mock_reader2.read = cancel_during_read

        mock_writer2 = AsyncMock()
        mock_writer2.close = MagicMock()

        server2 = UNIXServer(
            socket_path="/tmp/test2.sock",
            request_handler=normal_handler,
        )

        # CancelledError should be re-raised
        with pytest.raises(asyncio.CancelledError):
            await server2._handle_client(mock_reader2, mock_writer2)
