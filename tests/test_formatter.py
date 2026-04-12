"""Unit tests for CSV output formatting."""

import csv
import io
from typing import Any

from llm_lsp_cli.utils.formatter import (
    OutputFormat,
    format_completions_csv,
    format_document_symbols_csv,
    format_hover_csv,
    format_locations_csv,
    format_workspace_symbols_csv,
)


class TestCsvFormattingLocations:
    """Unit tests for CSV formatting of location lists (definition/references)."""

    def test_csv_format_locations_simple(self) -> None:
        """Test CSV formatting for location list with simple data."""
        locations = [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 20},
                },
            },
        ]

        result = format_locations_csv(locations)

        # Parse CSV to verify structure
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["uri"] == "file:///path/to/file.py"
        assert rows[0]["start_line"] == "10"
        assert rows[0]["start_char"] == "4"
        assert rows[0]["end_line"] == "10"
        assert rows[0]["end_char"] == "20"

    def test_csv_format_locations_multiple(self) -> None:
        """Test CSV formatting for multiple locations."""
        locations = [
            {
                "uri": "file:///path/to/file1.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            },
            {
                "uri": "file:///path/to/file2.py",
                "range": {
                    "start": {"line": 20, "character": 5},
                    "end": {"line": 20, "character": 25},
                },
            },
        ]

        result = format_locations_csv(locations)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["uri"] == "file:///path/to/file1.py"
        assert rows[1]["uri"] == "file:///path/to/file2.py"

    def test_csv_format_locations_empty(self) -> None:
        """Test CSV formatting returns empty string for no results."""
        locations: list[dict[str, Any]] = []
        result = format_locations_csv(locations)

        assert result == ""

    def test_csv_header_row_present(self) -> None:
        """Test that CSV output includes header row."""
        locations = [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            },
        ]

        result = format_locations_csv(locations)
        lines = result.strip().split("\n")

        assert len(lines) >= 1
        # Header should contain expected columns
        header = lines[0]
        assert "uri" in header
        assert "start_line" in header
        assert "start_char" in header
        assert "end_line" in header
        assert "end_char" in header

    def test_csv_field_order_matches_spec(self) -> None:
        """Test that CSV columns are in documented order."""
        locations = [
            {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            },
        ]

        result = format_locations_csv(locations)
        lines = result.strip().split("\n")
        header = lines[0]

        # Expected order: uri,start_line,start_char,end_line,end_char
        assert header == "uri,start_line,start_char,end_line,end_char"


class TestCsvFormattingCompletions:
    """Unit tests for CSV formatting of completion items."""

    def test_csv_format_completions_simple(self) -> None:
        """Test CSV formatting for completion items with basic data."""
        items = [
            {
                "label": "my_function",
                "kind": 12,
                "detail": "def my_function(x: int) -> str",
                "documentation": "A sample function.",
            },
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["label"] == "my_function"
        assert rows[0]["kind"] == "12"
        assert rows[0]["kind_name"] == "Function"
        assert rows[0]["detail"] == "def my_function(x: int) -> str"
        assert rows[0]["documentation"] == "A sample function."

    def test_csv_format_completions_includes_kind_name(self) -> None:
        """Test CSV output translates kind number to human-readable name."""
        items = [
            {"label": "MyClass", "kind": 5, "detail": "", "documentation": None},
            {"label": "my_func", "kind": 12, "detail": "", "documentation": None},
            {"label": "my_var", "kind": 13, "detail": "", "documentation": None},
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert rows[0]["kind_name"] == "Class"
        assert rows[1]["kind_name"] == "Function"
        assert rows[2]["kind_name"] == "Variable"

    def test_csv_format_completions_empty(self) -> None:
        """Test CSV formatting returns empty string for no results."""
        items: list[dict[str, Any]] = []
        result = format_completions_csv(items)

        assert result == ""

    def test_csv_format_completions_missing_fields(self) -> None:
        """Test CSV handles missing optional fields gracefully."""
        items = [
            {"label": "simple_item", "kind": 1},
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["label"] == "simple_item"
        # Missing fields should be empty strings
        assert rows[0]["detail"] == ""
        assert rows[0]["documentation"] == ""


class TestCsvFormattingSymbols:
    """Unit tests for CSV formatting of symbol lists."""

    def test_csv_format_document_symbols_simple(self) -> None:
        """Test CSV formatting for document symbols."""
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
            },
        ]

        result = format_document_symbols_csv(symbols)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["name"] == "MyClass"
        assert rows[0]["kind"] == "5"
        assert rows[0]["kind_name"] == "Class"
        assert rows[0]["start_line"] == "0"
        assert rows[0]["start_char"] == "0"
        assert rows[0]["end_line"] == "50"
        assert rows[0]["end_char"] == "0"

    def test_csv_format_document_symbols_kind_translation(self) -> None:
        """Test CSV formatting includes symbol kind name translation."""
        symbols = [
            {"name": "MyClass", "kind": 5, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            {"name": "my_method", "kind": 6, "range": {"start": {"line": 2, "character": 0}, "end": {"line": 3, "character": 0}}},
            {"name": "my_func", "kind": 12, "range": {"start": {"line": 4, "character": 0}, "end": {"line": 5, "character": 0}}},
        ]

        result = format_document_symbols_csv(symbols)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert rows[0]["kind_name"] == "Class"
        assert rows[1]["kind_name"] == "Method"
        assert rows[2]["kind_name"] == "Function"

    def test_csv_format_workspace_symbols_includes_uri(self) -> None:
        """Test workspace symbol CSV includes URI column."""
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            },
        ]

        result = format_workspace_symbols_csv(symbols)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["uri"] == "file:///path/to/myclass.py"
        assert rows[0]["name"] == "MyClass"

    def test_csv_format_symbols_empty(self) -> None:
        """Test CSV formatting returns empty string for no results."""
        symbols: list[dict[str, Any]] = []
        result = format_document_symbols_csv(symbols)

        assert result == ""


