"""Tests for diagnostic cache logic with mtime-based staleness.

These tests verify that when a file is unchanged (same mtime) and diagnostics are cached,
the client returns cached results WITHOUT sending a request to the server.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient


class TestDiagnosticCacheSkipServerRequest:
    """Tests for skipping server requests when cache is valid."""

    @pytest.mark.asyncio
    async def test_no_server_request_when_cache_valid_and_mtime_unchanged(
        self, temp_dir: Path
    ) -> None:
        """When mtime unchanged and diagnostics cached, no server request should be made.

        This test verifies mtime-based cache hit behavior.
        Expected behavior:
        1. First request: send to server, cache result with resultId and mtime
        2. Second request (same mtime): return cached diagnostics directly, NO server request
        """
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Cached error",
                "source": "pyright",
            }
        ]

        # Setup cache with mtime and resultId
        mtime = 100.0
        await client._diagnostic_cache.set_mtime(test_uri, mtime)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, test_diagnostics, result_id="result-123"
        )

        # Mock transport to track if send_request is called
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock()
        client._transport = mock_transport

        # Mock _ensure_open to return a known URI
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with SAME mtime - should NOT call the server
            result = await client.request_diagnostics("/tmp/test/file.py", uri=test_uri, mtime=mtime)

        # Verify: NO server request should have been made
        mock_transport.send_request.assert_not_called()

        # Verify: Cached diagnostics should be returned
        assert result == test_diagnostics

    @pytest.mark.asyncio
    async def test_server_request_when_mtime_changed(self, temp_dir: Path) -> None:
        """When mtime indicates file changed, server request SHOULD be made.

        This test ensures we don't over-optimize and skip necessary requests.
        """
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        old_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Old error",
                "source": "pyright",
            }
        ]
        new_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 1, "character": 0},
                    "end": {"line": 1, "character": 10},
                },
                "severity": 2,
                "message": "New warning",
                "source": "pyright",
            }
        ]

        # Setup cache with old mtime
        await client._diagnostic_cache.set_mtime(test_uri, 50.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, old_diagnostics, result_id="result-old"
        )

        # Mock transport with new diagnostics response
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "result-new",
                "items": new_diagnostics,
            }
        )
        client._transport = mock_transport

        # Mock _ensure_open to return a known URI
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with NEWER mtime (file changed)
            result = await client.request_diagnostics("/tmp/test/file.py", uri=test_uri, mtime=100.0)

        # Verify: Server request SHOULD have been made
        mock_transport.send_request.assert_called_once()

        # Verify: New diagnostics should be returned
        assert result == new_diagnostics

    @pytest.mark.asyncio
    async def test_server_request_when_no_result_id(self, temp_dir: Path) -> None:
        """When diagnostics cached but no resultId, server request SHOULD be made.

        Without a resultId, we cannot use the LSP 3.17 diagnostic pull optimization.
        """
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        cached_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Cached error",
                "source": "pyright",
            }
        ]

        # Setup cache with mtime but NO resultId
        await client._diagnostic_cache.set_mtime(test_uri, 100.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, cached_diagnostics, result_id=None  # No resultId
        )

        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "result-123",
                "items": cached_diagnostics,
            }
        )
        client._transport = mock_transport

        # Mock _ensure_open to return a known URI
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            result = await client.request_diagnostics("/tmp/test/file.py", uri=test_uri, mtime=100.0)

        # Verify: Server request SHOULD have been made (no resultId to use for optimization)
        mock_transport.send_request.assert_called_once()

        # Verify: Diagnostics should be returned
        assert result == cached_diagnostics

    @pytest.mark.asyncio
    async def test_first_diagnostic_request_sends_to_server(self, temp_dir: Path) -> None:
        """First diagnostic request (no cache) SHOULD send request to server.

        This test ensures the optimization doesn't break the initial request case.
        """
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "New error",
                "source": "pyright",
            }
        ]

        # No cache setup - first request

        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "result-123",
                "items": test_diagnostics,
            }
        )
        client._transport = mock_transport

        # Mock _ensure_open to return a known URI
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            result = await client.request_diagnostics("/tmp/test/file.py", uri=test_uri, mtime=100.0)

        # Verify: Server request SHOULD have been made
        mock_transport.send_request.assert_called_once()

        # Verify: Diagnostics should be returned
        assert result == test_diagnostics

    @pytest.mark.asyncio
    async def test_cache_hit_logging_without_server_request(self, temp_dir: Path) -> None:
        """When returning cached diagnostics, appropriate log message should be emitted.

        This test verifies that the cache hit path logs appropriately.
        """
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Cached error",
                "source": "pyright",
            }
        ]

        # Setup cache with mtime and resultId
        mtime = 100.0
        await client._diagnostic_cache.set_mtime(test_uri, mtime)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, test_diagnostics, result_id="result-123"
        )

        # Mock transport to ensure no request is made
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock()
        client._transport = mock_transport

        # Mock _ensure_open
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with SAME mtime
            result = await client.request_diagnostics("/tmp/test/file.py", uri=test_uri, mtime=mtime)

        # Verify no server request
        mock_transport.send_request.assert_not_called()

        # Verify cached diagnostics returned
        assert result == test_diagnostics
