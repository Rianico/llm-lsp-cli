"""Tests for uri_to_absolute_path integration (Issue 2b)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache
from llm_lsp_cli.lsp.client import LSPClient


class TestUriUtilityIntegration:
    """Verify both consumers delegate to shared utility."""

    def test_diagnostic_cache_uses_uri_utility(self, tmp_path: Path) -> None:
        """DiagnosticCache._uri_to_absolute_path should delegate to utils.uri."""
        cache = DiagnosticCache(tmp_path)
        test_uri = (tmp_path / "test.py").as_uri()

        # Mock at the location where it's imported (in cache module)
        with patch("llm_lsp_cli.lsp.cache.uri_to_absolute_path") as mock_util:
            mock_util.return_value = str(tmp_path / "test.py")

            cache._uri_to_absolute_path(test_uri)

            mock_util.assert_called_once()

    def test_lsp_client_uses_uri_utility(self, tmp_path: Path) -> None:
        """LSPClient._uri_to_absolute_path should delegate to utils.uri."""
        # LSPClient requires many params
        client = LSPClient(
            workspace_path=str(tmp_path),
            server_command="pyright",
            language_id="python",
        )

        test_uri = (tmp_path / "test.py").as_uri()

        # Mock at the source module (utils.uri) since import happens inside method
        with patch("llm_lsp_cli.utils.uri.uri_to_absolute_path") as mock_util:
            mock_util.return_value = str(tmp_path / "test.py")

            client._uri_to_absolute_path(test_uri)

            mock_util.assert_called_once()

    def test_both_consumers_produce_same_result(self, tmp_path: Path) -> None:
        """Both consumers should produce identical results for same input."""
        cache = DiagnosticCache(tmp_path)
        client = LSPClient(
            workspace_path=str(tmp_path),
            server_command="pyright",
            language_id="python",
        )

        test_uri = (tmp_path / "test.py").as_uri()

        # Both should produce the same result
        cache_result = cache._uri_to_absolute_path(test_uri)
        client_result = client._uri_to_absolute_path(test_uri)

        assert cache_result == client_result
