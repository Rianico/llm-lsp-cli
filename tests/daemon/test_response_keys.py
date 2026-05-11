"""Tests for RESPONSE_KEYS extraction (Step 3 of ADR-0028).

These tests verify that RESPONSE_KEYS is available as a module-level constant
in daemon.py, enabling import by commands/shared.py.
"""

import pytest

from llm_lsp_cli.lsp.constants import LSPConstants


class TestResponseKeysExtraction:
    """Test RESPONSE_KEYS module-level extraction."""

    def test_module_level_import(self) -> None:
        """RESPONSE_KEYS should be importable from daemon module."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS is not None
        assert isinstance(RESPONSE_KEYS, dict)

    def test_response_keys_is_dict_str_str(self) -> None:
        """RESPONSE_KEYS should be dict[str, str]."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        for key, value in RESPONSE_KEYS.items():
            assert isinstance(key, str), f"Key {key} is not str"
            assert isinstance(value, str), f"Value {value} is not str"


class TestResponseKeysBackwardCompatibility:
    """Test that RequestHandler.RESPONSE_KEYS still works."""

    def test_class_attribute_exists(self) -> None:
        """RequestHandler.RESPONSE_KEYS should still exist."""
        from llm_lsp_cli.daemon import RequestHandler

        assert hasattr(RequestHandler, "RESPONSE_KEYS")
        assert isinstance(RequestHandler.RESPONSE_KEYS, dict)

    def test_same_object_identity(self) -> None:
        """RequestHandler.RESPONSE_KEYS should reference module-level constant."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS, RequestHandler

        # Same object identity (not just equal values)
        assert RequestHandler.RESPONSE_KEYS is RESPONSE_KEYS


class TestResponseKeysCoverage:
    """Test that RESPONSE_KEYS covers all methods from the overload table."""

    def test_definition_key(self) -> None:
        """textDocument/definition -> locations."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.DEFINITION] == "locations"

    def test_hover_key(self) -> None:
        """textDocument/hover -> hover."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.HOVER] == "hover"

    def test_document_symbol_key(self) -> None:
        """textDocument/documentSymbol -> symbols."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.DOCUMENT_SYMBOL] == "symbols"

    def test_completion_key(self) -> None:
        """textDocument/completion -> items."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.COMPLETION] == "items"

    def test_references_key(self) -> None:
        """textDocument/references -> locations."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.REFERENCES] == "locations"

    def test_prepare_rename_key(self) -> None:
        """textDocument/prepareRename -> prepare_rename."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.PREPARE_RENAME] == "prepare_rename"

    def test_rename_key(self) -> None:
        """textDocument/rename -> workspace_edit."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.RENAME] == "workspace_edit"

    def test_workspace_symbol_key(self) -> None:
        """workspace/symbol -> symbols."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.WORKSPACE_SYMBOL] == "symbols"

    def test_diagnostic_key(self) -> None:
        """textDocument/diagnostic -> diagnostics."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.DIAGNOSTIC] == "diagnostics"

    def test_workspace_diagnostic_key(self) -> None:
        """workspace/diagnostic -> diagnostics."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.WORKSPACE_DIAGNOSTIC] == "diagnostics"

    def test_call_hierarchy_incoming_key(self) -> None:
        """callHierarchy/incomingCalls -> calls."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.CALL_HIERARCHY_INCOMING_CALLS] == "calls"

    def test_call_hierarchy_outgoing_key(self) -> None:
        """callHierarchy/outgoingCalls -> calls."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        assert RESPONSE_KEYS[LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS] == "calls"

    def test_did_change_key(self) -> None:
        """textDocument/didChange -> status (new entry)."""
        from llm_lsp_cli.daemon import RESPONSE_KEYS

        # This is a new entry for did-change
        assert LSPConstants.TEXT_DOCUMENT_DID_CHANGE in RESPONSE_KEYS
        assert RESPONSE_KEYS[LSPConstants.TEXT_DOCUMENT_DID_CHANGE] == "status"
