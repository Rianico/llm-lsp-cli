"""Unit tests for LSPClient document sync methods."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient
from llm_lsp_cli.lsp.constants import LSPConstants


@pytest.fixture
def mock_transport() -> AsyncMock:
    """Mock StdioTransport."""
    transport = AsyncMock()
    transport.send_notification = AsyncMock()
    transport.send_request = AsyncMock()
    transport.on_notification = MagicMock()
    transport.on_request = MagicMock()
    return transport


@pytest.fixture
def lsp_client(tmp_path: Path) -> LSPClient:
    """Create an LSPClient instance for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return LSPClient(
        workspace_path=str(workspace),
        server_command="pyright-langserver",
        server_args=["--stdio"],
        language_id="python",
    )


class TestOpenDocument:
    """Tests for LSPClient.open_document() method."""

    @pytest.mark.asyncio
    async def test_open_document_sends_didopen_notification(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify textDocument/didOpen sent with correct params."""
        # Set up transport
        lsp_client._transport = mock_transport

        # Create test file
        test_file = tmp_path / "test.py"
        test_content = "def hello():\n    pass\n"
        test_file.write_text(test_content)

        # Call open_document
        uri = await lsp_client.open_document(test_file, test_content)

        # Verify notification was sent
        mock_transport.send_notification.assert_called_once()
        call_args = mock_transport.send_notification.call_args

        # Verify method
        assert call_args[0][0] == LSPConstants.TEXT_DOCUMENT_DID_OPEN

        # Verify params structure
        params = call_args[0][1]
        assert "textDocument" in params
        text_doc = params["textDocument"]
        assert text_doc["uri"] == uri
        assert text_doc["languageId"] == "python"
        assert text_doc["version"] == 1
        assert text_doc["text"] == test_content

    @pytest.mark.asyncio
    async def test_open_document_returns_uri(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify method returns file URI."""
        lsp_client._transport = mock_transport

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        uri = await lsp_client.open_document(test_file, "content")

        assert uri == test_file.as_uri()
        assert uri.startswith("file://")

    @pytest.mark.asyncio
    async def test_open_document_with_nested_file(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify open_document works with nested file paths."""
        lsp_client._transport = mock_transport

        nested_dir = tmp_path / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "module.py"
        test_file.write_text("content")

        uri = await lsp_client.open_document(test_file, "content")

        assert uri == test_file.as_uri()


class TestCloseDocument:
    """Tests for LSPClient.close_document() method."""

    @pytest.mark.asyncio
    async def test_close_document_sends_didclose_notification(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
    ) -> None:
        """Verify textDocument/didClose sent with correct params."""
        lsp_client._transport = mock_transport

        test_uri = "file:///test/file.py"

        await lsp_client.close_document(test_uri)

        # Verify notification was sent
        mock_transport.send_notification.assert_called_once()
        call_args = mock_transport.send_notification.call_args

        # Verify method
        assert call_args[0][0] == LSPConstants.TEXT_DOCUMENT_DID_CLOSE

        # Verify params structure
        params = call_args[0][1]
        assert "textDocument" in params
        assert params["textDocument"]["uri"] == test_uri

    @pytest.mark.asyncio
    async def test_close_document_with_different_uris(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
    ) -> None:
        """Verify close_document works with various URI formats."""
        lsp_client._transport = mock_transport

        uris = [
            "file:///home/user/project/module.py",
            "file:///tmp/test.py",
            "file:///var/www/app/views.py",
        ]

        for uri in uris:
            mock_transport.send_notification.reset_mock()
            await lsp_client.close_document(uri)

            call_args = mock_transport.send_notification.call_args
            assert call_args[0][1]["textDocument"]["uri"] == uri
