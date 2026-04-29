"""Integration tests for definition, completion, and hover commands with compact range format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import CompactFormatter, HoverRecord
from llm_lsp_cli.utils import OutputFormat

runner = CliRunner()


class TestDefinitionCommandWorkflow:
    """Integration tests for definition command with compact range format."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        (temp_dir / "src").mkdir()
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def definition_response(self, temp_dir: Path) -> dict[str, Any]:
        """Simulate a textDocument/definition LSP response."""
        return {
            "locations": [
                {
                    "uri": f"file://{temp_dir}/src/main.py",
                    "range": {
                        "start": {"line": 10, "character": 4},
                        "end": {"line": 10, "character": 15},
                    },
                },
                {
                    "uri": f"file://{temp_dir}/src/utils.py",
                    "range": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 5, "character": 20},
                    },
                },
            ]
        }

    def test_workflow_text_output(
        self, formatter: CompactFormatter, definition_response: dict[str, Any]
    ) -> None:
        """Test definition text output with compact range."""
        locations = definition_response["locations"]
        records = formatter.transform_locations(locations)
        output = OutputDispatcher().format_list(records, OutputFormat.TEXT)

        # Compact format: "file: line:char-line:char"
        lines = output.strip().split("\n")
        assert len(lines) == 2
        assert "src/main.py: 11:5-11:16" in output
        assert "src/utils.py: 6:1-6:21" in output

    def test_workflow_json_output(
        self, formatter: CompactFormatter, definition_response: dict[str, Any]
    ) -> None:
        """Test definition JSON output with compact range."""
        locations = definition_response["locations"]
        records = formatter.transform_locations(locations)
        output = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(output)

        items = parsed["items"]
        assert len(items) == 2
        assert items[0]["file"] == "src/main.py"
        assert items[0]["range"] == "11:5-11:16"
        assert items[1]["file"] == "src/utils.py"
        assert items[1]["range"] == "6:1-6:21"

    def test_workflow_yaml_output(
        self, formatter: CompactFormatter, definition_response: dict[str, Any]
    ) -> None:
        """Test definition YAML output with compact range."""
        locations = definition_response["locations"]
        records = formatter.transform_locations(locations)
        output = OutputDispatcher().format_list(records, OutputFormat.YAML)
        parsed = yaml.safe_load(output)

        items = parsed["items"]
        assert len(items) == 2
        assert items[0]["file"] == "src/main.py"
        assert items[0]["range"] == "11:5-11:16"

    def test_workflow_csv_output(
        self, formatter: CompactFormatter, definition_response: dict[str, Any]
    ) -> None:
        """Test definition CSV output with compact range."""
        locations = definition_response["locations"]
        records = formatter.transform_locations(locations)
        output = OutputDispatcher().format_list(records, OutputFormat.CSV)
        lines = output.strip().split("\n")

        # Header + 2 data rows
        assert len(lines) == 3
        # Header should be: file,range (NOT uri,start_line,start_char,end_line,end_char)
        assert lines[0] == "file,range"
        # Data rows should have compact range
        assert "src/main.py,11:5-11:16" in lines[1]
        assert "src/utils.py,6:1-6:21" in lines[2]


