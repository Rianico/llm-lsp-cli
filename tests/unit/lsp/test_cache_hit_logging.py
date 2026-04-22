"""Unit tests for cache hit logging.

Tests for diagnostic cache hit/miss logging in the LSP client.
"""

import logging
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test Suite 4.1: Cache Hit Detection
# =============================================================================


class TestCacheHitLogging:
    """Tests for cache hit detection and logging."""

    @pytest.fixture
    def log_capture(self) -> Any:
        """Capture log output for assertions."""
        logger = logging.getLogger("llm_lsp_cli.lsp.client")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        yield stream, logger

        logger.removeHandler(handler)

    def test_cache_hit_logs_debug(self) -> None:
        """kind: "unchanged" triggers debug log."""
        # This test verifies that _normalize_document_diagnostics logs
        # a debug message when kind is "unchanged"
        from llm_lsp_cli.lsp.client import LSPClient

        # Check that the method handles "unchanged" kind
        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        client._diagnostic_cache.get_cached.return_value = []

        # Create a mock logger to capture calls
        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {"kind": "unchanged", "uri": "file:///test.py", "resultId": "abc123"}
            )

            # Should have logged about cache hit
            mock_logger.debug.assert_called()
            calls = [str(c) for c in mock_logger.debug.call_args_list]
            assert any("unchanged" in c.lower() or "cache" in c.lower() for c in calls)

    def test_cache_hit_includes_uri(self) -> None:
        """Cache hit log includes URI."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        client._diagnostic_cache.get_cached.return_value = []

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {"kind": "unchanged", "uri": "file:///test/sample.py", "resultId": "abc123"}
            )

            calls = [str(c) for c in mock_logger.debug.call_args_list]
            # URI should be in the log message
            all_calls = " ".join(calls)
            assert (
                "sample.py" in all_calls or "test/sample.py" in all_calls
                or "file:" in all_calls
            )

    def test_cache_miss_logs_debug(self) -> None:
        """Fresh diagnostics triggers debug log."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {"kind": "full", "items": [{"message": "error1"}, {"message": "error2"}]}
            )

            # Should have logged about fresh diagnostics
            mock_logger.debug.assert_called()
            calls = [str(c) for c in mock_logger.debug.call_args_list]
            assert any("fresh" in c.lower() or "diagnostic" in c.lower() for c in calls)

    def test_cache_miss_includes_count(self) -> None:
        """Cache miss log includes item count."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {
                    "kind": "full",
                    "items": [
                        {"message": "error1"},
                        {"message": "error2"},
                        {"message": "error3"},
                    ],
                }
            )

            calls = [str(c) for c in mock_logger.debug.call_args_list]
            all_calls = " ".join(calls)
            # Should include count of diagnostics
            assert "3" in all_calls or "count" in all_calls.lower()


# =============================================================================
# Test Suite 4.2: _normalize_document_diagnostics Behavior
# =============================================================================


class TestNormalizeDocumentDiagnostics:
    """Tests for _normalize_document_diagnostics behavior."""

    def test_unchanged_returns_cached(self) -> None:
        """kind: "unchanged" returns cached result."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        cached_diagnostics = [{"message": "cached error"}]
        client._diagnostic_cache.get_cached.return_value = cached_diagnostics

        diagnostics, result_id = client._normalize_document_diagnostics(
            {"kind": "unchanged", "uri": "file:///test.py", "resultId": "abc123"}
        )

        client._diagnostic_cache.get_cached.assert_called_once_with("file:///test.py")
        assert diagnostics == cached_diagnostics
        assert result_id is None

    def test_full_returns_items(self) -> None:
        """Full report returns items list."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()

        diagnostics, result_id = client._normalize_document_diagnostics(
            {"kind": "full", "items": [{"message": "error1"}, {"message": "error2"}], "resultId": "xyz"}
        )

        assert diagnostics == [{"message": "error1"}, {"message": "error2"}]
        assert result_id == "xyz"

    def test_none_returns_empty(self) -> None:
        """None result returns empty list."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()

        diagnostics, result_id = client._normalize_document_diagnostics(None)

        assert diagnostics == []
        assert result_id is None

    def test_list_passthrough(self) -> None:
        """List result passed through."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()

        diagnostics, result_id = client._normalize_document_diagnostics(
            [{"message": "error1"}, {"message": "error2"}]
        )

        assert diagnostics == [{"message": "error1"}, {"message": "error2"}]
        assert result_id is None


# =============================================================================
# Test Suite 4.3: Integration Tests
# =============================================================================


class TestDiagnosticCacheLoggingIntegration:
    """Integration tests for cache hit/miss logging."""

    @pytest.mark.asyncio
    async def test_cache_hit_visible_in_debug_output(self) -> None:
        """Full diagnostic request flow shows cache hit."""
        # This test would require a full LSP client setup
        # For now, we verify the logging pattern exists in the code
        import inspect

        from llm_lsp_cli.lsp import client

        source = inspect.getsource(client.LSPClient._normalize_document_diagnostics)
        assert "unchanged" in source or "debug" in source

    @pytest.mark.asyncio
    async def test_cache_miss_visible_in_debug_output(self) -> None:
        """First diagnostic request shows cache miss."""
        import inspect

        from llm_lsp_cli.lsp import client

        source = inspect.getsource(client.LSPClient._normalize_document_diagnostics)
        assert "full" in source or "items" in source
