"""Tests for LSPClient URI parameter support (P3)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp.client import LSPClient


@pytest.fixture
def mock_transport() -> AsyncMock:
    """Mock StdioTransport."""
    transport = AsyncMock()
    transport.send_request = AsyncMock(return_value={"items": []})
    transport.send_notification = AsyncMock()
    transport.on_notification = MagicMock()
    transport.on_request = MagicMock()
    return transport


@pytest.fixture
def lsp_client(tmp_path: Path) -> LSPClient:
    """Create LSPClient for testing."""
    return LSPClient(
        workspace_path=str(tmp_path),
        server_command="pyright-langserver",
        server_args=["--stdio"],
        language_id="python",
    )


class TestRequestDiagnosticsUriParameter:
    """Tests for request_diagnostics with optional URI parameter (P3)."""

    @pytest.mark.asyncio
    async def test_request_diagnostics_with_uri_parameter(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
    ) -> None:
        """Verify request_diagnostics uses provided URI."""
        lsp_client._transport = mock_transport

        test_uri = "file:///test/file.py"

        # Call with explicit URI (should skip _ensure_open)
        result = await lsp_client.request_diagnostics(file_path="ignored.py", uri=test_uri)

        # Verify transport.send_request called with provided URI
        call_args = mock_transport.send_request.call_args
        params = call_args[0][1]
        assert params["textDocument"]["uri"] == test_uri

    @pytest.mark.asyncio
    async def test_request_diagnostics_without_uri_falls_back_to_ensure_open(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify request_diagnostics falls back to _ensure_open when no URI."""
        lsp_client._transport = mock_transport

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        # Mock _ensure_open to track if it was called
        with patch.object(lsp_client, "_ensure_open", return_value=test_file.as_uri()) as mock_ensure:
            # Call without URI (backward compatibility)
            result = await lsp_client.request_diagnostics(file_path=str(test_file))

            # Verify _ensure_open was called
            mock_ensure.assert_called_once_with(str(test_file))

    @pytest.mark.asyncio
    async def test_request_diagnostics_backward_compatibility(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify request_diagnostics works without uri parameter (backward compat)."""
        lsp_client._transport = mock_transport

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        # This should work without uri parameter
        result = await lsp_client.request_diagnostics(file_path=str(test_file))

        # Verify request was sent
        mock_transport.send_request.assert_called_once()


class TestRequestDocumentSymbolsUriParameter:
    """Tests for request_document_symbols with optional URI parameter (P3)."""

    @pytest.mark.asyncio
    async def test_request_document_symbols_with_uri_parameter(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
    ) -> None:
        """Verify request_document_symbols uses provided URI."""
        lsp_client._transport = mock_transport

        test_uri = "file:///test/file.py"

        result = await lsp_client.request_document_symbols(file_path="ignored.py", uri=test_uri)

        call_args = mock_transport.send_request.call_args
        params = call_args[0][1]
        assert params["textDocument"]["uri"] == test_uri

    @pytest.mark.asyncio
    async def test_request_document_symbols_without_uri_falls_back(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify request_document_symbols falls back to _ensure_open."""
        lsp_client._transport = mock_transport

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        with patch.object(lsp_client, "_ensure_open", return_value=test_file.as_uri()) as mock_ensure:
            result = await lsp_client.request_document_symbols(file_path=str(test_file))

            mock_ensure.assert_called_once_with(str(test_file))

    @pytest.mark.asyncio
    async def test_request_document_symbols_backward_compatibility(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify request_document_symbols works without uri parameter."""
        lsp_client._transport = mock_transport

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        result = await lsp_client.request_document_symbols(file_path=str(test_file))

        mock_transport.send_request.assert_called_once()


class TestUriParameterTypeSafety:
    """Tests for URI parameter type hints and defaults (P3)."""

    @pytest.mark.asyncio
    async def test_uri_parameter_optional_default_none(
        self,
        lsp_client: LSPClient,
        mock_transport: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Verify uri parameter defaults to None."""
        lsp_client._transport = mock_transport
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        # Call without uri (should use default None)
        result = await lsp_client.request_diagnostics(file_path=str(test_file))

        # Should work without explicit uri
        assert isinstance(result, list)
