"""Tests for daemon request handlers."""

from unittest.mock import patch

import pytest

from llm_lsp_cli.daemon import RequestHandler


class TestRequestHandler:
    """Tests for RequestHandler."""

    @pytest.mark.asyncio
    async def test_ping(self) -> None:
        """Test ping request."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        result = await handler.handle("ping", {})
        assert result == {"status": "pong"}

    @pytest.mark.asyncio
    async def test_status(self) -> None:
        """Test status request."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        result = await handler.handle("status", {})
        assert result["running"] is True
        assert "socket" in result
        assert "pid" in result

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        """Test shutdown request."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        result = await handler.handle("shutdown", {})
        assert result == {"status": "shutting_down"}
        assert handler._shutdown is True

    @pytest.mark.asyncio
    async def test_unknown_method(self) -> None:
        """Test unknown method raises error."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        with pytest.raises(ValueError, match="Unknown method"):
            await handler.handle("unknown/method", {})

    @pytest.mark.asyncio
    async def test_definition_missing_filepath(self) -> None:
        """Test definition request without filePath raises error."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        with pytest.raises(ValueError, match="filePath"):
            await handler.handle("textDocument/definition", {})

    @pytest.mark.asyncio
    async def test_definition_delegates_to_registry(self) -> None:
        """Test definition request delegates to registry."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_definition") as mock_req:
            mock_req.return_value = [{"uri": "file://test.py", "range": {}}]

            result = await handler.handle("textDocument/definition", {
                "workspacePath": "/tmp/test",
                "filePath": "/tmp/test.py",
                "line": 10,
                "column": 5,
            })

            assert result == {"locations": [{"uri": "file://test.py", "range": {}}]}
            mock_req.assert_awaited_once_with(
                workspace_path="/tmp/test",
                file_path="/tmp/test.py",
                line=10,
                column=5,
            )

    @pytest.mark.asyncio
    async def test_references_missing_filepath(self) -> None:
        """Test references request without filePath raises error."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        with pytest.raises(ValueError, match="filePath"):
            await handler.handle("textDocument/references", {})

    @pytest.mark.asyncio
    async def test_references_delegates_to_registry(self) -> None:
        """Test references request delegates to registry."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_references") as mock_req:
            mock_req.return_value = [{"uri": "file://test.py", "range": {}}]

            result = await handler.handle("textDocument/references", {
                "workspacePath": "/tmp/test",
                "filePath": "/tmp/test.py",
                "line": 10,
                "column": 5,
            })

            assert result == {"locations": [{"uri": "file://test.py", "range": {}}]}

    @pytest.mark.asyncio
    async def test_completion_missing_filepath(self) -> None:
        """Test completion request without filePath raises error."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        with pytest.raises(ValueError, match="filePath"):
            await handler.handle("textDocument/completion", {})

    @pytest.mark.asyncio
    async def test_completion_delegates_to_registry(self) -> None:
        """Test completion request delegates to registry."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_completions") as mock_req:
            mock_req.return_value = [{"label": "test"}]

            result = await handler.handle("textDocument/completion", {
                "workspacePath": "/tmp/test",
                "filePath": "/tmp/test.py",
                "line": 10,
                "column": 5,
            })

            assert result == {"items": [{"label": "test"}]}

    @pytest.mark.asyncio
    async def test_hover_missing_filepath(self) -> None:
        """Test hover request without filePath raises error."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        with pytest.raises(ValueError, match="filePath"):
            await handler.handle("textDocument/hover", {})

    @pytest.mark.asyncio
    async def test_hover_delegates_to_registry(self) -> None:
        """Test hover request delegates to registry."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_hover") as mock_req:
            mock_req.return_value = {"contents": {"value": "test"}}

            result = await handler.handle("textDocument/hover", {
                "workspacePath": "/tmp/test",
                "filePath": "/tmp/test.py",
                "line": 10,
                "column": 5,
            })

            assert result == {"hover": {"contents": {"value": "test"}}}

    @pytest.mark.asyncio
    async def test_hover_null_response(self) -> None:
        """Test hover request with null response."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_hover") as mock_req:
            mock_req.return_value = None

            result = await handler.handle("textDocument/hover", {
                "workspacePath": "/tmp/test",
                "filePath": "/tmp/test.py",
                "line": 10,
                "column": 5,
            })

            assert result == {}

    @pytest.mark.asyncio
    async def test_document_symbol_missing_filepath(self) -> None:
        """Test documentSymbol request without filePath raises error."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)
        with pytest.raises(ValueError, match="filePath"):
            await handler.handle("textDocument/documentSymbol", {})

    @pytest.mark.asyncio
    async def test_document_symbol_delegates_to_registry(self) -> None:
        """Test documentSymbol request delegates to registry."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_document_symbols") as mock_req:
            mock_req.return_value = [{"name": "test", "kind": 12}]

            result = await handler.handle("textDocument/documentSymbol", {
                "workspacePath": "/tmp/test",
                "filePath": "/tmp/test.py",
            })

            assert result == {"symbols": [{"name": "test", "kind": 12}]}

    @pytest.mark.asyncio
    async def test_workspace_symbol_delegates_to_registry(self) -> None:
        """Test workspace/symbol request delegates to registry."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_workspace_symbols") as mock_req:
            mock_req.return_value = [{"name": "test", "kind": 5}]

            result = await handler.handle("workspace/symbol", {
                "workspacePath": "/tmp/test",
                "query": "test",
            })

            assert result == {"symbols": [{"name": "test", "kind": 5}]}

    @pytest.mark.asyncio
    async def test_workspace_symbol_default_query(self) -> None:
        """Test workspace/symbol with default empty query."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_workspace_symbols") as mock_req:
            mock_req.return_value = []

            result = await handler.handle("workspace/symbol", {
                "workspacePath": "/tmp/test",
            })

            assert result == {"symbols": []}
            mock_req.assert_awaited_once_with(workspace_path="/tmp/test", query="")

    @pytest.mark.asyncio
    async def test_definition_default_workspace(self) -> None:
        """Test definition uses default workspace if not provided."""
        handler = RequestHandler(workspace_path="/tmp/test", language="python", lsp_conf=None)

        with patch.object(handler._registry, "request_definition") as mock_req:
            mock_req.return_value = []

            result = await handler.handle("textDocument/definition", {
                "filePath": "/tmp/test.py",
                "line": 10,
                "column": 5,
            })

            assert result == {"locations": []}
