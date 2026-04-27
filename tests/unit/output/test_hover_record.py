"""Unit tests for HoverRecord dataclass."""

from __future__ import annotations

import pytest

from llm_lsp_cli.output.formatter import HoverRecord, Position, Range
from llm_lsp_cli.output.protocol import FormattableRecord


class TestHoverRecordFormattableRecord:
    """Tests for HoverRecord implementing FormattableRecord protocol."""

    def test_hover_record_implements_formattable_record(self) -> None:
        """HoverRecord should implement FormattableRecord protocol."""
        record = HoverRecord(
            file="src/main.py",
            content="def my_function(x: int) -> str",
        )
        assert isinstance(record, FormattableRecord)

    def test_hover_record_to_compact_dict_returns_correct_structure(self) -> None:
        """HoverRecord.to_compact_dict should return dict with compact range."""
        range_obj = Range(
            start=Position(line=10, character=4),
            end=Position(line=10, character=15),
        )
        record = HoverRecord(
            file="src/main.py",
            content="def my_function(x: int) -> str",
            range=range_obj,
        )
        result = record.to_compact_dict()
        assert result["file"] == "src/main.py"
        assert result["content"] == "def my_function(x: int) -> str"
        assert result["range"] == "11:5-11:16"

    def test_hover_record_get_csv_headers_returns_expected_columns(self) -> None:
        """HoverRecord.get_csv_headers should return expected columns."""
        record = HoverRecord(
            file="test.py",
            content="docs",
        )
        headers = record.get_csv_headers()
        assert headers == ["file", "content", "range"]

    def test_hover_record_get_csv_row_handles_none_range(self) -> None:
        """HoverRecord.get_csv_row should handle None range with empty string."""
        record = HoverRecord(
            file="src/main.py",
            content="Some documentation",
            range=None,
        )
        row = record.get_csv_row()
        assert row["file"] == "src/main.py"
        assert row["content"] == "Some documentation"
        assert row["range"] == ""

    def test_hover_record_get_text_line_formats_correctly(self) -> None:
        """HoverRecord.get_text_line should format with file and content."""
        range_obj = Range(
            start=Position(line=10, character=4),
            end=Position(line=10, character=15),
        )
        record = HoverRecord(
            file="src/main.py",
            content="def my_function(x: int) -> str",
            range=range_obj,
        )
        line = record.get_text_line()
        assert "src/main.py" in line
        assert "def my_function" in line
        assert "[11:5-11:16]" in line

    def test_hover_record_to_compact_dict_omits_none_range(self) -> None:
        """HoverRecord.to_compact_dict should omit None range field."""
        record = HoverRecord(
            file="src/main.py",
            content="Some documentation",
            range=None,
        )
        result = record.to_compact_dict()
        assert "range" not in result


class TestHoverRecordRangeFormat:
    """Tests for compact range format in HoverRecord."""

    def test_range_format_is_one_based(self) -> None:
        """Range format should be 1-based (LSP is 0-based)."""
        range_obj = Range(
            start=Position(line=0, character=0),
            end=Position(line=0, character=10),
        )
        record = HoverRecord(
            file="test.py",
            content="docs",
            range=range_obj,
        )
        row = record.get_csv_row()
        assert row["range"] == "1:1-1:11"

    def test_range_format_uses_colon_separator(self) -> None:
        """Range format should use colon separator: line:char-line:char."""
        range_obj = Range(
            start=Position(line=10, character=5),
            end=Position(line=10, character=15),
        )
        record = HoverRecord(
            file="test.py",
            content="docs",
            range=range_obj,
        )
        row = record.get_csv_row()
        assert row["range"] == "11:6-11:16"

    def test_multi_line_range_formatted_correctly(self) -> None:
        """Multi-line ranges should be formatted correctly."""
        range_obj = Range(
            start=Position(line=0, character=0),
            end=Position(line=5, character=10),
        )
        record = HoverRecord(
            file="test.py",
            content="docs",
            range=range_obj,
        )
        row = record.get_csv_row()
        assert row["range"] == "1:1-6:11"


class TestHoverRecordCSVEdgeCases:
    """Tests for CSV edge cases in HoverRecord."""

    def test_csv_uses_empty_string_for_none_range(self) -> None:
        """CSV should use empty string for None range."""
        record = HoverRecord(
            file="test.py",
            content="docs",
            range=None,
        )
        row = record.get_csv_row()
        assert row["range"] == ""

    def test_text_line_without_range(self) -> None:
        """Text line should work without range."""
        record = HoverRecord(
            file="test.py",
            content="Some docs",
            range=None,
        )
        line = record.get_text_line()
        assert "test.py" in line
        assert "Some docs" in line

    def test_content_with_special_characters(self) -> None:
        """Content with special characters should be handled."""
        record = HoverRecord(
            file="test.py",
            content="def foo(x: int) -> str:\n    return str(x)",
            range=None,
        )
        # Content should be preserved, newline handling is implementation detail
        result = record.to_compact_dict()
        assert "def foo" in result["content"]
