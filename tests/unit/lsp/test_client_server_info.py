"""Tests for LSP client server info capture.

This module tests the server_info property in LSPClient that captures
the serverInfo from the initialize response for use in output headers.
"""

from __future__ import annotations

import pytest


class TestLSPClientServerInfo:
    """Test server info capture from initialize response."""

    @pytest.mark.asyncio
    async def test_server_info_property_after_initialize(self) -> None:
        """server_info returns dict after initialize() completes."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from llm_lsp_cli.lsp import types as lsp
        from llm_lsp_cli.lsp.client import LSPClient

        # Create a mock TypedLSPTransport
        mock_typed_transport = MagicMock()
        mock_typed_transport.start = AsyncMock()
        mock_typed_transport.send_notification = AsyncMock()
        mock_typed_transport.send_request_fire_and_forget = AsyncMock()
        mock_typed_transport.on_notification = MagicMock()
        mock_typed_transport.on_request = MagicMock()
        mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
            capabilities=lsp.ServerCapabilities(),
            server_info={"name": "test-server"}
        ))

        with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
            client = LSPClient(
                workspace_path="/tmp/test",
                server_command="test-server",
            )
            await client.initialize()

            assert client.server_info == {"name": "test-server"}

    @pytest.mark.asyncio
    async def test_server_info_empty_when_not_present(self) -> None:
        """server_info returns {} when response lacks serverInfo."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from llm_lsp_cli.lsp import types as lsp
        from llm_lsp_cli.lsp.client import LSPClient

        mock_typed_transport = MagicMock()
        mock_typed_transport.start = AsyncMock()
        mock_typed_transport.send_notification = AsyncMock()
        mock_typed_transport.send_request_fire_and_forget = AsyncMock()
        mock_typed_transport.on_notification = MagicMock()
        mock_typed_transport.on_request = MagicMock()
        # No server_info in InitializeResult
        mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
            capabilities=lsp.ServerCapabilities()
        ))

        with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
            client = LSPClient(
                workspace_path="/tmp/test",
                server_command="test-server",
            )
            await client.initialize()

            assert client.server_info == {}

    @pytest.mark.asyncio
    async def test_server_info_full_object_preserved(self) -> None:
        """Complete serverInfo object captured, not just name."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from llm_lsp_cli.lsp import types as lsp
        from llm_lsp_cli.lsp.client import LSPClient

        mock_typed_transport = MagicMock()
        mock_typed_transport.start = AsyncMock()
        mock_typed_transport.send_notification = AsyncMock()
        mock_typed_transport.send_request_fire_and_forget = AsyncMock()
        mock_typed_transport.on_notification = MagicMock()
        mock_typed_transport.on_request = MagicMock()
        mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
            capabilities=lsp.ServerCapabilities(),
            server_info={"name": "pyright", "version": "1.2.3"}
        ))

        with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
            client = LSPClient(
                workspace_path="/tmp/test",
                server_command="test-server",
            )
            await client.initialize()

            assert client.server_info["name"] == "pyright"
            assert client.server_info["version"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_server_info_multiple_initializes(self) -> None:
        """Server info updated on subsequent initialize calls."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from llm_lsp_cli.lsp import types as lsp
        from llm_lsp_cli.lsp.client import LSPClient

        mock_typed_transport = MagicMock()
        mock_typed_transport.start = AsyncMock()
        mock_typed_transport.send_notification = AsyncMock()
        mock_typed_transport.send_request_fire_and_forget = AsyncMock()
        mock_typed_transport.on_notification = MagicMock()
        mock_typed_transport.on_request = MagicMock()

        with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
            client = LSPClient(
                workspace_path="/tmp/test",
                server_command="test-server",
            )

            # First initialize returns server A
            mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
                capabilities=lsp.ServerCapabilities(),
                server_info={"name": "server-a"}
            ))
            await client.initialize()
            assert client.server_info["name"] == "server-a"

            # Reset for second initialize
            client._initialized = False

            # Second initialize returns server B
            mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
                capabilities=lsp.ServerCapabilities(),
                server_info={"name": "server-b"}
            ))
            await client.initialize()
            assert client.server_info["name"] == "server-b"

    @pytest.mark.asyncio
    async def test_server_info_property_exists(self) -> None:
        """LSPClient has server_info property."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="test-server",
        )

        # Property should exist and return empty dict before initialize
        assert hasattr(client, "server_info")
        # Before initialize, should return empty dict
        assert client.server_info == {}

    @pytest.mark.asyncio
    async def test_server_info_with_basedpyright_response(self) -> None:
        """Server info correctly captured from basedpyright initialize response."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from llm_lsp_cli.lsp import types as lsp
        from llm_lsp_cli.lsp.client import LSPClient

        mock_typed_transport = MagicMock()
        mock_typed_transport.start = AsyncMock()
        mock_typed_transport.send_notification = AsyncMock()
        mock_typed_transport.send_request_fire_and_forget = AsyncMock()
        mock_typed_transport.on_notification = MagicMock()
        mock_typed_transport.on_request = MagicMock()
        mock_typed_transport.send_initialize = AsyncMock(return_value=lsp.InitializeResult(
            capabilities=lsp.ServerCapabilities(),
            server_info={"name": "basedpyright", "version": "1.15.0"}
        ))

        with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
            client = LSPClient(
                workspace_path="/tmp/test",
                server_command="basedpyright-langserver",
            )
            await client.initialize()

            assert client.server_info["name"] == "basedpyright"
            assert client.server_info["version"] == "1.15.0"