class TestCompletionCommandWorkflow:
    """Integration tests for completion command with compact range format."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def completion_response(self) -> dict[str, Any]:
        """Simulate a textDocument/completion LSP response."""
        return {
            "items": [
                {
                    "label": "my_function",
                    "kind": 12,  # Function
                    "detail": "def my_function(x: int) -> str",
                    "documentation": "A sample function.",
                    "textEdit": {
                        "range": {
                            "start": {"line": 5, "character": 0},
                            "end": {"line": 5, "character": 10},
                        },
                        "newText": "my_function",
                    },
                    "data": {
                        "position": {"line": 5, "character": 5},
                    },
                },
                {
                    "label": "MyClass",
                    "kind": 5,  # Class
                    "detail": "class MyClass",
                    "textEdit": {
                        "range": {
                            "start": {"line": 10, "character": 4},
                            "end": {"line": 10, "character": 12},
                        },
                        "newText": "MyClass",
                    },
                },
            ]
        }

    def test_workflow_text_output(
        self, formatter: CompactFormatter, completion_response: dict[str, Any]
    ) -> None:
        """Test completion text output with compact range."""
        items = completion_response["items"]
        records = formatter.transform_completions(items, file_path="src/main.py")
        output = OutputDispatcher().format_list(records, OutputFormat.TEXT)

        # Format: "file: label - detail [range]"
        assert "src/main.py: my_function - def my_function(x: int) -> str [6:1-6:11]" in output
        assert "src/main.py: MyClass - class MyClass [11:5-11:13]" in output

    def test_workflow_json_output(
        self, formatter: CompactFormatter, completion_response: dict[str, Any]
    ) -> None:
        """Test completion JSON output with compact range."""
        items = completion_response["items"]
        records = formatter.transform_completions(items, file_path="src/main.py")
        output = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(output)

        result_items = parsed["items"]
        assert len(result_items) == 2

        # First completion
        assert result_items[0]["file"] == "src/main.py"
        assert result_items[0]["label"] == "my_function"
        assert result_items[0]["kind_name"] == "Function"
        assert result_items[0]["detail"] == "def my_function(x: int) -> str"
        assert result_items[0]["documentation"] == "A sample function."
        assert result_items[0]["range"] == "6:1-6:11"
        assert result_items[0]["position"] == "6:6-6:6"  # Single point as range

        # Second completion
        assert result_items[1]["label"] == "MyClass"
        assert result_items[1]["kind_name"] == "Class"
        assert result_items[1]["range"] == "11:5-11:13"
        assert "position" not in result_items[1]  # No position field

    def test_workflow_yaml_output(
        self, formatter: CompactFormatter, completion_response: dict[str, Any]
    ) -> None:
        """Test completion YAML output with compact range."""
        items = completion_response["items"]
        records = formatter.transform_completions(items, file_path="src/main.py")
        output = OutputDispatcher().format_list(records, OutputFormat.YAML)
        parsed = yaml.safe_load(output)

        result_items = parsed["items"]
        assert len(result_items) == 2
        assert result_items[0]["range"] == "6:1-6:11"

    def test_workflow_csv_output(
        self, formatter: CompactFormatter, completion_response: dict[str, Any]
    ) -> None:
        """Test completion CSV output with compact range."""
        items = completion_response["items"]
        records = formatter.transform_completions(items, file_path="src/main.py")
        output = OutputDispatcher().format_list(records, OutputFormat.CSV)
        lines = output.strip().split("\n")

        # Header + 2 data rows
        assert len(lines) == 3
        # Header should include file, label, kind_name, detail, documentation, range, position
        header = lines[0]
        assert "file" in header
        assert "label" in header
        assert "kind_name" in header
        assert "range" in header


class TestHoverCommandWorkflow:
    """Integration tests for hover command with compact range format."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def hover_response_with_range(self) -> dict[str, Any]:
        """Simulate a textDocument/hover LSP response with range."""
        return {
            "hover": {
                "contents": {
                    "kind": "markdown",
                    "value": "```python\ndef my_function(x: int) -> str\n```",
                },
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 15},
                },
            }
        }

    @pytest.fixture
    def hover_response_no_range(self) -> dict[str, Any]:
        """Simulate a textDocument/hover LSP response without range."""
        return {
            "hover": {
                "contents": {
                    "kind": "plaintext",
                    "value": "Some documentation",
                },
            }
        }

    @pytest.fixture
    def hover_response_none(self) -> dict[str, Any]:
        """Simulate a textDocument/hover LSP response with None hover."""
        return {"hover": None}

    def test_workflow_text_output_with_range(
        self, formatter: CompactFormatter, hover_response_with_range: dict[str, Any]
    ) -> None:
        """Test hover text output with compact range."""
        hover = hover_response_with_range["hover"]
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        output = OutputDispatcher().format(record, OutputFormat.TEXT)

        # Format: "file: content [range]"
        assert "src/main.py:" in output
        assert "def my_function" in output
        assert "[11:5-11:16]" in output

    def test_workflow_json_output_with_range(
        self, formatter: CompactFormatter, hover_response_with_range: dict[str, Any]
    ) -> None:
        """Test hover JSON output with compact range."""
        hover = hover_response_with_range["hover"]
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        output = OutputDispatcher().format(record, OutputFormat.JSON)
        parsed = json.loads(output)

        assert parsed["file"] == "src/main.py"
        assert "def my_function" in parsed["content"]
        assert parsed["range"] == "11:5-11:16"

    def test_workflow_yaml_output_with_range(
        self, formatter: CompactFormatter, hover_response_with_range: dict[str, Any]
    ) -> None:
        """Test hover YAML output with compact range."""
        hover = hover_response_with_range["hover"]
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        output = OutputDispatcher().format(record, OutputFormat.YAML)
        parsed = yaml.safe_load(output)

        assert parsed["file"] == "src/main.py"
        assert parsed["range"] == "11:5-11:16"

    def test_workflow_csv_output_with_range(
        self, formatter: CompactFormatter, hover_response_with_range: dict[str, Any]
    ) -> None:
        """Test hover CSV output with compact range."""
        hover = hover_response_with_range["hover"]
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        output = OutputDispatcher().format(record, OutputFormat.CSV)

        # Header should be: file,content,range
        assert output.startswith("file,content,range\n")
        # Content contains newlines, so CSV will have multiple lines
        # Verify the key elements are present
        assert "src/main.py" in output
        assert "11:5-11:16" in output
        assert "def my_function" in output

    def test_workflow_json_without_range(
        self, formatter: CompactFormatter, hover_response_no_range: dict[str, Any]
    ) -> None:
        """Test hover JSON output without range."""
        hover = hover_response_no_range["hover"]
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        output = OutputDispatcher().format(record, OutputFormat.JSON)
        parsed = json.loads(output)

        assert parsed["file"] == "src/main.py"
        assert parsed["content"] == "Some documentation"
        assert "range" not in parsed  # Should be omitted

    def test_workflow_none_hover(
        self, formatter: CompactFormatter, hover_response_none: dict[str, Any]
    ) -> None:
        """Test hover with None response."""
        hover = hover_response_none["hover"]
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is None


