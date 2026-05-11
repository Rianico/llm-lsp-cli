"""Tests for LSPConstants Final[str] attributes (Step 1 of ADR-0028).

These tests verify that LSPConstants method-name attributes are annotated as Final[str],
enabling type narrowing for @overload matching.

Note: Python's Final is a type hint only and doesn't enforce runtime immutability.
The real benefit is that type checkers can narrow Final[str] to Literal["value"].
"""

import typing
from typing import get_type_hints

import pytest

from llm_lsp_cli.lsp.constants import LSPConstants


class TestLSPConstantsFinal:
    """Test that method-name attributes are annotated as Final[str]."""

    def test_definition_is_final_str(self) -> None:
        """DEFINITION should be annotated as Final[str] to enable type narrowing."""
        assert LSPConstants.DEFINITION == "textDocument/definition"
        # Verify the annotation is Final[str]
        hints = get_type_hints(LSPConstants)
        assert "DEFINITION" in hints
        # Final[str] appears as typing.Final in the hints
        origin = typing.get_origin(hints["DEFINITION"])
        assert origin is typing.Final or str(hints["DEFINITION"]).startswith("typing.Final")

    def test_hover_is_final_str(self) -> None:
        """HOVER should be annotated as Final[str]."""
        assert LSPConstants.HOVER == "textDocument/hover"
        hints = get_type_hints(LSPConstants)
        assert "HOVER" in hints
        origin = typing.get_origin(hints["HOVER"])
        assert origin is typing.Final or str(hints["HOVER"]).startswith("typing.Final")

    def test_document_symbol_is_final_str(self) -> None:
        """DOCUMENT_SYMBOL should be annotated as Final[str]."""
        assert LSPConstants.DOCUMENT_SYMBOL == "textDocument/documentSymbol"
        hints = get_type_hints(LSPConstants)
        assert "DOCUMENT_SYMBOL" in hints
        origin = typing.get_origin(hints["DOCUMENT_SYMBOL"])
        assert origin is typing.Final or str(hints["DOCUMENT_SYMBOL"]).startswith("typing.Final")

    def test_completion_is_final_str(self) -> None:
        """COMPLETION should be annotated as Final[str]."""
        assert LSPConstants.COMPLETION == "textDocument/completion"
        hints = get_type_hints(LSPConstants)
        assert "COMPLETION" in hints
        origin = typing.get_origin(hints["COMPLETION"])
        assert origin is typing.Final or str(hints["COMPLETION"]).startswith("typing.Final")

    def test_references_is_final_str(self) -> None:
        """REFERENCES should be annotated as Final[str]."""
        assert LSPConstants.REFERENCES == "textDocument/references"
        hints = get_type_hints(LSPConstants)
        assert "REFERENCES" in hints
        origin = typing.get_origin(hints["REFERENCES"])
        assert origin is typing.Final or str(hints["REFERENCES"]).startswith("typing.Final")

    def test_prepare_rename_is_final_str(self) -> None:
        """PREPARE_RENAME should be annotated as Final[str]."""
        assert LSPConstants.PREPARE_RENAME == "textDocument/prepareRename"
        hints = get_type_hints(LSPConstants)
        assert "PREPARE_RENAME" in hints
        origin = typing.get_origin(hints["PREPARE_RENAME"])
        assert origin is typing.Final or str(hints["PREPARE_RENAME"]).startswith("typing.Final")

    def test_rename_is_final_str(self) -> None:
        """RENAME should be annotated as Final[str]."""
        assert LSPConstants.RENAME == "textDocument/rename"
        hints = get_type_hints(LSPConstants)
        assert "RENAME" in hints
        origin = typing.get_origin(hints["RENAME"])
        assert origin is typing.Final or str(hints["RENAME"]).startswith("typing.Final")

    def test_workspace_symbol_is_final_str(self) -> None:
        """WORKSPACE_SYMBOL should be annotated as Final[str]."""
        assert LSPConstants.WORKSPACE_SYMBOL == "workspace/symbol"
        hints = get_type_hints(LSPConstants)
        assert "WORKSPACE_SYMBOL" in hints
        origin = typing.get_origin(hints["WORKSPACE_SYMBOL"])
        assert origin is typing.Final or str(hints["WORKSPACE_SYMBOL"]).startswith("typing.Final")

    def test_diagnostic_is_final_str(self) -> None:
        """DIAGNOSTIC should be annotated as Final[str]."""
        assert LSPConstants.DIAGNOSTIC == "textDocument/diagnostic"
        hints = get_type_hints(LSPConstants)
        assert "DIAGNOSTIC" in hints
        origin = typing.get_origin(hints["DIAGNOSTIC"])
        assert origin is typing.Final or str(hints["DIAGNOSTIC"]).startswith("typing.Final")

    def test_workspace_diagnostic_is_final_str(self) -> None:
        """WORKSPACE_DIAGNOSTIC should be annotated as Final[str]."""
        assert LSPConstants.WORKSPACE_DIAGNOSTIC == "workspace/diagnostic"
        hints = get_type_hints(LSPConstants)
        assert "WORKSPACE_DIAGNOSTIC" in hints
        origin = typing.get_origin(hints["WORKSPACE_DIAGNOSTIC"])
        assert origin is typing.Final or str(hints["WORKSPACE_DIAGNOSTIC"]).startswith("typing.Final")

    def test_call_hierarchy_incoming_calls_is_final_str(self) -> None:
        """CALL_HIERARCHY_INCOMING_CALLS should be annotated as Final[str]."""
        assert LSPConstants.CALL_HIERARCHY_INCOMING_CALLS == "callHierarchy/incomingCalls"
        hints = get_type_hints(LSPConstants)
        assert "CALL_HIERARCHY_INCOMING_CALLS" in hints
        origin = typing.get_origin(hints["CALL_HIERARCHY_INCOMING_CALLS"])
        assert origin is typing.Final or str(hints["CALL_HIERARCHY_INCOMING_CALLS"]).startswith("typing.Final")

    def test_call_hierarchy_outgoing_calls_is_final_str(self) -> None:
        """CALL_HIERARCHY_OUTGOING_CALLS should be annotated as Final[str]."""
        assert LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS == "callHierarchy/outgoingCalls"
        hints = get_type_hints(LSPConstants)
        assert "CALL_HIERARCHY_OUTGOING_CALLS" in hints
        origin = typing.get_origin(hints["CALL_HIERARCHY_OUTGOING_CALLS"])
        assert origin is typing.Final or str(hints["CALL_HIERARCHY_OUTGOING_CALLS"]).startswith("typing.Final")

    def test_text_document_did_change_is_final_str(self) -> None:
        """TEXT_DOCUMENT_DID_CHANGE should be annotated as Final[str]."""
        assert LSPConstants.TEXT_DOCUMENT_DID_CHANGE == "textDocument/didChange"
        hints = get_type_hints(LSPConstants)
        assert "TEXT_DOCUMENT_DID_CHANGE" in hints
        origin = typing.get_origin(hints["TEXT_DOCUMENT_DID_CHANGE"])
        assert origin is typing.Final or str(hints["TEXT_DOCUMENT_DID_CHANGE"]).startswith("typing.Final")


class TestLSPConstantsNonMethodAttributes:
    """Test that non-method attributes remain int (not Final)."""

    def test_completion_trigger_kinds_are_int(self) -> None:
        """Completion trigger kinds should remain int (used for comparison, not overload matching)."""
        assert isinstance(LSPConstants.COMPLETION_TRIGGER_INVOKED, int)
        assert LSPConstants.COMPLETION_TRIGGER_INVOKED == 1

    def test_symbol_kinds_are_int(self) -> None:
        """Symbol kinds should remain int."""
        assert isinstance(LSPConstants.SYMBOL_KIND_CLASS, int)
        assert LSPConstants.SYMBOL_KIND_CLASS == 5

    def test_error_codes_are_int(self) -> None:
        """Error codes should remain int."""
        assert isinstance(LSPConstants.ERROR_PARSE_ERROR, int)
        assert LSPConstants.ERROR_PARSE_ERROR == -32700
