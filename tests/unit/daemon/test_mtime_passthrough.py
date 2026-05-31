"""Unit tests for daemon mtime pass-through to client.request().

These tests verify that the daemon properly passes mtime in the LSP params
to enable cache optimization (avoiding redundant server requests).
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from llm_lsp_cli.daemon import RequestHandler
from llm_lsp_cli.lsp.constants import LSPConstants


class TestDaemonMtimePassthrough:
    """Tests for daemon passing mtime to client.request() for diagnostics."""

    @pytest.mark.asyncio
    async def test_daemon_passes_mtime_in_lsp_params(self, tmp_path: Path) -> None:
        """Daemon MUST pass mtime in LSP params for cache optimization."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")
        test_uri = test_file.as_uri()
        expected_mtime = os.stat(test_file).st_mtime

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            await handler._handle_lsp_method(
                LSPConstants.DIAGNOSTIC,
                {"filePath": str(test_file), "workspacePath": str(tmp_path)},
            )

        # Verify client.request was called with mtime in params
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        lsp_params = call_args[0][1]  # Second positional arg is the params dict
        assert "_mtime" in lsp_params, "mtime MUST be passed in LSP params"
        assert lsp_params["_mtime"] is not None, "mtime MUST not be None for existing files"
        assert abs(lsp_params["_mtime"] - expected_mtime) < 0.001

    @pytest.mark.asyncio
    async def test_daemon_uses_os_stat_for_mtime(self, tmp_path: Path) -> None:
        """Daemon MUST use os.stat() to get file mtime."""
        test_file = tmp_path / "test.py"
        test_file.write_text("y = 2\n")
        test_uri = test_file.as_uri()
        expected_mtime = 12345.678

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            mock_stat = AsyncMock()
            mock_stat.st_mtime = expected_mtime
            mock_stat.st_mtime_ns = int(expected_mtime * 1e9)

            with patch("os.stat", return_value=mock_stat):
                await handler._handle_lsp_method(
                    LSPConstants.DIAGNOSTIC,
                    {"filePath": str(test_file), "workspacePath": str(tmp_path)},
                )

        mock_client.request.assert_called_once()
        lsp_params = mock_client.request.call_args[0][1]
        assert lsp_params["_mtime"] == expected_mtime

    @pytest.mark.asyncio
    async def test_daemon_passes_correct_uri_in_lsp_params(self, tmp_path: Path) -> None:
        """Daemon MUST pass the correct URI in LSP params."""
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
            mock_client.request = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=expected_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            await handler._handle_lsp_method(
                LSPConstants.DIAGNOSTIC,
                {"filePath": str(test_file), "workspacePath": str(tmp_path)},
            )

        mock_client.request.assert_called_once()
        lsp_params = mock_client.request.call_args[0][1]
        assert lsp_params["textDocument"]["uri"] == expected_uri


class TestDaemonMtimeStatFailure:
    """Tests for daemon behavior when os.stat fails."""

    @pytest.mark.asyncio
    async def test_daemon_handles_stat_failure_gracefully(self, tmp_path: Path) -> None:
        """Daemon MUST handle stat failures gracefully and still make the request."""
        test_file = tmp_path / "missing.py"
        test_file.write_text("x = 1\n")
        test_uri = test_file.as_uri()

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            with patch("os.stat", side_effect=OSError("File not found")):
                await handler._handle_lsp_method(
                    LSPConstants.DIAGNOSTIC,
                    {"filePath": str(test_file), "workspacePath": str(tmp_path)},
                )

        # Verify request was still made
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_daemon_omits_mtime_when_stat_fails(self, tmp_path: Path) -> None:
        """When os.stat fails, daemon MUST omit mtime from params."""
        test_file = tmp_path / "stat_error.py"
        test_file.write_text("x = 1\n")
        test_uri = test_file.as_uri()

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = AsyncMock()
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=[])
            mock_client.open_document = AsyncMock(return_value=test_uri)
            mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)
            mock_ws.return_value = mock_workspace

            with patch("os.stat", side_effect=PermissionError("Access denied")):
                await handler._handle_lsp_method(
                    LSPConstants.DIAGNOSTIC,
                    {"filePath": str(test_file), "workspacePath": str(tmp_path)},
                )

        mock_client.request.assert_called_once()
        lsp_params = mock_client.request.call_args[0][1]
        # mtime should NOT be in params when stat fails
        assert "_mtime" not in lsp_params


class TestDaemonMtimeCacheIntegration:
    """Tests for daemon + client cache interaction via mtime."""

    @pytest.mark.asyncio
    async def test_second_diagnostic_request_uses_cache_via_mtime(
        self, tmp_path: Path
    ) -> None:
        """Second request with same mtime MUST use cached diagnostics (no server hit)."""
        from llm_lsp_cli.lsp.client import LSPClient

        test_file = tmp_path / "cached.py"
        test_file.write_text("cached_var = 1\n")
        test_uri = test_file.as_uri()
        mtime = os.stat(test_file).st_mtime

        client = LSPClient(
            workspace_path=str(tmp_path),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

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

        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock()
        client._transport = mock_transport

        # Use new request() method with _mtime in params
        result = await client.request(
            LSPConstants.DIAGNOSTIC,
            {"textDocument": {"uri": test_uri}, "_mtime": mtime},
        )

        # Server should NOT have been called (cache hit)
        mock_transport.send_request.assert_not_called()
        assert result == cached_diagnostics
