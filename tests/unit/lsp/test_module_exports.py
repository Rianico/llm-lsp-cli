"""Tests that StdioTransport is not publicly exported.

These tests verify that StdioTransport is NOT exported from lsp/__init__.py,
enforcing the boundary that clients must use TypedLSPTransport instead.
"""

import pytest


class TestModuleExports:
    """Tests that StdioTransport is not publicly exported."""

    def test_stdio_transport_not_in_all(self) -> None:
        """T4.1: StdioTransport not in lsp.__all__."""
        from llm_lsp_cli import lsp

        if hasattr(lsp, "__all__"):
            assert "StdioTransport" not in lsp.__all__, (
                "StdioTransport must not be in __all__ (boundary enforcement)"
            )

    def test_stdio_transport_not_importable_from_lsp(self) -> None:
        """T4.2: StdioTransport cannot be imported from lsp module."""
        from llm_lsp_cli import lsp

        assert not hasattr(lsp, "StdioTransport"), (
            "StdioTransport must not be accessible via lsp.StdioTransport"
        )

    def test_typed_lsp_transport_is_importable(self) -> None:
        """T4.3: TypedLSPTransport is the public interface."""
        from llm_lsp_cli.lsp.typed_transport import TypedLSPTransport

        assert TypedLSPTransport is not None, (
            "TypedLSPTransport must be importable from typed_transport"
        )
