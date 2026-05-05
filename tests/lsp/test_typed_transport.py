"""Tests for TypedLSPTransport wrapper.

These tests verify that the typed transport properly validates LSP responses
and returns typed Pydantic models instead of raw dicts.
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError


class TestTypedLSPTransport:
    """Tests for TypedLSPTransport typed wrapper methods."""

    @pytest.fixture
    def mock_transport(self) -> AsyncMock:
        """Mock StdioTransport for testing."""
        mock = AsyncMock()
        mock.send_request = AsyncMock()
        return mock

    @pytest.fixture
    def typed_transport(self, mock_transport: AsyncMock) -> Any:
        """TypedLSPTransport with mocked underlying transport."""
        from llm_lsp_cli.lsp.typed_transport import TypedLSPTransport

        return TypedLSPTransport(mock_transport)

    @pytest.mark.asyncio
    async def test_send_initialize_validates_response(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_initialize validates and returns InitializeResult."""
        from llm_lsp_cli.lsp.types import InitializeResult

        mock_transport.send_request.return_value = {
            "capabilities": {"hoverProvider": True},
            "serverInfo": {"name": "test"},
        }

        result = await typed_transport.send_initialize({"rootUri": "file:///test"})

        assert isinstance(result, InitializeResult)
        assert result.server_info is not None
        assert result.server_info.get("name") == "test"

    @pytest.mark.asyncio
    async def test_send_initialize_invalid_response_raises(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_initialize raises ValidationError for invalid response."""
        mock_transport.send_request.return_value = {"invalid": "data"}

        with pytest.raises(ValidationError):
            await typed_transport.send_initialize({"rootUri": "file:///test"})

    @pytest.mark.asyncio
    async def test_send_hover_returns_none_when_no_result(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_hover returns None when server returns null."""
        mock_transport.send_request.return_value = None

        result = await typed_transport.send_hover(
            {
                "textDocument": {"uri": "file:///test.py"},
                "position": {"line": 0, "character": 0},
            }
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_send_hover_validates_hover_response(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_hover validates Hover response."""
        from llm_lsp_cli.lsp.types import Hover

        mock_transport.send_request.return_value = {
            "contents": {"kind": "markdown", "value": "test hover"}
        }

        result = await typed_transport.send_hover(
            {
                "textDocument": {"uri": "file:///test.py"},
                "position": {"line": 0, "character": 0},
            }
        )

        assert isinstance(result, Hover)
        assert result.contents is not None

    @pytest.mark.asyncio
    async def test_send_definition_returns_location_list(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_definition returns list of validated Locations."""
        from llm_lsp_cli.lsp.types import Location

        mock_transport.send_request.return_value = [
            {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            }
        ]

        result = await typed_transport.send_definition(
            {
                "textDocument": {"uri": "file:///test.py"},
                "position": {"line": 0, "character": 0},
            }
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Location)

    @pytest.mark.asyncio
    async def test_send_references_returns_location_list(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_references returns list of validated Locations."""
        from llm_lsp_cli.lsp.types import Location

        mock_transport.send_request.return_value = [
            {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 10},
                },
            }
        ]

        result = await typed_transport.send_references(
            {
                "textDocument": {"uri": "file:///test.py"},
                "position": {"line": 0, "character": 0},
                "context": {"includeDeclaration": True},
            }
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Location)

    @pytest.mark.asyncio
    async def test_send_completion_returns_completion_list(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_completion returns validated CompletionList."""
        from llm_lsp_cli.lsp.types import CompletionList

        mock_transport.send_request.return_value = {
            "isIncomplete": False,
            "items": [{"label": "test_func", "kind": 3}],
        }

        result = await typed_transport.send_completion(
            {
                "textDocument": {"uri": "file:///test.py"},
                "position": {"line": 0, "character": 0},
            }
        )

        assert isinstance(result, CompletionList)
        assert result.is_incomplete is False

    @pytest.mark.asyncio
    async def test_send_document_symbol_returns_symbol_list(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_document_symbol returns list of DocumentSymbols."""
        from llm_lsp_cli.lsp.types import DocumentSymbol

        mock_transport.send_request.return_value = [
            {
                "name": "test_func",
                "kind": 12,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 5, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            }
        ]

        result = await typed_transport.send_document_symbol(
            {"textDocument": {"uri": "file:///test.py"}}
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], DocumentSymbol)

    @pytest.mark.asyncio
    async def test_send_prepare_call_hierarchy_returns_items(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_prepare_call_hierarchy returns list of CallHierarchyItems."""
        from llm_lsp_cli.lsp.types import CallHierarchyItem

        mock_transport.send_request.return_value = [
            {
                "name": "test_func",
                "kind": 12,
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 5, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            }
        ]

        result = await typed_transport.send_prepare_call_hierarchy(
            {
                "textDocument": {"uri": "file:///test.py"},
                "position": {"line": 0, "character": 5},
            }
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], CallHierarchyItem)

    @pytest.mark.asyncio
    async def test_send_incoming_calls_validates_response(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_incoming_calls validates CallHierarchyIncomingCall response."""
        from llm_lsp_cli.lsp.types import CallHierarchyIncomingCall

        mock_transport.send_request.return_value = [
            {
                "from": {
                    "name": "caller",
                    "kind": 12,
                    "uri": "file:///caller.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 5, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                },
                "fromRanges": [],
            }
        ]

        result = await typed_transport.send_incoming_calls({"item": {}})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], CallHierarchyIncomingCall)
        assert result[0].from_.name == "caller"

    @pytest.mark.asyncio
    async def test_send_outgoing_calls_validates_response(
        self, typed_transport: Any, mock_transport: AsyncMock
    ) -> None:
        """send_outgoing_calls validates CallHierarchyOutgoingCall response."""
        from llm_lsp_cli.lsp.types import CallHierarchyOutgoingCall

        mock_transport.send_request.return_value = [
            {
                "to": {
                    "name": "callee",
                    "kind": 12,
                    "uri": "file:///callee.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 5, "character": 0},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                },
                "fromRanges": [],
            }
        ]

        result = await typed_transport.send_outgoing_calls({"item": {}})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], CallHierarchyOutgoingCall)
        assert result[0].to.name == "callee"


class TestTypedLSPTransportGateway:
    """Tests that TypedLSPTransport exposes all necessary gateway methods."""

    @pytest.fixture
    def gateway_mock_transport(self) -> AsyncMock:
        """Mock StdioTransport for testing gateway methods."""
        mock = AsyncMock()
        mock.send_request = AsyncMock()
        mock.send_notification = AsyncMock()
        mock.on_notification = AsyncMock()
        mock.on_request = AsyncMock()
        return mock

    @pytest.fixture
    def gateway_typed_transport(self, gateway_mock_transport: AsyncMock) -> Any:
        """TypedLSPTransport with mocked underlying transport."""
        from llm_lsp_cli.lsp.typed_transport import TypedLSPTransport
        return TypedLSPTransport(gateway_mock_transport)

    def test_has_send_notification_delegate(self, gateway_typed_transport: Any) -> None:
        """T6.1: TypedLSPTransport has send_notification method."""
        assert hasattr(gateway_typed_transport, "send_notification")

    def test_has_on_notification_delegate(self, gateway_typed_transport: Any) -> None:
        """T6.2: TypedLSPTransport has on_notification method."""
        assert hasattr(gateway_typed_transport, "on_notification")

    def test_has_on_request_delegate(self, gateway_typed_transport: Any) -> None:
        """T6.3: TypedLSPTransport has on_request method."""
        assert hasattr(gateway_typed_transport, "on_request")

    def test_has_transport_property(self, gateway_typed_transport: Any) -> None:
        """T6.4: TypedLSPTransport exposes underlying transport property."""
        assert hasattr(gateway_typed_transport, "_transport")

    @pytest.mark.asyncio
    async def test_send_notification_delegates_to_transport(
        self, gateway_typed_transport: Any, gateway_mock_transport: AsyncMock
    ) -> None:
        """T6.5: send_notification delegates to underlying transport."""
        if hasattr(gateway_typed_transport, "send_notification"):
            await gateway_typed_transport.send_notification("test/method", {"key": "value"})
            gateway_mock_transport.send_notification.assert_called_once_with(
                "test/method", {"key": "value"}
            )

    def test_on_notification_delegates_to_transport(
        self, gateway_typed_transport: Any, gateway_mock_transport: AsyncMock
    ) -> None:
        """T6.6: on_notification delegates to underlying transport."""
        from unittest.mock import Mock
        handler = Mock()
        if hasattr(gateway_typed_transport, "on_notification"):
            gateway_typed_transport.on_notification("test/notif", handler)
            gateway_mock_transport.on_notification.assert_called_once_with("test/notif", handler)

    def test_on_request_delegates_to_transport(
        self, gateway_typed_transport: Any, gateway_mock_transport: AsyncMock
    ) -> None:
        """T6.7: on_request delegates to underlying transport."""
        from unittest.mock import Mock
        handler = Mock()
        if hasattr(gateway_typed_transport, "on_request"):
            gateway_typed_transport.on_request("test/req", handler)
            gateway_mock_transport.on_request.assert_called_once_with("test/req", handler)
