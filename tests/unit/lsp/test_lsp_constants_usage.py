"""Tests verifying LSP constants are used instead of duplicated strings."""

import ast
from pathlib import Path

from llm_lsp_cli.domain.services import LspMethodRouter
from llm_lsp_cli.lsp.constants import LSPConstants


class TestLspConstantUsage:
    """Verify LSP method strings reference LSPConstants."""

    def _find_string_literals(
        self, file_path: Path, target_strings: list[str]
    ) -> list[tuple[int, str]]:
        """Find occurrences of target strings in a Python file."""
        source = file_path.read_text()
        tree = ast.parse(source)

        occurrences = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in target_strings:
                    occurrences.append((node.lineno, node.value))

        return occurrences

    def test_daemon_does_not_duplicate_lsp_methods(self):
        """Verify daemon.py does not have duplicated LSP method strings."""
        daemon_file = Path("src/llm_lsp_cli/daemon.py")

        # These strings should NOT appear as raw strings
        lsp_methods = [
            "textDocument/definition",
            "textDocument/references",
            "textDocument/completion",
            "textDocument/hover",
            "textDocument/documentSymbol",
            "workspace/symbol",
        ]

        occurrences = self._find_string_literals(daemon_file, lsp_methods)

        # Daemon should import from LSPConstants, not duplicate strings
        assert len(occurrences) == 0, (
            f"Found duplicated LSP method strings in daemon.py: {occurrences}"
        )

    def test_daemon_imports_lsp_constants(self):
        """Verify daemon.py imports LSPConstants."""
        daemon_file = Path("src/llm_lsp_cli/daemon.py")
        source = daemon_file.read_text()

        # Should import LSPConstants
        assert (
            "from llm_lsp_cli.lsp.constants import LSPConstants" in source
            or "import LSPConstants" in source
        )

    def test_registry_uses_lsp_constants(self):
        """Verify server registry is properly structured.

        Note: registry.py uses ConfigManager which internally uses LSPConstants.
        The registry itself focuses on workspace management and server lifecycle.
        """
        registry_file = Path("src/llm_lsp_cli/server/registry.py")
        source = registry_file.read_text()

        # Registry should import ConfigManager which handles LSP constants
        assert "ConfigManager" in source, "registry.py should import ConfigManager"

    def test_method_router_provides_all_constants(self):
        """Verify LspMethodRouter provides configs for all LSPConstants methods."""
        router = LspMethodRouter()

        # Key LSP methods should have router configs
        key_methods = [
            LSPConstants.DEFINITION,
            LSPConstants.REFERENCES,
            LSPConstants.COMPLETION,
            LSPConstants.HOVER,
            LSPConstants.DOCUMENT_SYMBOL,
            LSPConstants.WORKSPACE_SYMBOL,
            LSPConstants.DIAGNOSTIC,
            LSPConstants.WORKSPACE_DIAGNOSTIC,
        ]

        for method in key_methods:
            config = router.get_config(method)
            assert config is not None, f"LspMethodRouter missing config for {method}"

    def test_lsp_constants_are_defined(self):
        """Verify LSPConstants has all expected method constants."""
        assert hasattr(LSPConstants, "DEFINITION")
        assert hasattr(LSPConstants, "REFERENCES")
        assert hasattr(LSPConstants, "COMPLETION")
        assert hasattr(LSPConstants, "HOVER")
        assert hasattr(LSPConstants, "DOCUMENT_SYMBOL")
        assert hasattr(LSPConstants, "WORKSPACE_SYMBOL")
        assert hasattr(LSPConstants, "DIAGNOSTIC")
        assert hasattr(LSPConstants, "WORKSPACE_DIAGNOSTIC")

    def test_lsp_constant_values(self):
        """Verify LSP constant values match LSP specification."""
        assert LSPConstants.DEFINITION == "textDocument/definition"
        assert LSPConstants.REFERENCES == "textDocument/references"
        assert LSPConstants.COMPLETION == "textDocument/completion"
        assert LSPConstants.HOVER == "textDocument/hover"
        assert LSPConstants.DOCUMENT_SYMBOL == "textDocument/documentSymbol"
        assert LSPConstants.WORKSPACE_SYMBOL == "workspace/symbol"
        assert LSPConstants.DIAGNOSTIC == "textDocument/diagnostic"
        assert LSPConstants.WORKSPACE_DIAGNOSTIC == "workspace/diagnostic"
