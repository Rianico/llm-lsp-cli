"""Tests for text renderer grouped output.

This module tests the render_workspace_symbols_grouped and
render_workspace_diagnostics_grouped functions in output/text_renderer.py
for hierarchical TEXT output with file grouping.
"""

from __future__ import annotations

import pytest


class TestRenderWorkspaceSymbolsGrouped:
    """Test hierarchical TEXT output for grouped symbols."""

    def test_renders_header_first_line(self) -> None:
        """Header appears on first line."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function", "range": "1:1-5:1"},
                ]
            },
        ]

        result = render_workspace_symbols_grouped(grouped_data, header="Basedpyright: workspace-symbol")

        lines = result.split("\n")
        assert lines[0] == "Basedpyright: workspace-symbol"

    def test_renders_file_headers(self) -> None:
        """Each file group has file path header."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function", "range": "1:1-5:1"},
                ]
            },
            {
                "file": "src/other.py",
                "symbols": [
                    {"name": "MyClass", "kind_name": "Class", "range": "1:1-20:1"},
                ]
            },
        ]

        result = render_workspace_symbols_grouped(grouped_data, header="Server: command")

        assert "src/main.py:" in result
        assert "src/other.py:" in result

    def test_renders_tree_connectors(self) -> None:
        """Symbols use tree connectors (├──, └──)."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function", "range": "1:1-5:1"},
                    {"name": "func2", "kind_name": "Function", "range": "6:1-10:1"},
                ]
            },
        ]

        result = render_workspace_symbols_grouped(grouped_data, header="Server: command")

        # First symbol should use ├──
        assert "├── func1" in result
        # Last symbol should use └──
        assert "└── func2" in result

    def test_renders_symbol_details(self) -> None:
        """Symbol line includes name, kind, range."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "test.py",
                "symbols": [
                    {"name": "myFunc", "kind_name": "Function", "range": "5:1-10:1"},
                ]
            },
        ]

        result = render_workspace_symbols_grouped(grouped_data, header="Server: command")

        assert "myFunc" in result
        assert "Function" in result
        assert "5:1-10:1" in result

    def test_empty_groups_returns_no_symbols_message(self) -> None:
        """Empty grouped data produces 'No symbols found.'"""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        result = render_workspace_symbols_grouped([], header="Server: command")

        assert result == "No symbols found."

    def test_single_symbol_per_file(self) -> None:
        """Single symbol uses └── connector."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "test.py",
                "symbols": [
                    {"name": "onlyFunc", "kind_name": "Function", "range": "1:1-5:1"},
                ]
            },
        ]

        result = render_workspace_symbols_grouped(grouped_data, header="Server: command")

        # Single symbol should use └──
        assert "└── onlyFunc" in result
        assert "├── onlyFunc" not in result

    def test_multiple_files_rendered(self) -> None:
        """Multiple files all rendered with headers."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "a.py",
                "symbols": [{"name": "a_func", "kind_name": "Function", "range": "1:1-5:1"}]
            },
            {
                "file": "b.py",
                "symbols": [{"name": "b_func", "kind_name": "Function", "range": "1:1-5:1"}]
            },
            {
                "file": "c.py",
                "symbols": [{"name": "c_func", "kind_name": "Function", "range": "1:1-5:1"}]
            },
        ]

        result = render_workspace_symbols_grouped(grouped_data, header="Server: command")

        assert "a.py:" in result
        assert "b.py:" in result
        assert "c.py:" in result


class TestRenderWorkspaceDiagnosticsGrouped:
    """Test hierarchical TEXT output for grouped diagnostics."""

    def test_renders_header_first_line(self) -> None:
        """Header appears on first line."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "src/main.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "Test error", "range": "1:1-1:10"},
                ]
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data, header="Basedpyright: workspace-diagnostics")

        lines = result.split("\n")
        assert lines[0] == "Basedpyright: workspace-diagnostics"

    def test_renders_file_headers(self) -> None:
        """Each file group has file path header."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "src/main.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "Error 1", "range": "1:1-1:10"},
                ]
            },
            {
                "file": "src/other.py",
                "diagnostics": [
                    {"severity_name": "Warning", "message": "Warning 1", "range": "5:1-5:5"},
                ]
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data, header="Server: command")

        assert "src/main.py:" in result
        assert "src/other.py:" in result

    def test_renders_diagnostic_severity_and_message(self) -> None:
        """Diagnostic line includes severity and message."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "test.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "Undefined variable", "range": "10:5-10:15"},
                ]
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data, header="Server: command")

        assert "Error" in result
        assert "Undefined variable" in result

    def test_renders_diagnostic_with_code(self) -> None:
        """Diagnostic line includes code if present."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "test.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "Type error", "code": "E001", "range": "5:1-5:10"},
                ]
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data, header="Server: command")

        assert "E001" in result

    def test_renders_diagnostic_without_code(self) -> None:
        """Diagnostic line works without code."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "test.py",
                "diagnostics": [
                    {"severity_name": "Warning", "message": "Unused import", "range": "1:1-1:10"},
                ]
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data, header="Server: command")

        assert "Warning" in result
        assert "Unused import" in result

    def test_empty_groups_returns_no_diagnostics_message(self) -> None:
        """Empty grouped data produces 'No diagnostics found.'"""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        result = render_workspace_diagnostics_grouped([], header="Server: command")

        assert result == "No diagnostics found."

    def test_tree_connectors_for_diagnostics(self) -> None:
        """Diagnostics use tree connectors like symbols."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "test.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "Error 1", "range": "1:1-1:5"},
                    {"severity_name": "Warning", "message": "Warning 1", "range": "5:1-5:5"},
                ]
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data, header="Server: command")

        assert "├──" in result
        assert "└──" in result
