"""Tests for file-level command headers in TEXT output.

This module tests that alert headers appear correctly in TEXT output
for file-level LSP commands (diagnostics, document-symbol, definition, etc.).
"""

from __future__ import annotations

import pytest


class TestFileLevelCommandHeaders:
    """Test alert headers appear in TEXT output for file-level commands."""

    def test_diagnostics_shows_header_in_text(self) -> None:
        """diagnostics command shows '<Server>: diagnostics of <file>' in TEXT."""
        # This test will verify the header appears in TEXT output
        # The header should be: "Basedpyright: diagnostics of src/main.py"
        from llm_lsp_cli.commands.lsp import diagnostics
        # Implementation will be checked in GREEN phase
        # For now, this test will fail because the feature doesn't exist
        pytest.skip("RED phase - feature not implemented")

    def test_document_symbol_shows_header_in_text(self) -> None:
        """document-symbol command shows header in TEXT."""
        # Header should be: "Basedpyright: document-symbol of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_definition_shows_header_in_text(self) -> None:
        """definition command shows header in TEXT."""
        # Header should be: "Basedpyright: definition of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_references_shows_header_in_text(self) -> None:
        """references command shows header in TEXT."""
        # Header should be: "Basedpyright: references of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_completion_shows_header_in_text(self) -> None:
        """completion command shows header in TEXT."""
        # Header should be: "Basedpyright: completion of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_hover_shows_header_in_text(self) -> None:
        """hover command shows header in TEXT."""
        # Header should be: "Basedpyright: hover of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_incoming_calls_shows_header_in_text(self) -> None:
        """incoming-calls command shows header in TEXT."""
        # Header should be: "Basedpyright: incoming-calls of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_outgoing_calls_shows_header_in_text(self) -> None:
        """outgoing-calls command shows header in TEXT."""
        # Header should be: "Basedpyright: outgoing-calls of src/main.py"
        pytest.skip("RED phase - feature not implemented")

    def test_json_format_no_header(self) -> None:
        """JSON output does NOT include header (must be parseable)."""
        # JSON output should be valid JSON array, no header string
        pytest.skip("RED phase - feature not implemented")

    def test_yaml_format_no_header(self) -> None:
        """YAML output does NOT include header."""
        # YAML output should be valid YAML, no header
        pytest.skip("RED phase - feature not implemented")

    def test_csv_format_no_header(self) -> None:
        """CSV output does NOT include alert header."""
        # CSV should have column headers only, no alert header
        pytest.skip("RED phase - feature not implemented")


class TestHeaderBuilderIntegration:
    """Test header builder integration with commands."""

    def test_header_builder_module_exists(self) -> None:
        """header_builder module can be imported."""
        from llm_lsp_cli.output import header_builder  # noqa: F401

    def test_build_alert_header_function_exists(self) -> None:
        """build_alert_header function exists."""
        from llm_lsp_cli.output.header_builder import build_alert_header

        assert callable(build_alert_header)

    def test_command_info_dataclass_exists(self) -> None:
        """CommandInfo dataclass exists."""
        from llm_lsp_cli.output.header_builder import CommandInfo

        assert CommandInfo is not None
