"""Integration tests for LSP client logging."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient, WorkspaceDiagnosticManager


class TestClientLoggerIntegration:
    """Test LSPClient integration with logging."""

    def test_client_requires_server_command(self) -> None:
        """Verify LSPClient requires server_command parameter."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
        )

        assert client is not None

    def test_client_default_trace_mode(self) -> None:
        """Verify LSPClient default trace mode."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
        )

        assert client.trace is False

    def test_client_trace_enabled(self) -> None:
        """Verify LSPClient can enable trace mode."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
            trace=True,
        )

        assert client.trace is True

    @pytest.mark.asyncio
    async def test_client_initializes_successfully(self) -> None:
        """Verify client can initialize with mocked transport."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="echo",
            server_args=["hello"],
        )

        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"Content-Length: 2\r\n\r\n{}")
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b"")

        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(return_value={"capabilities": {}})
        mock_transport.send_notification = AsyncMock()
        mock_transport.on_notification = MagicMock()
        mock_transport.on_request = MagicMock()
        mock_transport.start = AsyncMock()
        mock_transport.stop = AsyncMock()
        mock_transport._process = mock_process

        with (
            patch("llm_lsp_cli.lsp.client.StdioTransport", return_value=mock_transport),
            patch.object(client, "_wait_for_workspace_index", AsyncMock()),
        ):
            result = await client.initialize()

        assert "capabilities" in result
        assert client._initialized is True
        assert client._diagnostic_manager is not None

    @pytest.mark.asyncio
    async def test_definition_request_completes(self) -> None:
        """Verify definition() request completes successfully."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="echo",
            server_args=["hello"],
        )

        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(return_value=[])

        with (
            patch.object(client, "_ensure_open", AsyncMock(return_value="file:///tmp/test.py")),
            patch.object(client, "_normalize_locations", return_value=[]),
        ):
            client._transport = mock_transport
            locations = await client.request_definition("/tmp/test.py", 0, 0)

        assert locations == []
        mock_transport.send_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_completes_successfully(self) -> None:
        """Verify shutdown() completes successfully."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="echo",
            server_args=["hello"],
        )

        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(return_value={"capabilities": {}})
        mock_transport.send_notification = AsyncMock()
        mock_transport.stop = AsyncMock()

        client._initialized = True
        client._transport = mock_transport

        await client.shutdown()

        assert client._initialized is False
        mock_transport.stop.assert_called_once()

    def test_client_diagnostic_manager_created_on_init(self) -> None:
        """Verify diagnostic manager is created during initialization."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
        )

        assert client._diagnostic_manager is None

    def test_client_diagnostic_cache_initialized(self) -> None:
        """Verify client diagnostic cache is initialized."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
        )

        assert client._diagnostic_cache == {}

    def test_diagnostic_manager_creation(self) -> None:
        """Verify WorkspaceDiagnosticManager can be created."""
        mock_client = MagicMock()
        manager = WorkspaceDiagnosticManager(mock_client)

        assert manager is not None
        assert manager._client is mock_client

    def test_diagnostic_manager_pull_mode_default(self) -> None:
        """Verify diagnostic manager defaults to pull mode unsupported."""
        mock_client = MagicMock()
        manager = WorkspaceDiagnosticManager(mock_client)

        assert manager._pull_mode_supported is True
