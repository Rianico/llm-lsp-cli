"""Tests for import boundaries in the LSP module.

After the LSP client deepening refactor, LSPClient uses StdioTransport
directly. These tests verify the current import structure.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent


class TestImportBoundaries:
    """Tests for import structure in the LSP module."""

    def test_client_imports_stdio_transport(self) -> None:
        """LSPClient imports StdioTransport directly."""
        client_path = REPO_ROOT / "src/llm_lsp_cli/lsp/client.py"
        content = client_path.read_text()

        assert "from .transport import" in content and "StdioTransport" in content, (
            "LSPClient must import StdioTransport from transport"
        )

    def test_client_does_not_import_typed_transport(self) -> None:
        """LSPClient no longer imports TypedLSPTransport."""
        client_path = REPO_ROOT / "src/llm_lsp_cli/lsp/client.py"
        content = client_path.read_text()

        assert "TypedLSPTransport" not in content, (
            "LSPClient must not import TypedLSPTransport"
        )
