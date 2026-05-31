"""Tests for module exports in the LSP module.

StdioTransport is not publicly exported from lsp/__init__.py.
TypedLSPTransport no longer exists after the refactoring.
"""

import pytest


class TestModuleExports:
    """Tests for module exports."""

    def test_stdio_transport_not_in_all(self) -> None:
        """StdioTransport not in lsp.__all__."""
        from llm_lsp_cli import lsp

        if hasattr(lsp, "__all__"):
            assert "StdioTransport" not in lsp.__all__, (
                "StdioTransport must not be in __all__ (it's an implementation detail)"
            )

    def test_stdio_transport_not_importable_from_lsp(self) -> None:
        """StdioTransport cannot be imported from lsp module."""
        from llm_lsp_cli import lsp

        assert not hasattr(lsp, "StdioTransport"), (
            "StdioTransport must not be accessible via lsp.StdioTransport"
        )
