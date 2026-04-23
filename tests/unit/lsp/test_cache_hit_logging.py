"""Unit tests for cache hit logging.

Tests for diagnostic cache hit/miss logging in the LSP client.
Per ADR-0009, cache HIT messages should be logged at INFO level (not DEBUG).
"""

import logging
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test Suite 4.1: Cache Hit Log Level (ADR-0009)
# =============================================================================


class TestCacheHitLogLevel:
    """Tests for cache HIT log level promotion to INFO per ADR-0009."""

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

    def test_server_cache_hit_logs_info_level(self) -> None:
        """Server-reported cache HIT (kind=unchanged) should log at INFO level.

        This test will FAIL before implementation - currently logs at DEBUG.
        Per ADR-0009: Promote cache HIT to INFO for visibility at default log level.
        """
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        client._diagnostic_cache.get_cached.return_value = []

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {"kind": "unchanged", "uri": "file:///test.py", "resultId": "abc123"}
            )

            # Should have logged at INFO level (not DEBUG)
            # This assertion will FAIL before the fix is applied
            mock_logger.info.assert_called()
            calls = [str(c) for c in mock_logger.info.call_args_list]
            assert any("unchanged" in c.lower() or "cache" in c.lower() for c in calls)

    def test_server_cache_hit_not_debug(self) -> None:
        """Server-reported cache HIT should NOT log at DEBUG level.

        Per ADR-0009: Cache HIT upgraded to INFO.
        """
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        client._diagnostic_cache.get_cached.return_value = []

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {"kind": "unchanged", "uri": "file:///test.py", "resultId": "abc123"}
            )

            # Should NOT use debug for cache hit anymore
            debug_calls = [str(c) for c in mock_logger.debug.call_args_list]
            cache_hit_debug_calls = [
                c for c in debug_calls
                if "unchanged" in c.lower() or "cache hit" in c.lower()
            ]
            assert len(cache_hit_debug_calls) == 0, (
                "Cache HIT should not log at DEBUG level - use INFO instead"
            )

    def test_mtime_cache_hit_logs_info_level(self) -> None:
        """mtime-based cache HIT should log at INFO level.

        Tests _log_cache_hit() method which is called when mtime validation passes.
        This test will FAIL before implementation - currently logs at DEBUG.
        """
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        # Mock FileState with typical cache data
        mock_file_state = MagicMock()
        mock_file_state.diagnostics = [{"message": "cached error"}]
        mock_file_state.last_result_id = "result-abc123"
        mock_file_state.document_version = 1
        mock_file_state.is_open = True

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._log_cache_hit(
                uri="file:///workspace/src/module.py",
                file_state=mock_file_state,
                current_mtime=12345.67,
            )

            # Should have logged at INFO level
            mock_logger.info.assert_called()
            calls = [str(c) for c in mock_logger.info.call_args_list]
            assert any("cache HIT" in c for c in calls)

    def test_mtime_cache_hit_not_debug(self) -> None:
        """mtime-based cache HIT should NOT log at DEBUG level.

        Per ADR-0009: Cache HIT upgraded to INFO.
        """
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        mock_file_state = MagicMock()
        mock_file_state.diagnostics = []
        mock_file_state.last_result_id = "test-id"
        mock_file_state.document_version = 1
        mock_file_state.is_open = False

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._log_cache_hit(
                uri="file:///test.py",
                file_state=mock_file_state,
                current_mtime=100.0,
            )

            # Should NOT use debug for cache hit
            debug_calls = [str(c) for c in mock_logger.debug.call_args_list]
            cache_hit_debug_calls = [c for c in debug_calls if "cache HIT" in c]
            assert len(cache_hit_debug_calls) == 0, (
                "Cache HIT should not log at DEBUG level - use INFO instead"
            )

    def test_cache_hit_includes_structured_data(self) -> None:
        """Cache HIT log includes structured data: resultId, mtime, version, open, diags."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()
        mock_file_state = MagicMock()
        mock_file_state.diagnostics = [{"message": "error1"}, {"message": "error2"}]
        mock_file_state.last_result_id = "abc123def456"
        mock_file_state.document_version = 5
        mock_file_state.is_open = True

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._log_cache_hit(
                uri="file:///workspace/src/module.py",
                file_state=mock_file_state,
                current_mtime=12345.67,
            )

            # Check that info was called (will fail before fix)
            mock_logger.info.assert_called()
            calls = [str(c) for c in mock_logger.info.call_args_list]
            all_calls = " ".join(calls)

            # Verify structured data is present
            assert "resultId" in all_calls or "result" in all_calls.lower()
            assert "mtime" in all_calls.lower() or "12345" in all_calls
            assert "diags=2" in all_calls or "diags" in all_calls.lower()


# =============================================================================
# Test Suite 4.2: Cache Miss Logging (remains at DEBUG)
# =============================================================================


class TestCacheMissLogging:
    """Tests for cache miss logging - should remain at DEBUG level."""

    def test_cache_miss_logs_debug(self) -> None:
        """Fresh diagnostics triggers debug log (not changed by ADR-0009)."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = MagicMock()

        with patch("llm_lsp_cli.lsp.client.logger") as mock_logger:
            client._normalize_document_diagnostics(
                {"kind": "full", "items": [{"message": "error1"}, {"message": "error2"}]}
            )

            # Fresh diagnostics should still log at DEBUG
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
# Test Suite 4.3: _normalize_document_diagnostics Behavior
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
            {
                "kind": "full",
                "items": [{"message": "error1"}, {"message": "error2"}],
                "resultId": "xyz",
            }
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
# Test Suite 4.4: Integration Tests
# =============================================================================


class TestDiagnosticCacheLoggingIntegration:
    """Integration tests for cache hit/miss logging."""

    @pytest.mark.asyncio
    async def test_cache_hit_visible_at_default_log_level(self) -> None:
        """Cache HIT should be visible at default (INFO) log level.

        Per ADR-0009: Cache behavior should be observable at default log levels.
        """
        import inspect

        from llm_lsp_cli.lsp import client

        # Verify _log_cache_hit and _log_cache_hit_server use logger.info
        source = inspect.getsource(client.LSPClient._log_cache_hit)
        assert "logger.info" in source, "_log_cache_hit should use logger.info"

        source = inspect.getsource(client.LSPClient._log_cache_hit_server)
        assert "logger.info" in source, "_log_cache_hit_server should use logger.info"

    @pytest.mark.asyncio
    async def test_cache_miss_still_debug(self) -> None:
        """Cache miss should remain at DEBUG level (not changed by ADR-0009)."""
        import inspect

        from llm_lsp_cli.lsp import client

        source = inspect.getsource(client.LSPClient._normalize_document_diagnostics)
        # Fresh diagnostic logging should remain at debug
        assert "debug" in source or "fresh" in source.lower()
