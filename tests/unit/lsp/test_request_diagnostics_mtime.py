"""Tests for LSPClient.request_diagnostics() with mtime parameter.

These tests verify the refactored request_diagnostics method:
- Accepts optional mtime parameter
- Uses mtime for staleness check
- Calls set_mtime after refresh
- Backward compatible when mtime not provided
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient


class TestRequestDiagnosticsMtime:
    """Tests for request_diagnostics with mtime parameter."""

    @pytest.mark.asyncio
    async def test_accepts_mtime_parameter(self, temp_dir: Path) -> None:
        """request_diagnostics should accept mtime parameter without error."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics: list[dict[str, Any]] = [{"message": "test"}]

        # Setup cache with matching mtime (not stale)
        await client._diagnostic_cache.set_mtime(test_uri, 100.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, test_diagnostics, result_id="result-123"
        )

        # Mock _ensure_open
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Should not raise
            result = await client.request_diagnostics(
                file_path="/tmp/test/file.py", uri=test_uri, mtime=100.0
            )

        assert result == test_diagnostics

    @pytest.mark.asyncio
    async def test_uses_mtime_for_staleness_check_stale(self, temp_dir: Path) -> None:
        """When mtime indicates stale, should make server request."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        old_diagnostics = [{"message": "old"}]
        new_diagnostics = [{"message": "new"}]

        # Setup cache with old mtime
        await client._diagnostic_cache.set_mtime(test_uri, 50.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, old_diagnostics, result_id="result-old"
        )

        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "result-new",
                "items": new_diagnostics,
            }
        )
        client._transport = mock_transport

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with newer mtime (stale)
            result = await client.request_diagnostics(
                file_path="/tmp/test/file.py", uri=test_uri, mtime=100.0
            )

        # Server request should have been made
        mock_transport.send_request.assert_called_once()
        assert result == new_diagnostics

    @pytest.mark.asyncio
    async def test_skips_server_when_mtime_unchanged(self, temp_dir: Path) -> None:
        """When mtime matches stored, should skip server request."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics = [{"message": "cached"}]

        # Setup cache with matching mtime
        await client._diagnostic_cache.set_mtime(test_uri, 100.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, test_diagnostics, result_id="result-123"
        )

        # Mock transport (should NOT be called)
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock()
        client._transport = mock_transport

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with same mtime (not stale)
            result = await client.request_diagnostics(
                file_path="/tmp/test/file.py", uri=test_uri, mtime=100.0
            )

        # No server request should have been made
        mock_transport.send_request.assert_not_called()
        assert result == test_diagnostics

    @pytest.mark.asyncio
    async def test_calls_set_mtime_after_refresh(self, temp_dir: Path) -> None:
        """After refreshing diagnostics, set_mtime should be called."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        new_diagnostics = [{"message": "new"}]

        # Setup cache with old mtime
        await client._diagnostic_cache.set_mtime(test_uri, 50.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, [], result_id="result-old"
        )

        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "result-new",
                "items": new_diagnostics,
            }
        )
        client._transport = mock_transport

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with newer mtime
            await client.request_diagnostics(
                file_path="/tmp/test/file.py", uri=test_uri, mtime=100.0
            )

        # Verify mtime was updated
        state = await client._diagnostic_cache.get_file_state(test_uri)
        assert state.mtime == 100.0

    @pytest.mark.asyncio
    async def test_works_without_mtime_backward_compat(self, temp_dir: Path) -> None:
        """request_diagnostics should work without mtime (backward compatible)."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics = [{"message": "test"}]

        # Setup cache without mtime (legacy scenario)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, test_diagnostics, result_id="result-123"
        )

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

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # No mtime provided - should still work
            result = await client.request_diagnostics(
                file_path="/tmp/test/file.py", uri=test_uri
            )

        assert result == test_diagnostics

    @pytest.mark.asyncio
    async def test_falls_back_to_cache_on_error(self, temp_dir: Path) -> None:
        """When server request fails, should return cached diagnostics."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        cached_diagnostics = [{"message": "cached"}]

        # Setup cache
        await client._diagnostic_cache.set_mtime(test_uri, 100.0)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, cached_diagnostics, result_id="result-123"
        )

        # Mock transport to raise error
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(side_effect=Exception("Server error"))
        client._transport = mock_transport

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Request with newer mtime (would be stale, but server fails)
            result = await client.request_diagnostics(
                file_path="/tmp/test/file.py", uri=test_uri, mtime=200.0
            )

        # Should return cached diagnostics
        assert result == cached_diagnostics
