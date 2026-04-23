"""Tests for LSPClient call hierarchy methods (LSP 3.17)."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from llm_lsp_cli.lsp.client import LSPClient
from tests.fixtures import (
    CALL_HIERARCHY_INCOMING_RESPONSE,
    CALL_HIERARCHY_OUTGOING_RESPONSE,
    CALL_HIERARCHY_PREPARE_RESPONSE,
)


@pytest.fixture
def mock_transport_for_call_hierarchy() -> AsyncMock:
    """Create a mock transport for call hierarchy testing."""
    transport = AsyncMock()
    transport.send_request = AsyncMock()
    return transport


@pytest.fixture
def lsp_client_with_mocked_transport(
    tmp_path: Path, mock_transport_for_call_hierarchy: AsyncMock
) -> LSPClient:
    """Create an LSPClient with mocked transport for call hierarchy testing."""
    client = LSPClient(
        workspace_path=str(tmp_path),
        server_command="test",
    )
    client._transport = mock_transport_for_call_hierarchy
    client._initialized = True
    return client


class TestRequestIncomingCalls:
    """Tests for LSPClient.request_call_hierarchy_incoming method."""

    @pytest.mark.asyncio
    async def test_request_incoming_calls_happy_path(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """Request incoming calls returns CallHierarchyIncomingCall list."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to return prepare response, then incoming calls response
        transport.send_request.side_effect = [
            CALL_HIERARCHY_PREPARE_RESPONSE["items"],  # prepareCallHierarchy returns items
            CALL_HIERARCHY_INCOMING_RESPONSE["calls"],  # incomingCalls returns calls
        ]

        # Create a temp file for the test
        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert len(result) == 1
        assert result[0]["from_"]["name"] == "caller_function"

    @pytest.mark.asyncio
    async def test_request_incoming_calls_prepare_returns_null(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """If prepareCallHierarchy returns null, return empty list."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to return null from prepare
        transport.send_request.return_value = None

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_request_incoming_calls_prepare_returns_empty_array(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """If prepareCallHierarchy returns [], return empty list."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to return empty array from prepare
        transport.send_request.return_value = []

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_request_incoming_calls_followup_returns_null(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """If prepare succeeds but incomingCalls returns null, return empty list."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport: prepare returns items, incoming calls returns null
        transport.send_request.side_effect = [
            CALL_HIERARCHY_PREPARE_RESPONSE["items"],  # prepareCallHierarchy returns items
            None,  # incomingCalls returns null
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_request_incoming_calls_data_field_preserved(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """The data field from prepare response must be passed to followup request."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Create item with data field
        item_with_data = {
            "name": "my_function",
            "kind": 12,
            "uri": "file:///project/src/module.py",
            "range": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 20, "character": 0},
            },
            "selectionRange": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 16},
            },
            "data": {"opaque": "server-specific-data"},
        }

        transport.send_request.side_effect = [
            [item_with_data],  # prepareCallHierarchy returns item with data
            CALL_HIERARCHY_INCOMING_RESPONSE["calls"],  # incomingCalls response
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        # Verify the second call included the data field
        second_call_args = transport.send_request.call_args_list[1]
        item_arg = second_call_args[0][1]["item"]
        assert "data" in item_arg
        assert item_arg["data"] == {"opaque": "server-specific-data"}

    @pytest.mark.asyncio
    async def test_request_incoming_calls_method_not_found(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """If server returns MethodNotFound (-32601), return empty list with warning."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to raise LSPError with MethodNotFound code
        from llm_lsp_cli.lsp.constants import LSPConstants
        from llm_lsp_cli.lsp.transport import LSPError

        method_not_found_error = LSPError({
            "code": LSPConstants.ERROR_METHOD_NOT_FOUND,
            "message": "Method not found",
        })

        # prepareCallHierarchy succeeds, incomingCalls fails
        transport.send_request.side_effect = [
            [{"name": "func", "kind": 12, "uri": "file:///test.py",
              "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
              "selectionRange": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 4}}}],
            method_not_found_error,
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert result == []
        # Should log a warning (not error)
        assert any("not found" in record.message.lower() or "not supported" in record.message.lower()
                   for record in caplog.records)

    @pytest.mark.asyncio
    async def test_request_incoming_calls_transport_error(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """If transport raises exception, let it propagate."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to raise exception
        transport.send_request.side_effect = ConnectionError("Transport failed")

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        with pytest.raises(ConnectionError, match="Transport failed"):
            await client.request_call_hierarchy_incoming(
                file_path=str(test_file),
                line=10,
                column=4,
            )


class TestRequestOutgoingCalls:
    """Tests for LSPClient.request_call_hierarchy_outgoing method."""

    @pytest.mark.asyncio
    async def test_request_outgoing_calls_happy_path(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """Request outgoing calls returns CallHierarchyOutgoingCall list."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to return prepare response, then outgoing calls response
        transport.send_request.side_effect = [
            CALL_HIERARCHY_PREPARE_RESPONSE["items"],  # prepareCallHierarchy returns items
            CALL_HIERARCHY_OUTGOING_RESPONSE["calls"],  # outgoingCalls returns calls
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_outgoing(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert len(result) == 1
        assert result[0]["to"]["name"] == "helper_function"

    @pytest.mark.asyncio
    async def test_request_outgoing_calls_prepare_returns_null(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """If prepareCallHierarchy returns null, return empty list."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        # Mock transport to return null from prepare
        transport.send_request.return_value = None

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_outgoing(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_request_outgoing_calls_method_not_found(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """If server returns MethodNotFound (-32601), return empty list with warning."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        from llm_lsp_cli.lsp.constants import LSPConstants
        from llm_lsp_cli.lsp.transport import LSPError

        method_not_found_error = LSPError({
            "code": LSPConstants.ERROR_METHOD_NOT_FOUND,
            "message": "Method not found",
        })

        # prepareCallHierarchy succeeds, outgoingCalls fails
        transport.send_request.side_effect = [
            [{"name": "func", "kind": 12, "uri": "file:///test.py",
              "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
              "selectionRange": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 4}}}],
            method_not_found_error,
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        result = await client.request_call_hierarchy_outgoing(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        assert result == []
        # Should log a warning (not error)
        assert any("not found" in record.message.lower() or "not supported" in record.message.lower()
                   for record in caplog.records)


class TestCallHierarchyTwoStepProtocol:
    """Tests verifying the two-step call hierarchy protocol."""

    @pytest.mark.asyncio
    async def test_incoming_calls_calls_prepare_first(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """Incoming calls must call prepareCallHierarchy before incomingCalls."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        transport.send_request.side_effect = [
            CALL_HIERARCHY_PREPARE_RESPONSE["items"],
            CALL_HIERARCHY_INCOMING_RESPONSE["calls"],
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        await client.request_call_hierarchy_incoming(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        # Verify two calls were made
        assert transport.send_request.call_count == 2

        # First call should be prepareCallHierarchy
        first_call = transport.send_request.call_args_list[0]
        assert first_call[0][0] == "textDocument/prepareCallHierarchy"

        # Second call should be callHierarchy/incomingCalls
        second_call = transport.send_request.call_args_list[1]
        assert second_call[0][0] == "callHierarchy/incomingCalls"

    @pytest.mark.asyncio
    async def test_outgoing_calls_calls_prepare_first(
        self, lsp_client_with_mocked_transport: LSPClient, mock_transport_for_call_hierarchy: AsyncMock
    ) -> None:
        """Outgoing calls must call prepareCallHierarchy before outgoingCalls."""
        client = lsp_client_with_mocked_transport
        transport = mock_transport_for_call_hierarchy

        transport.send_request.side_effect = [
            CALL_HIERARCHY_PREPARE_RESPONSE["items"],
            CALL_HIERARCHY_OUTGOING_RESPONSE["calls"],
        ]

        test_file = Path(client.workspace_path) / "test.py"
        test_file.write_text("def my_function(): pass")

        await client.request_call_hierarchy_outgoing(
            file_path=str(test_file),
            line=10,
            column=4,
        )

        # Verify two calls were made
        assert transport.send_request.call_count == 2

        # First call should be prepareCallHierarchy
        first_call = transport.send_request.call_args_list[0]
        assert first_call[0][0] == "textDocument/prepareCallHierarchy"

        # Second call should be callHierarchy/outgoingCalls
        second_call = transport.send_request.call_args_list[1]
        assert second_call[0][0] == "callHierarchy/outgoingCalls"
