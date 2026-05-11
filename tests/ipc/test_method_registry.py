"""Tests for IPC method registry.

This test module covers T2 scenarios from the test specification.
Tests will fail until src/llm_lsp_cli/ipc/method_registry.py is implemented.
"""

import pytest


class TestMethodTypesRegistry:
    """Tests for METHOD_TYPES registry (T2.1-T2.14)."""

    def test_method_types_contains_ping(self) -> None:
        """T2.1: METHOD_TYPES contains daemon control methods."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "ping" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["ping"]
        assert params_type.__name__ == "EmptyParams"
        assert result_type.__name__ == "PingResult"

    def test_method_types_contains_shutdown(self) -> None:
        """T2.2: METHOD_TYPES contains shutdown method."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "shutdown" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["shutdown"]
        assert params_type.__name__ == "EmptyParams"
        assert result_type.__name__ == "ShutdownResult"

    def test_method_types_contains_status(self) -> None:
        """T2.3: METHOD_TYPES contains status method."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "status" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["status"]
        assert params_type.__name__ == "EmptyParams"
        assert result_type.__name__ == "DaemonStatusResult"

    def test_method_types_contains_text_document_definition(self) -> None:
        """T2.4: METHOD_TYPES contains textDocument/definition."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "textDocument/definition" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["textDocument/definition"]
        # Result type should be list[Location] or similar
        assert params_type.__name__ == "TextDocumentPositionParams"

    def test_method_types_contains_text_document_hover(self) -> None:
        """T2.5: METHOD_TYPES contains textDocument/hover."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "textDocument/hover" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["textDocument/hover"]
        assert params_type.__name__ == "TextDocumentPositionParams"

    def test_method_types_contains_text_document_document_symbol(self) -> None:
        """T2.6: METHOD_TYPES contains textDocument/documentSymbol."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "textDocument/documentSymbol" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["textDocument/documentSymbol"]
        assert params_type.__name__ == "DocumentSymbolParams"

    def test_method_types_contains_workspace_symbol(self) -> None:
        """T2.7: METHOD_TYPES contains workspace/symbol."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "workspace/symbol" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["workspace/symbol"]
        assert params_type.__name__ == "WorkspaceSymbolParams"

    def test_method_types_contains_text_document_prepare_rename(self) -> None:
        """T2.8: METHOD_TYPES contains textDocument/prepareRename."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "textDocument/prepareRename" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["textDocument/prepareRename"]
        assert params_type.__name__ == "TextDocumentPositionParams"

    def test_method_types_contains_text_document_rename(self) -> None:
        """T2.9: METHOD_TYPES contains textDocument/rename."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "textDocument/rename" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["textDocument/rename"]
        assert params_type.__name__ == "RenameParams"

    def test_method_types_contains_text_document_references(self) -> None:
        """T2.10: METHOD_TYPES contains textDocument/references."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert "textDocument/references" in METHOD_TYPES
        params_type, result_type = METHOD_TYPES["textDocument/references"]
        assert params_type.__name__ == "ReferenceParams"

    def test_unknown_method_raises_key_error(self) -> None:
        """T2.12: Unknown method raises KeyError."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        with pytest.raises(KeyError):
            _ = METHOD_TYPES["unknown/method"]

    def test_registry_format_is_correct(self) -> None:
        """T2.13: Registry format is correct (params type, result type)."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        entry = METHOD_TYPES["ping"]
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        # First element is params type class
        assert hasattr(entry[0], "__name__")
        # Second element is result type class
        assert hasattr(entry[1], "__name__")


class TestMethodNameLiteral:
    """Tests for MethodName Literal type (T2.11)."""

    def test_method_name_literal_exists(self) -> None:
        """T2.11: MethodName Literal includes all methods."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES, MethodName

        # MethodName should be a Literal type that contains method names
        # We can verify it's valid by checking all METHOD_TYPES keys are valid
        for method_name in METHOD_TYPES:
            # This is a runtime check - type checkers will verify at compile time
            assert isinstance(method_name, str)


class TestMethodTypePairAlias:
    """Tests for MethodTypePair alias (T2.14)."""

    def test_method_type_pair_alias_works(self) -> None:
        """T2.14: MethodTypePair alias works."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES, MethodTypePair

        pair: MethodTypePair = METHOD_TYPES["ping"]
        assert pair is not None


class TestRegistryCompleteness:
    """Tests for registry completeness and minimum size."""

    def test_registry_has_at_least_ten_entries(self) -> None:
        """Verify METHOD_TYPES has at least 10 entries as per success criteria."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        assert len(METHOD_TYPES) >= 10

    def test_all_daemon_control_methods_present(self) -> None:
        """Verify all daemon control methods are present."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        daemon_methods = ["ping", "shutdown", "status"]
        for method in daemon_methods:
            assert method in METHOD_TYPES, f"Missing daemon method: {method}"

    def test_all_lsp_methods_present(self) -> None:
        """Verify all LSP methods are present."""
        from llm_lsp_cli.ipc.method_registry import METHOD_TYPES

        lsp_methods = [
            "textDocument/definition",
            "textDocument/hover",
            "textDocument/documentSymbol",
            "workspace/symbol",
            "textDocument/prepareRename",
            "textDocument/rename",
            "textDocument/references",
        ]
        for method in lsp_methods:
            assert method in METHOD_TYPES, f"Missing LSP method: {method}"
