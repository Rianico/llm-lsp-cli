"""Tests for StdioTransport.on_request method."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.constants import LSPConstants
from llm_lsp_cli.lsp.transport import StdioTransport


class TestTransportRequestHandling:
    """Test the StdioTransport.on_request method for handling server->client requests."""

    def test_on_request_registers_handler(self) -> None:
        """Test that on_request registers handler correctly."""
        transport = StdioTransport(command="test")
        handler = MagicMock()

        transport.on_request("workspace/configuration", handler)

        assert transport._request_handlers["workspace/configuration"] == handler

    async def test_handle_request_calls_handler(self) -> None:
        """Test that handle_request calls handler and sends response."""
        transport = StdioTransport(command="test")
        handler = AsyncMock(return_value={"result": "value"})
        transport.on_request("workspace/configuration", handler)

        # Mock _send_payload
        transport._send_payload = AsyncMock()

        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "workspace/configuration",
            "params": {"items": []},
        }

        await transport._handle_request(request_data)

        handler.assert_called_once_with({"items": []})
        transport._send_payload.assert_called_once()
        response = transport._send_payload.call_args[0][0]
        assert response["id"] == 1
        assert response["result"] == {"result": "value"}
        assert "error" not in response

    async def test_handle_request_sends_error_on_handler_exception(self) -> None:
        """Test that handler exceptions send error response."""
        transport = StdioTransport(command="test")
        handler = AsyncMock(side_effect=Exception("Handler error"))
        transport.on_request("test/method", handler)
        transport._send_payload = AsyncMock()

        request_data = {"jsonrpc": "2.0", "id": 2, "method": "test/method", "params": {}}

        await transport._handle_request(request_data)

        transport._send_payload.assert_called_once()
        response = transport._send_payload.call_args[0][0]
        assert response["id"] == 2
        assert "error" in response
        assert response["error"]["code"] == LSPConstants.ERROR_INTERNAL_ERROR

    async def test_handle_request_sends_error_for_unknown_method(self) -> None:
        """Test that unknown methods are logged and ignored."""
        transport = StdioTransport(command="test")
        transport._send_payload = AsyncMock()

        request_data = {"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}}

        await transport._handle_request(request_data)

        # Unknown methods are silently ignored (no error sent)
        transport._send_payload.assert_not_called()