class TestCsvFormattingHover:
    """Unit tests for CSV formatting of hover responses."""

    def test_csv_format_hover_simple(self) -> None:
        """Test CSV formatting for hover response."""
        hover = {
            "contents": {
                "kind": "markdown",
                "value": "```python\ndef my_function(x: int) -> str\n```",
            },
            "range": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 15},
            },
        }

        result = format_hover_csv(hover)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert "def my_function" in rows[0]["content"]
        assert rows[0]["range_start_line"] == "10"
        assert rows[0]["range_start_char"] == "4"
        assert rows[0]["range_end_line"] == "10"
        assert rows[0]["range_end_char"] == "15"

    def test_csv_format_hover_single_row(self) -> None:
        """Test hover CSV produces single row (not a list)."""
        hover = {
            "contents": {"kind": "plaintext", "value": "Some hover text"},
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
        }

        result = format_hover_csv(hover)
        lines = result.strip().split("\n")

        # Header + 1 data row = 2 lines
        assert len(lines) == 2

    def test_csv_format_hover_no_range(self) -> None:
        """Test hover CSV handles missing range gracefully."""
        hover = {
            "contents": {"kind": "plaintext", "value": "Some hover text"},
        }

        result = format_hover_csv(hover)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["content"] == "Some hover text"
        # Missing range fields should be empty
        assert rows[0]["range_start_line"] == ""
        assert rows[0]["range_end_line"] == ""

    def test_csv_format_hover_none_content(self) -> None:
        """Test hover CSV handles None hover value."""
        result = format_hover_csv(None)

        assert result == ""


class TestCsvEdgeCases:
    """Edge case tests for CSV formatting."""

    def test_csv_uri_with_comma(self) -> None:
        """Test CSV escaping when URI contains comma."""
        locations = [
            {
                "uri": "file:///path/to/file,with,commas.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
            },
        ]

        result = format_locations_csv(locations)

        # Parse CSV to verify proper escaping
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["uri"] == "file:///path/to/file,with,commas.py"

    def test_csv_uri_with_quotes(self) -> None:
        """Test CSV escaping when URI contains quotes."""
        locations = [
            {
                "uri": 'file:///path/to/file"with"quotes.py',
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
            },
        ]

        result = format_locations_csv(locations)

        # Parse CSV to verify proper escaping
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["uri"] == 'file:///path/to/file"with"quotes.py'

    def test_csv_detail_with_newline(self) -> None:
        """Test CSV escaping when detail contains newline."""
        items = [
            {
                "label": "func",
                "kind": 12,
                "detail": "def func():\n    pass",
                "documentation": "Docs",
            },
        ]

        result = format_completions_csv(items)

        # Parse CSV to verify proper escaping
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["detail"] == "def func():\n    pass"

    def test_csv_empty_string_fields(self) -> None:
        """Test CSV handles empty string fields correctly."""
        items = [
            {"label": "item", "kind": 1, "detail": "", "documentation": ""},
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["detail"] == ""
        assert rows[0]["documentation"] == ""

    def test_csv_none_values(self) -> None:
        """Test CSV represents None values (empty vs 'null')."""
        items = [
            {"label": "item", "kind": 1, "detail": None, "documentation": None},
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        # None values should become empty strings in CSV
        assert rows[0]["detail"] == ""
        assert rows[0]["documentation"] == ""

    def test_csv_unicode_characters(self) -> None:
        """Test CSV handles unicode characters correctly."""
        items = [
            {
                "label": "\u03b1\u03b2\u03b3_func",  # Greek letters
                "kind": 12,
                "detail": "function with \u4e2d\u6587 chars",  # Chinese
                "documentation": "Docs with emoji \U0001F600",
            },
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["label"] == "\u03b1\u03b2\u03b3_func"
        assert rows[0]["detail"] == "function with \u4e2d\u6587 chars"

    def test_csv_very_long_fields(self) -> None:
        """Test CSV handles very long field values."""
        long_detail = "x" * 10000  # 10KB field
        items = [
            {"label": "item", "kind": 1, "detail": long_detail, "documentation": "short"},
        ]

        result = format_completions_csv(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["detail"] == long_detail

    def test_csv_special_chars_in_name(self) -> None:
        """Test CSV handles special characters in symbol names."""
        symbols = [
            {
                "name": "function_with_underscore_and_123_numbers",
                "kind": 12,
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]

        result = format_document_symbols_csv(symbols)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["name"] == "function_with_underscore_and_123_numbers"


class TestOutputFormatEnum:
    """Tests for CSV format option in OutputFormat enum."""

    def test_csv_format_enum_exists(self) -> None:
        """Test that CSV format is available in OutputFormat enum."""
        # This test will fail until CSV is added to the enum
        assert hasattr(OutputFormat, "CSV")
        assert OutputFormat.CSV == "csv"

    def test_csv_format_in_iteration(self) -> None:
        """Test that CSV format can be iterated over with other formats."""
        formats = list(OutputFormat)
        format_values = [f.value for f in formats]

        assert "csv" in format_values
