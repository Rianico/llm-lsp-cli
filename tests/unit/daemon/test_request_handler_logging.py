"""Unit tests for RequestHandler logging functionality."""

import logging
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture

from llm_lsp_cli.daemon import RequestHandler


class TestRequestHandlerLogging:
    """Tests for RequestHandler._handle_lsp_method() logging."""

    @pytest.mark.asyncio
    async def test_logs_method_entry(self, caplog: LogCaptureFixture):
        """DEBUG log emitted when handling LSP method."""
        with caplog.at_level(logging.DEBUG):
            handler = RequestHandler(
                workspace_path="/test/workspace",
                language="python",
            )

            # Mock registry method
            with patch.object(handler._registry, "request_document_symbols") as mock_method:
                mock_method.return_value = []

                await handler._handle_lsp_method(
                    "textDocument/documentSymbol",
                    {"filePath": "/test.py"},
                )

            # Verify method entry was logged
            assert "Handling LSP method" in caplog.text
            assert "textDocument/documentSymbol" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_method_parameters(self, caplog: LogCaptureFixture):
        """DEBUG log includes method parameters."""
        with caplog.at_level(logging.DEBUG):
            handler = RequestHandler(
                workspace_path="/test/workspace",
                language="python",
            )

            # Mock registry method
            with patch.object(handler._registry, "request_document_symbols") as mock_method:
                mock_method.return_value = []

                params = {"filePath": "/test/file.py", "workspacePath": "/test/workspace"}
                await handler._handle_lsp_method(
                    "textDocument/documentSymbol",
                    params,
                )

            # Verify parameters were logged
            assert "params" in caplog.text.lower() or "/test/file.py" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_exception_with_traceback(self, caplog: LogCaptureFixture):
        """EXCEPTION log with full traceback when registry method raises."""
        with caplog.at_level(logging.DEBUG):
            handler = RequestHandler(
                workspace_path="/test/workspace",
                language="python",
            )

            # Mock registry method to raise exception
            with patch.object(handler._registry, "request_document_symbols") as mock_method:
                mock_method.side_effect = ValueError("Test error")

                with pytest.raises(ValueError):
                    await handler._handle_lsp_method(
                        "textDocument/documentSymbol",
                        {"filePath": "/test.py"},
                    )

            # Verify exception was logged with traceback
            # logger.exception() should be called, which includes traceback
            assert "Test error" in caplog.text
            # Verify exception logging occurred (traceback indicator)
            assert "Traceback" in caplog.text or "error" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_logs_successful_return(self, caplog: LogCaptureFixture):
        """DEBUG log when registry method returns successfully."""
        with caplog.at_level(logging.DEBUG):
            handler = RequestHandler(
                workspace_path="/test/workspace",
                language="python",
            )

            # Mock registry method
            with patch.object(handler._registry, "request_document_symbols") as mock_method:
                mock_method.return_value = [{"name": "MyClass", "kind": "Class"}]

                await handler._handle_lsp_method(
                    "textDocument/documentSymbol",
                    {"filePath": "/test.py"},
                )

            # Verify successful execution was logged
            assert "Registry method returned" in caplog.text or "symbols" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_uses_logger_exception_not_error(self, caplog: LogCaptureFixture):
        """Verifies logger.exception() is used (not logger.error()) for exceptions."""
        # This test verifies that exception logging uses logger.exception()
        # which includes the traceback, not just logger.error()
        with caplog.at_level(logging.DEBUG):
            handler = RequestHandler(
                workspace_path="/test/workspace",
                language="python",
            )

            # Mock registry method to raise with traceback
            with patch.object(handler._registry, "request_document_symbols") as mock_method:
                mock_method.side_effect = RuntimeError("Critical error")

                with pytest.raises(RuntimeError):
                    await handler._handle_lsp_method(
                        "textDocument/documentSymbol",
                        {"filePath": "/test.py"},
                    )

            # Verify traceback is present (indicates logger.exception() was used)
            # logger.error() doesn't include traceback unless explicitly formatted
            log_records = [r for r in caplog.records if "Critical error" in r.getMessage()]
            assert len(log_records) > 0
            # The presence of traceback in caplog.text indicates exception() was used
            assert "Traceback" in caplog.text
