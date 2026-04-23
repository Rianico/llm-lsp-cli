"""Tests for RequestHandler call hierarchy method routing."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from llm_lsp_cli.daemon import RequestHandler
from llm_lsp_cli.lsp.constants import LSPConstants


class TestRequestHandlerCallHierarchy:
    """Tests for RequestHandler call hierarchy method handling."""

    @pytest.fixture
    def mock_registry(self) -> AsyncMock:
        """Create a mock ServerRegistry for testing."""
        registry = AsyncMock()
        registry.request_call_hierarchy_incoming = AsyncMock(
            return_value=[
                {
                    "from_": {
                        "name": "caller_func",
                        "kind": 12,
                        "uri": "file:///project/src/caller.py",
                        "range": {
                            "start": {"line": 5, "character": 0},
                            "end": {"line": 10, "character": 0},
                        },
                        "selectionRange": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 5, "character": 14},
                        },
                    },
                    "fromRanges": [],
                }
            ]
        )
        registry.request_call_hierarchy_outgoing = AsyncMock(
            return_value=[
                {
                    "to": {
                        "name": "helper_func",
                        "kind": 12,
                        "uri": "file:///project/src/helper.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 5, "character": 0},
                        },
                        "selectionRange": {
                            "start": {"line": 0, "character": 4},
                            "end": {"line": 0, "character": 14},
                        },
                    },
                    "fromRanges": [],
                }
            ]
        )
        registry.get_or_create_workspace = AsyncMock()
        registry.get_or_create_workspace.return_value.ensure_initialized = AsyncMock()
        return registry

    @pytest.fixture
    def handler(self, mock_registry: AsyncMock, tmp_path: Path) -> RequestHandler:
        """Create a RequestHandler for testing."""
        handler = RequestHandler(str(tmp_path), "python")
        handler._registry = mock_registry
        return handler

    @pytest.mark.asyncio
    async def test_handle_incoming_calls_routes_correctly(
        self, handler: RequestHandler, mock_registry: AsyncMock, tmp_path: Path
    ) -> None:
        """Handle incoming calls routes to registry.request_call_hierarchy_incoming."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 0,
            "column": 4,
        }

        result = await handler.handle(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS, params)

        mock_registry.request_call_hierarchy_incoming.assert_called_once()
        assert "calls" in result

    @pytest.mark.asyncio
    async def test_handle_outgoing_calls_routes_correctly(
        self, handler: RequestHandler, mock_registry: AsyncMock, tmp_path: Path
    ) -> None:
        """Handle outgoing calls routes to registry.request_call_hierarchy_outgoing."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 0,
            "column": 4,
        }

        result = await handler.handle(LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS, params)

        mock_registry.request_call_hierarchy_outgoing.assert_called_once()
        assert "calls" in result

    @pytest.mark.asyncio
    async def test_handle_incoming_calls_response_key(
        self, handler: RequestHandler, tmp_path: Path
    ) -> None:
        """Incoming calls response should have 'calls' key."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 0,
            "column": 4,
        }

        result = await handler.handle(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS, params)

        assert "calls" in result
        assert isinstance(result["calls"], list)

    @pytest.mark.asyncio
    async def test_handle_outgoing_calls_response_key(
        self, handler: RequestHandler, tmp_path: Path
    ) -> None:
        """Outgoing calls response should have 'calls' key."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 0,
            "column": 4,
        }

        result = await handler.handle(LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS, params)

        assert "calls" in result
        assert isinstance(result["calls"], list)

    @pytest.mark.asyncio
    async def test_handle_incoming_calls_position_extraction(
        self, handler: RequestHandler, mock_registry: AsyncMock, tmp_path: Path
    ) -> None:
        """Incoming calls extracts position from params correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 5,
            "column": 10,
        }

        await handler.handle(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS, params)

        # Verify the call included position parameters
        call_args = mock_registry.request_call_hierarchy_incoming.call_args
        assert call_args[1]["line"] == 5
        assert call_args[1]["column"] == 10


class TestRequestHandlerCallHierarchyMethodRecognition:
    """Tests for RequestHandler recognizing call hierarchy methods."""

    @pytest.fixture
    def handler(self, tmp_path: Path) -> RequestHandler:
        """Create a RequestHandler for testing."""
        return RequestHandler(str(tmp_path), "python")

    def test_request_handler_recognizes_incoming_calls(self, handler: RequestHandler) -> None:
        """RequestHandler should recognize callHierarchy/incomingCalls."""
        # The handler's handle method should accept these methods
        # Check that RESPONSE_KEYS includes the method
        assert LSPConstants.CALL_HIERARCHY_INCOMING_CALLS in handler.RESPONSE_KEYS

    def test_request_handler_recognizes_outgoing_calls(self, handler: RequestHandler) -> None:
        """RequestHandler should recognize callHierarchy/outgoingCalls."""
        assert LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS in handler.RESPONSE_KEYS

    def test_incoming_calls_response_key_is_calls(self, handler: RequestHandler) -> None:
        """Incoming calls response key should be 'calls'."""
        assert handler.RESPONSE_KEYS[LSPConstants.CALL_HIERARCHY_INCOMING_CALLS] == "calls"

    def test_outgoing_calls_response_key_is_calls(self, handler: RequestHandler) -> None:
        """Outgoing calls response key should be 'calls'."""
        assert handler.RESPONSE_KEYS[LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS] == "calls"
