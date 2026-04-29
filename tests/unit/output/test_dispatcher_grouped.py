"""Tests for dispatcher grouped output functionality.

This module tests the format_grouped method in OutputDispatcher for
handling grouped workspace output across different formats.
"""

from __future__ import annotations

import json

import pytest
import yaml

from llm_lsp_cli.utils import OutputFormat


class TestFormatGrouped:
    """Test format_grouped method for workspace output."""

    def test_json_format_grouped_symbols(self) -> None:
        """JSON format produces grouped array with _source and command."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function"},
                    {"name": "func2", "kind_name": "Function"},
                ]
            },
            {
                "file": "src/other.py",
                "symbols": [
                    {"name": "MyClass", "kind_name": "Class"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.JSON,
            items_key="symbols",
            _source="TestServer",
            command="workspace-symbol",
        )

        # Should be valid JSON dict with _source, command, files
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["_source"] == "TestServer"
        assert parsed["command"] == "workspace-symbol"
        assert len(parsed["files"]) == 2
        assert parsed["files"][0]["file"] == "src/main.py"
        assert len(parsed["files"][0]["symbols"]) == 2

    def test_json_format_grouped_diagnostics(self) -> None:
        """JSON format produces grouped array for diagnostics."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "src/main.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "Test error"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.JSON,
            items_key="diagnostics",
            _source="TestServer",
            command="workspace-diagnostics",
        )

        parsed = json.loads(result)
        assert parsed["_source"] == "TestServer"
        assert parsed["command"] == "workspace-diagnostics"
        assert len(parsed["files"]) == 1
        assert parsed["files"][0]["file"] == "src/main.py"
        assert "diagnostics" in parsed["files"][0]

    def test_yaml_format_grouped(self) -> None:
        """YAML format produces grouped structure."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.YAML,
            items_key="symbols",
            _source="TestServer",
            command="workspace-symbol",
        )

        parsed = yaml.safe_load(result)
        assert parsed["_source"] == "TestServer"
        assert parsed["command"] == "workspace-symbol"
        assert len(parsed["files"]) == 1
        assert parsed["files"][0]["file"] == "src/main.py"

    def test_csv_format_stays_flat(self) -> None:
        """CSV format produces flat table, not grouped."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function", "range": "1:1-5:1"},
                    {"name": "func2", "kind_name": "Function", "range": "6:1-10:1"},
                ]
            },
            {
                "file": "src/other.py",
                "symbols": [
                    {"name": "MyClass", "kind_name": "Class", "range": "1:1-20:1"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped_flat(
            grouped_data,
            OutputFormat.CSV,
            items_key="symbols",
            headers=["file", "name", "kind_name", "range"]
        )

        # CSV should be flat with file column
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 data rows
        assert "file" in lines[0]  # header has file column

    def test_csv_format_includes_all_items(self) -> None:
        """CSV includes all items from all groups."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "a.py",
                "symbols": [
                    {"name": "s1", "kind_name": "Function", "range": "1:1-5:1"},
                    {"name": "s2", "kind_name": "Function", "range": "6:1-10:1"},
                    {"name": "s3", "kind_name": "Function", "range": "11:1-15:1"},
                ]
            },
            {
                "file": "b.py",
                "symbols": [
                    {"name": "s4", "kind_name": "Class", "range": "1:1-20:1"},
                    {"name": "s5", "kind_name": "Class", "range": "21:1-40:1"},
                    {"name": "s6", "kind_name": "Class", "range": "41:1-60:1"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped_flat(
            grouped_data,
            OutputFormat.CSV,
            items_key="symbols",
            headers=["file", "name", "kind_name", "range"]
        )

        lines = result.strip().split("\n")
        assert len(lines) == 7  # header + 6 data rows

    def test_text_format_with_header(self) -> None:
        """TEXT format prepends header if provided."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function", "range": "1:1-5:1"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped_text(
            grouped_data,
            items_key="symbols",
            header="Basedpyright: workspace-symbol"
        )

        lines = result.split("\n")
        assert lines[0] == "Basedpyright: workspace-symbol"

    def test_text_format_without_header(self) -> None:
        """TEXT format works without header."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "src/main.py",
                "symbols": [
                    {"name": "func1", "kind_name": "Function", "range": "1:1-5:1"},
                ]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped_text(
            grouped_data,
            items_key="symbols",
            header=None
        )

        # Should start with file header, not alert header
        lines = result.split("\n")
        assert "Basedpyright" not in lines[0]

    def test_empty_grouped_data_json(self) -> None:
        """Empty grouped data produces empty files array in JSON."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            [], OutputFormat.JSON, items_key="symbols", _source="TestServer", command="workspace-symbol"
        )

        parsed = json.loads(result)
        assert parsed["_source"] == "TestServer"
        assert parsed["command"] == "workspace-symbol"
        assert parsed["files"] == []

    def test_empty_grouped_data_yaml(self) -> None:
        """Empty grouped data produces empty files array in YAML."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            [], OutputFormat.YAML, items_key="symbols", _source="TestServer", command="workspace-symbol"
        )

        parsed = yaml.safe_load(result)
        assert parsed["_source"] == "TestServer"
        assert parsed["command"] == "workspace-symbol"
        assert parsed["files"] == []

    def test_items_key_respected_symbols(self) -> None:
        """items_key='symbols' produces correct structure."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "test.py",
                "symbols": [{"name": "test"}]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data, OutputFormat.JSON, items_key="symbols", _source="TestServer", command="workspace-symbol"
        )

        parsed = json.loads(result)
        assert "symbols" in parsed["files"][0]
        assert "diagnostics" not in parsed["files"][0]

    def test_items_key_respected_diagnostics(self) -> None:
        """items_key='diagnostics' produces correct structure."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        grouped_data = [
            {
                "file": "test.py",
                "diagnostics": [{"message": "test"}]
            },
        ]

        dispatcher = OutputDispatcher()
        result = dispatcher.format_grouped(
            grouped_data, OutputFormat.JSON, items_key="diagnostics", _source="TestServer", command="workspace-diagnostics"
        )

        parsed = json.loads(result)
        assert "diagnostics" in parsed["files"][0]
        assert "symbols" not in parsed["files"][0]


class TestDispatcherGroupedMethods:
    """Test that dispatcher has required grouped methods."""

    def test_dispatcher_has_format_grouped_method(self) -> None:
        """OutputDispatcher has format_grouped method."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format_grouped")
        assert callable(getattr(OutputDispatcher, "format_grouped"))

    def test_dispatcher_has_format_grouped_text_method(self) -> None:
        """OutputDispatcher has format_grouped_text method."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format_grouped_text")
        assert callable(getattr(OutputDispatcher, "format_grouped_text"))

    def test_dispatcher_has_format_grouped_flat_method(self) -> None:
        """OutputDispatcher has format_grouped_flat method."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format_grouped_flat")
        assert callable(getattr(OutputDispatcher, "format_grouped_flat"))
