"""Unit tests for CompletionRecord dataclass."""

from __future__ import annotations

import pytest

from llm_lsp_cli.output.formatter import CompletionRecord, Position, Range
from llm_lsp_cli.output.protocol import FormattableRecord


class TestCompletionRecordFormattableRecord:
    """Tests for CompletionRecord implementing FormattableRecord protocol."""

    def test_completion_record_implements_formattable_record(self) -> None:
        """CompletionRecord should implement FormattableRecord protocol."""
        record = CompletionRecord(
            file="src/main.py",
            label="my_function",
            kind=12,
            kind_name="Function",
        )
        assert isinstance(record, FormattableRecord)

    def test_completion_record_to_compact_dict_returns_correct_structure(self) -> None:
        """CompletionRecord.to_compact_dict should return dict with compact range."""
        range_obj = Range(
            start=Position(line=5, character=0),
            end=Position(line=5, character=10),
        )
        position = Range(
            start=Position(line=5, character=5),
            end=Position(line=5, character=5),
        )
        record = CompletionRecord(
            file="src/main.py",
            label="my_function",
            kind=12,
            kind_name="Function",
            detail="def my_function(x: int) -> str",
            documentation="A sample function.",
            range=range_obj,
            position=position,
        )
        result = record.to_compact_dict()
        assert result["file"] == "src/main.py"
        assert result["label"] == "my_function"
        assert result["kind_name"] == "Function"
        assert result["detail"] == "def my_function(x: int) -> str"
        assert result["documentation"] == "A sample function."
        assert result["range"] == "6:1-6:11"
        # Position is formatted as a range "6:6-6:6" since it's stored as a Range
        assert result["position"] == "6:6-6:6"

    def test_completion_record_get_csv_headers_returns_expected_columns(self) -> None:
        """CompletionRecord.get_csv_headers should return expected columns."""
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=12,
            kind_name="Function",
        )
        headers = record.get_csv_headers()
        assert "file" in headers
        assert "label" in headers
        assert "kind_name" in headers
        assert "detail" in headers
        assert "range" in headers

    def test_completion_record_get_csv_row_returns_string_values(self) -> None:
        """CompletionRecord.get_csv_row should return all string values."""
        range_obj = Range(
            start=Position(line=5, character=0),
            end=Position(line=5, character=10),
        )
        record = CompletionRecord(
            file="src/main.py",
            label="my_function",
            kind=12,
            kind_name="Function",
            detail="def my_function(x: int) -> str",
            range=range_obj,
        )
        row = record.get_csv_row()
        assert isinstance(row["file"], str)
        assert isinstance(row["label"], str)
        assert isinstance(row["kind_name"], str)
        assert isinstance(row["detail"], str)
        assert isinstance(row["range"], str)
        assert row["range"] == "6:1-6:11"

    def test_completion_record_get_text_line_returns_single_line(self) -> None:
        """CompletionRecord.get_text_line should return single line without newlines."""
        range_obj = Range(
            start=Position(line=5, character=0),
            end=Position(line=5, character=10),
        )
        record = CompletionRecord(
            file="src/main.py",
            label="my_function",
            kind=12,
            kind_name="Function",
            range=range_obj,
        )
        line = record.get_text_line()
        assert "\n" not in line
        assert "src/main.py" in line
        assert "my_function" in line
        assert "[6:1-6:11]" in line

    def test_completion_record_omits_none_fields_from_dict(self) -> None:
        """CompletionRecord.to_compact_dict should omit None fields."""
        record = CompletionRecord(
            file="src/main.py",
            label="my_function",
            kind=12,
            kind_name="Function",
            detail=None,
            documentation=None,
            range=None,
            position=None,
        )
        result = record.to_compact_dict()
        assert "detail" not in result
        assert "documentation" not in result
        assert "range" not in result
        assert "position" not in result


class TestCompletionRecordRangeFormat:
    """Tests for compact range format in CompletionRecord."""

    def test_range_format_is_one_based(self) -> None:
        """Range format should be 1-based (LSP is 0-based)."""
        # LSP: line=0, char=0 -> compact: 1:1
        range_obj = Range(
            start=Position(line=0, character=0),
            end=Position(line=0, character=10),
        )
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=13,
            kind_name="Variable",
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
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=13,
            kind_name="Variable",
            range=range_obj,
        )
        row = record.get_csv_row()
        # 0-based (10,5)-(10,15) -> 1-based "11:6-11:16"
        assert row["range"] == "11:6-11:16"

    def test_multi_line_range_formatted_correctly(self) -> None:
        """Multi-line ranges should be formatted correctly."""
        range_obj = Range(
            start=Position(line=0, character=0),
            end=Position(line=5, character=10),
        )
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=13,
            kind_name="Variable",
            range=range_obj,
        )
        row = record.get_csv_row()
        assert row["range"] == "1:1-6:11"


class TestCompletionRecordCSVEdgeCases:
    """Tests for CSV edge cases in CompletionRecord."""

    def test_csv_uses_empty_string_for_none_range(self) -> None:
        """CSV should use empty string for None range, not 'null'."""
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=13,
            kind_name="Variable",
            range=None,
        )
        row = record.get_csv_row()
        assert row["range"] == ""

    def test_csv_uses_empty_string_for_none_detail(self) -> None:
        """CSV should use empty string for None detail."""
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=13,
            kind_name="Variable",
            detail=None,
        )
        row = record.get_csv_row()
        assert row["detail"] == ""

    def test_csv_uses_empty_string_for_none_documentation(self) -> None:
        """CSV should use empty string for None documentation."""
        record = CompletionRecord(
            file="test.py",
            label="foo",
            kind=13,
            kind_name="Variable",
            documentation=None,
        )
        row = record.get_csv_row()
        assert row["documentation"] == ""