class TestCompactRangeFormatConsistency:
    """Tests to verify compact range format is consistent across all commands."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        return CompactFormatter(temp_dir)

    def test_range_is_one_based(self, formatter: CompactFormatter) -> None:
        """Verify range format is 1-based (LSP is 0-based)."""
        # LSP line=0, char=0 should become compact "1:1"
        items = [
            {
                "label": "test",
                "kind": 12,
                "textEdit": {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    }
                },
            }
        ]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].range is not None
        assert records[0].range.to_compact() == "1:1-1:11"

    def test_range_uses_colon_separator(self, formatter: CompactFormatter) -> None:
        """Verify range format uses colon separator: line:char-line:char."""
        items = [
            {
                "label": "test",
                "kind": 12,
                "textEdit": {
                    "range": {
                        "start": {"line": 10, "character": 5},
                        "end": {"line": 10, "character": 15},
                    }
                },
            }
        ]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].range is not None
        # 0-based (10,5)-(10,15) -> 1-based "11:6-11:16"
        assert records[0].range.to_compact() == "11:6-11:16"

    def test_multi_line_range_format(self, formatter: CompactFormatter) -> None:
        """Verify multi-line ranges are formatted correctly."""
        items = [
            {
                "label": "test",
                "kind": 12,
                "textEdit": {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 5, "character": 10},
                    }
                },
            }
        ]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].range is not None
        assert records[0].range.to_compact() == "1:1-6:11"

    def test_json_omits_none_fields(self, formatter: CompactFormatter) -> None:
        """Verify JSON output omits None fields."""
        items = [
            {
                "label": "test",
                "kind": 12,
                # No detail, documentation, textEdit, or data
            }
        ]
        records = formatter.transform_completions(items, file_path="test.py")
        output = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(output)

        result_items = parsed["items"]

        # Required fields should be present
        assert "file" in result_items[0]
        assert "label" in result_items[0]
        assert "kind_name" in result_items[0]

        # Optional None fields should be omitted
        assert "detail" not in result_items[0]
        assert "documentation" not in result_items[0]
        assert "range" not in result_items[0]
        assert "position" not in result_items[0]

    def test_csv_uses_empty_string_for_none(self, formatter: CompactFormatter) -> None:
        """Verify CSV uses empty string for None fields."""
        items = [
            {
                "label": "test",
                "kind": 12,
                # No detail, documentation, textEdit, or data
            }
        ]
        records = formatter.transform_completions(items, file_path="test.py")
        output = OutputDispatcher().format_list(records, OutputFormat.CSV)
        lines = output.strip().split("\n")

        # Should have header and one data row
        assert len(lines) == 2

        # Data row should have empty strings for None fields
        data_line = lines[1]
        # Count commas to verify structure
        assert data_line.count(",") == 6  # 7 columns, 6 commas
