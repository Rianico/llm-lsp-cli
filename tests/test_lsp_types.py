"""Tests for LSP types and constants."""

from llm_lsp_cli.lsp.constants import LSPConstants
from llm_lsp_cli.lsp.types import (
    Location,
    Position,
    Range,
)


class TestPosition:
    """Tests for Position type."""

    def test_position_creation(self) -> None:
        """Test creating a position."""
        pos: Position = {"line": 10, "character": 5}
        assert pos["line"] == 10
        assert pos["character"] == 5


class TestRange:
    """Tests for Range type."""

    def test_range_creation(self) -> None:
        """Test creating a range."""
        range_obj: Range = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 10, "character": 5},
        }
        assert range_obj["start"]["line"] == 0
        assert range_obj["end"]["character"] == 5


class TestLocation:
    """Tests for Location type."""

    def test_location_creation(self) -> None:
        """Test creating a location."""
        loc: Location = {
            "uri": "file:///path/to/file.py",
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 10, "character": 5},
            },
        }
        assert "file://" in loc["uri"]
        assert "range" in loc


class TestLSPConstants:
    """Tests for LSP constants."""

    def test_jsonrpc_version(self) -> None:
        """Test JSON-RPC version constant."""
        assert LSPConstants.JSONRPC_VERSION == "2.0"

    def test_request_methods(self) -> None:
        """Test request method constants."""
        assert LSPConstants.INITIALIZE == "initialize"
        assert LSPConstants.SHUTDOWN == "shutdown"
        assert LSPConstants.EXIT == "exit"

    def test_text_document_methods(self) -> None:
        """Test text document method constants."""
        assert LSPConstants.TEXT_DOCUMENT_DID_OPEN == "textDocument/didOpen"
        assert LSPConstants.TEXT_DOCUMENT_DID_CLOSE == "textDocument/didClose"
        assert LSPConstants.COMPLETION == "textDocument/completion"
        assert LSPConstants.DEFINITION == "textDocument/definition"
        assert LSPConstants.REFERENCES == "textDocument/references"
        assert LSPConstants.HOVER == "textDocument/hover"

    def test_workspace_methods(self) -> None:
        """Test workspace method constants."""
        assert LSPConstants.WORKSPACE_SYMBOL == "workspace/symbol"

    def test_error_codes(self) -> None:
        """Test error code constants."""
        assert LSPConstants.ERROR_PARSE_ERROR == -32700
        assert LSPConstants.ERROR_INVALID_REQUEST == -32600
        assert LSPConstants.ERROR_METHOD_NOT_FOUND == -32601
        assert LSPConstants.ERROR_INTERNAL_ERROR == -32603

    def test_completion_trigger_kinds(self) -> None:
        """Test completion trigger kind constants."""
        assert LSPConstants.COMPLETION_TRIGGER_INVOKED == 1
        assert LSPConstants.COMPLETION_TRIGGER_TRIGGER_CHARACTER == 2

    def test_symbol_kinds(self) -> None:
        """Test symbol kind constants."""
        assert LSPConstants.SYMBOL_KIND_CLASS == 5
        assert LSPConstants.SYMBOL_KIND_FUNCTION == 12
        assert LSPConstants.SYMBOL_KIND_METHOD == 6
