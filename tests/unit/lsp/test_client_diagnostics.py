"""Tests for LSP client diagnostics functionality."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from llm_lsp_cli.lsp.client import LSPClient


class TestClientDiagnosticCache:
    """Tests for diagnostic caching in LSPClient."""

    async def test_handle_diagnostics_caches_results(self, temp_dir: Path) -> None:
        """Test that publishDiagnostics notifications are cached."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        # Create a test file in the workspace
        test_file = temp_dir / "file.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        test_diagnostics = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Test error",
                "source": "test",
            }
        ]

        params = {"uri": test_uri, "diagnostics": test_diagnostics}

        # Call the handler
        client._handle_diagnostics(params)

        # Give the async task time to complete
        await asyncio.sleep(0.01)

        # Verify diagnostics were cached using the new API
        cached = await client._diagnostic_cache.get_diagnostics(test_uri)
        assert cached == test_diagnostics


class TestClientRequestDiagnostics:
    """Tests for request_diagnostics method."""

    async def test_request_diagnostics_returns_diagnostics(self, temp_dir: Path) -> None:
        """Test that request_diagnostics returns diagnostics list."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        # Mock the transport
        mock_transport = AsyncMock()
        mock_response = {
            "kind": "full",
            "items": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                    "severity": 1,
                    "message": "Type error",
                    "source": "pyright",
                }
            ],
        }
        mock_transport.send_request = AsyncMock(return_value=mock_response)
        client._transport = mock_transport

        # Mock _ensure_open to return a known URI
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = "file:///tmp/test/file.py"

            # Call request_diagnostics
            result = await client.request_diagnostics("/tmp/test/file.py")

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["message"] == "Type error"

    async def test_request_diagnostics_fallback_to_cache(self, temp_dir: Path) -> None:
        """Test that request_diagnostics falls back to cached diagnostics on error."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        # Pre-populate cache using the new API
        test_uri = "file:///tmp/test/file.py"
        cached_diagnostics = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 2,
                "message": "Cached warning",
                "source": "cache",
            }
        ]
        await client._diagnostic_cache.update_diagnostics(test_uri, cached_diagnostics)

        # Mock transport to raise an exception
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(side_effect=Exception("Method not supported"))
        client._transport = mock_transport

        # Mock _ensure_open
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Call request_diagnostics
            result = await client.request_diagnostics("/tmp/test/file.py")

        # Verify fallback to cache
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["message"] == "Cached warning"


class TestClientWorkspaceDiagnostics:
    """Tests for request_workspace_diagnostics method."""

    async def test_request_workspace_diagnostics_waits_for_indexing(self, temp_dir: Path) -> None:
        """Test that workspace diagnostics waits for workspace indexing."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        # Create test file and pre-populate cache using the new API
        test_file = temp_dir / "file.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        cached_diagnostics = [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "severity": 1,
                "message": "Workspace error",
                "source": "pyright",
            }
        ]
        await client._diagnostic_cache.update_diagnostics(test_uri, cached_diagnostics)

        # Mock the transport (not used in push mode fallback, but needed for initialization)
        mock_transport = AsyncMock()
        client._transport = mock_transport

        # Mark workspace as indexed
        client._workspace_indexed.set()

        # Call request_workspace_diagnostics
        result = await client.request_workspace_diagnostics()

        # Verify the result (push mode returns cached diagnostics via unified cache)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["uri"] == test_uri
        assert len(result[0]["diagnostics"]) == 1
