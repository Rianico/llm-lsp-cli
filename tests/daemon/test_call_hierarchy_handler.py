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
        registry.request = AsyncMock(
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
        """Handle incoming calls routes to registry.request."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 0,
            "column": 4,
        }

        result = await handler.handle(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS, params)

        mock_registry.request.assert_called_once()
        assert "calls" in result

    @pytest.mark.asyncio
    async def test_handle_outgoing_calls_routes_correctly(
        self, handler: RequestHandler, mock_registry: AsyncMock, tmp_path: Path
    ) -> None:
        """Handle outgoing calls routes to registry.request."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 0,
            "column": 4,
        }

        # Reset mock for outgoing calls test
        mock_registry.request.return_value = [
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

        result = await handler.handle(LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS, params)

        mock_registry.request.assert_called_once()
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

    @pytest.mark.asyncio
    async def test_handle_incoming_calls_position_extraction(
        self, handler: RequestHandler, mock_registry: AsyncMock, tmp_path: Path
    ) -> None:
        """Position params should be extracted and passed correctly."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def my_func(): pass")

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
            "line": 10,
            "column": 5,
        }

        await handler.handle(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS, params)

        mock_registry.request.assert_called_once()
        call_args = mock_registry.request.call_args
        # Check that position was passed in LSP params
        lsp_params = call_args[0][2]
        assert lsp_params["position"]["line"] == 10
        assert lsp_params["position"]["character"] == 5
