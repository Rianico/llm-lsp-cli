"""Unit tests for daemon mtime pass-through to request_diagnostics.

These tests verify that the daemon properly passes mtime to client.request_diagnostics()
to enable cache optimization (avoiding redundant server requests).

Bug: daemon._send_lsp_request() at line 512 doesn't pass mtime to request_diagnostics().
Fix: Get mtime from file stats and pass it to request_diagnostics(file_path=..., uri=..., mtime=...).
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from llm_lsp_cli.daemon import RequestHandler


class TestDaemonMtimePassthrough:
    """Tests for daemon passing mtime to request_diagnostics."""

    @pytest.mark.asyncio
    async def test_daemon_passes_mtime_to_request_diagnostics(self, tmp_path: Path) -> None:
        """Daemon MUST pass mtime to request_diagnostics for cache optimization.

        This test verifies that when the daemon handles a diagnostic request,
        it obtains the file's mtime and passes it to the client's request_diagnostics method.
        """
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")
        test_uri = test_file.as_uri()
        expected_mtime = os.stat(test_file).st_mtime

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        # Mock the registry and client
        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request_diagnostics = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            # Call the handler with a diagnostic request
            await handler._handle_lsp_method(
                "textDocument/diagnostic",
                {"filePath": str(test_file), "workspacePath": str(tmp_path)},
            )

        # CRITICAL ASSERTION: request_diagnostics MUST have been called with mtime
        mock_client.request_diagnostics.assert_called_once()
        call_kwargs = mock_client.request_diagnostics.call_args.kwargs
        assert "mtime" in call_kwargs, "mtime parameter MUST be passed to request_diagnostics"
        assert call_kwargs["mtime"] is not None, "mtime MUST not be None for existing files"
        # Verify mtime is approximately correct (within floating point tolerance)
        assert abs(call_kwargs["mtime"] - expected_mtime) < 0.001, "mtime value should match file's mtime"

    @pytest.mark.asyncio
    async def test_daemon_uses_os_stat_for_mtime(self, tmp_path: Path) -> None:
        """Daemon MUST use os.stat() to get file mtime.

        Verifies that the daemon uses os.stat(file_path).st_mtime (or st_mtime_ns / 1e9)
        to obtain the modification time.
        """
        test_file = tmp_path / "test.py"
        test_file.write_text("y = 2\n")
        test_uri = test_file.as_uri()
        expected_mtime = 12345.678

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        # Mock os.stat to return a controlled mtime
        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request_diagnostics = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            # Mock os.stat to return controlled mtime
            mock_stat = AsyncMock()
            mock_stat.st_mtime = expected_mtime
            mock_stat.st_mtime_ns = int(expected_mtime * 1e9)

            with patch("os.stat", return_value=mock_stat):
                await handler._handle_lsp_method(
                    "textDocument/diagnostic",
                    {"filePath": str(test_file), "workspacePath": str(tmp_path)},
                )

        # Verify mtime was passed correctly
        call_kwargs = mock_client.request_diagnostics.call_args.kwargs
        assert "mtime" in call_kwargs
        assert call_kwargs["mtime"] == expected_mtime

    @pytest.mark.asyncio
    async def test_daemon_passes_correct_file_path_to_request_diagnostics(
        self, tmp_path: Path
    ) -> None:
        """Daemon MUST pass the correct file_path to request_diagnostics."""
        test_file = tmp_path / "example.py"
        test_file.write_text("z = 3\n")
        test_uri = test_file.as_uri()

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request_diagnostics = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            await handler._handle_lsp_method(
                "textDocument/diagnostic",
                {"filePath": str(test_file), "workspacePath": str(tmp_path)},
            )

        call_kwargs = mock_client.request_diagnostics.call_args.kwargs
        assert call_kwargs.get("file_path") == str(test_file)

    @pytest.mark.asyncio
    async def test_daemon_passes_correct_uri_to_request_diagnostics(self, tmp_path: Path) -> None:
        """Daemon MUST pass the correct URI to request_diagnostics."""
        test_file = tmp_path / "uri_test.py"
        test_file.write_text("a = 1\n")
        expected_uri = test_file.as_uri()

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request_diagnostics = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=expected_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            await handler._handle_lsp_method(
                "textDocument/diagnostic",
                {"filePath": str(test_file), "workspacePath": str(tmp_path)},
            )

        call_kwargs = mock_client.request_diagnostics.call_args.kwargs
        assert call_kwargs.get("uri") == expected_uri


class TestDaemonMtimeStatFailure:
    """Tests for daemon behavior when os.stat fails."""

    @pytest.mark.asyncio
    async def test_daemon_handles_stat_failure_gracefully(self, tmp_path: Path) -> None:
        """Daemon MUST handle stat failures gracefully and still make the request.

        When os.stat() raises an error (e.g., file deleted, permission error),
        the daemon should fall back to mtime=None and still process the request.
        """
        test_file = tmp_path / "missing.py"
        test_file.write_text("x = 1\n")  # Create file for DocumentSyncContext
        test_uri = test_file.as_uri()

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request_diagnostics = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            # Mock os.stat to raise OSError
            with patch("os.stat", side_effect=OSError("File not found")):
                # The daemon should still handle this without crashing
                await handler._handle_lsp_method(
                    "textDocument/diagnostic",
                    {"filePath": str(test_file), "workspacePath": str(tmp_path)},
                )

        # Verify request_diagnostics was still called
        mock_client.request_diagnostics.assert_called_once()
        # The daemon should not crash - that's the key assertion

    @pytest.mark.asyncio
    async def test_daemon_passes_none_mtime_when_stat_fails(self, tmp_path: Path) -> None:
        """When os.stat fails, daemon MUST pass mtime=None to force server request."""
        test_file = tmp_path / "stat_error.py"
        test_file.write_text("x = 1\n")  # Create file for DocumentSyncContext
        test_uri = test_file.as_uri()

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request_diagnostics = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            with patch("os.stat", side_effect=PermissionError("Access denied")):
                await handler._handle_lsp_method(
                    "textDocument/diagnostic",
                    {"filePath": str(test_file), "workspacePath": str(tmp_path)},
                )

        call_kwargs = mock_client.request_diagnostics.call_args.kwargs
        # mtime MUST be passed (even if None) - key assertion
        assert "mtime" in call_kwargs, "mtime parameter MUST be passed (as None if stat fails)"
        # mtime should be None when stat fails
        assert call_kwargs["mtime"] is None


class TestDaemonMtimeCacheIntegration:
    """Tests for daemon + client cache interaction via mtime."""

    @pytest.mark.asyncio
    async def test_second_diagnostic_request_uses_cache_via_mtime(
        self, tmp_path: Path
    ) -> None:
        """Second request with same mtime MUST use cached diagnostics (no server hit).

        This tests the end-to-end cache optimization:
        1. First request: daemon passes mtime -> client sends to server -> cache populated
        2. Second request: daemon passes same mtime -> client uses cache -> NO server hit
        """
        from llm_lsp_cli.lsp.client import LSPClient

        test_file = tmp_path / "cached.py"
        test_file.write_text("cached_var = 1\n")
        test_uri = test_file.as_uri()
        mtime = os.stat(test_file).st_mtime

        # Create a real client with mocked transport
        client = LSPClient(
            workspace_path=str(tmp_path),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        # Setup cache with existing diagnostics
        cached_diagnostics: list[dict[str, Any]] = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Cached issue",
                "source": "test",
            }
        ]
        await client._diagnostic_cache.set_mtime(test_uri, mtime)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, cached_diagnostics, result_id="cached-result-id"
        )

        # Mock transport to track server calls
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock()
        client._transport = mock_transport

        # Mock _ensure_open
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Simulate daemon's call to request_diagnostics with mtime
            result = await client.request_diagnostics(
                file_path=str(test_file), uri=test_uri, mtime=mtime
            )

        # Server should NOT have been called (cache hit)
        mock_transport.send_request.assert_not_called()
        # Cached diagnostics should be returned
        assert result == cached_diagnostics
