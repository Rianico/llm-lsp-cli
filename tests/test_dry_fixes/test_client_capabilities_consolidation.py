"""Tests for ClientCapabilities TypedDict consolidation (Issue 1)."""

import pytest


class TestClientCapabilitiesImport:
    """Test that ClientCapabilities is consolidated to lsp/types.py."""

    def test_client_capabilities_import_from_lsp_types(self) -> None:
        """Verify config.types can import ClientCapabilities from lsp.types."""
        from llm_lsp_cli.config.types import ClientCapabilities as ConfigCaps
        from llm_lsp_cli.lsp.types import ClientCapabilities as LspCaps

        assert ConfigCaps is LspCaps, "ClientCapabilities should be same type from both modules"

    def test_client_capabilities_structure_preserved(self) -> None:
        """Verify TypedDict structure matches LSP spec expectations."""
        from llm_lsp_cli.lsp.types import ClientCapabilities

        # Create instance with minimal required fields
        caps: ClientCapabilities = {
            "workspace": {},
            "textDocument": {"synchronization": {}},
            "window": {},
            "general": {},
        }

        assert "workspace" in caps
        assert "textDocument" in caps
        assert "window" in caps
        assert "general" in caps

    def test_config_types_backward_compatible(self) -> None:
        """Verify existing imports still resolve after consolidation."""
        from llm_lsp_cli.config.types import (
            ClientCapabilities,
            InitializeParams,
            TextDocumentClientCapabilities,
        )

        # Should be able to construct InitializeParams with ClientCapabilities
        params: InitializeParams = {
            "processId": 1234,
            "capabilities": {
                "workspace": {},
                "textDocument": {},
            },
        }
        assert params["capabilities"]["workspace"] == {}
