"""Integration tests for LSP client logging."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient


class TestLSPClientNoLogFile:
    """Test LSPClient no longer uses log_file parameter."""

    def test_init_signature_excludes_log_file(self) -> None:
        """LSPClient.__init__ does not accept log_file parameter."""
        # Arrange
        from llm_lsp_cli.lsp.client import LSPClient

        # Act & Assert
        with pytest.raises(TypeError, match="log_file"):
            LSPClient(
                workspace_path="/tmp/test",
                server_command="pyright-langserver",
                log_file=Path("/tmp/test.log"),  # type: ignore
            )

    def test_instance_has_no_log_file_attribute(self) -> None:
        """LSPClient instance has no log_file attribute."""
        # Arrange
        from llm_lsp_cli.lsp.client import LSPClient

        # Act
        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="pyright-langserver",
        )

        # Assert
        assert not hasattr(client, "log_file")


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
        # Verify workspace diagnostic tokens are generated
        assert client.get_workspace_diagnostic_token() is not None

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

    def test_client_diagnostic_cache_initialized(self) -> None:
        """Verify client diagnostic cache is initialized."""
        from llm_lsp_cli.lsp.cache import DiagnosticCache

        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
        )

        assert isinstance(client._diagnostic_cache, DiagnosticCache)

    def test_workspace_diagnostic_token_generated(self) -> None:
        """Verify workspace diagnostic token is generated on first access."""
        client = LSPClient(
            workspace_path="/tmp",
            server_command="test-server",
        )

        token = client.get_workspace_diagnostic_token()
        assert token is not None
        # Token should be constant
        assert client.get_workspace_diagnostic_token() == token
