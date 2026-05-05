"""Tests that only TypedLSPTransport can import StdioTransport.

These tests verify the import boundary: only typed_transport.py should
import StdioTransport, enforcing the type safety gateway pattern.
"""

import subprocess
from pathlib import Path

import pytest

# Repository root (4 levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent.parent


class TestImportBoundaries:
    """Tests that only TypedLSPTransport can import StdioTransport."""

    def test_only_typed_transport_imports_stdio(self) -> None:
        """T5.1: Only typed_transport.py imports StdioTransport."""
        # Use grep to find all imports of StdioTransport
        result = subprocess.run(
            [
                "rg", "-n",
                r"from\s+.*transport.*import.*StdioTransport|StdioTransport\s*=\s*",
                "src/llm_lsp_cli/",
                "--include-glob", "*.py",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )

        lines = result.stdout.strip().split("\n") if result.stdout else []
        # Filter out typed_transport.py and transport.py (its own definition)
        violations = [
            line for line in lines
            if line and "typed_transport.py" not in line and "transport.py:" not in line
        ]

        assert len(violations) == 0, (
            f"StdioTransport imported outside typed_transport.py: {violations}"
        )

    def test_client_does_not_import_stdio_transport(self) -> None:
        """T5.2: LSPClient does not directly import StdioTransport."""
        client_path = REPO_ROOT / "src/llm_lsp_cli/lsp/client.py"
        content = client_path.read_text()

        # Check for direct import patterns
        direct_imports = [
            "from .transport import StdioTransport",
            "from .transport import LSPError, StdioTransport",
        ]

        for import_pattern in direct_imports:
            assert import_pattern not in content, (
                f"LSPClient must not directly import StdioTransport: {import_pattern}"
            )

    def test_client_uses_typed_transport(self) -> None:
        """T5.3: LSPClient should use TypedLSPTransport, not StdioTransport."""
        client_path = REPO_ROOT / "src/llm_lsp_cli/lsp/client.py"
        content = client_path.read_text()

        # Check that client imports TypedLSPTransport
        assert "TypedLSPTransport" in content, (
            "LSPClient must import and use TypedLSPTransport"
        )

        # Check that client stores a _typed_transport attribute
        assert "_typed_transport" in content or "typed_transport" in content, (
            "LSPClient must store a typed_transport reference"
        )
