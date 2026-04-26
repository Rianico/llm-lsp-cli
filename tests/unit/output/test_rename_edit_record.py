"""Unit tests for RenameEditRecord dataclass."""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

import pytest

from llm_lsp_cli.output.formatter import Position, Range
from llm_lsp_cli.output.protocol import FormattableRecord

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_range() -> Range:
    """Create a sample Range for testing."""
    return Range(
        start=Position(line=10, character=6),
        end=Position(line=10, character=18),
    )


@pytest.fixture
def sample_rename_edit_record(sample_range: Range) -> Any:
    """Create a sample RenameEditRecord for testing.

    Returns the record once implemented.
    """
    from llm_lsp_cli.output.formatter import RenameEditRecord

    return RenameEditRecord(
        file="src/main.py",
        range=sample_range,
        old_text="OldClassName",
        new_text="NewClassName",
    )


# =============================================================================
# Test Class: TestRenameEditRecordExists
# =============================================================================


class TestRenameEditRecordExists:
    """Tests verifying RenameEditRecord dataclass exists and is importable."""

    def test_rename_edit_record_exists(self) -> None:
        """Verify RenameEditRecord can be imported from formatter module."""
        from llm_lsp_cli.output.formatter import RenameEditRecord

        assert RenameEditRecord is not None

    def test_rename_edit_record_is_dataclass(self) -> None:
        """Verify RenameEditRecord is decorated with @dataclass."""
        from llm_lsp_cli.output.formatter import RenameEditRecord

        assert is_dataclass(RenameEditRecord)


# =============================================================================
# Test Class: TestRenameEditRecordFields
# =============================================================================


class TestRenameEditRecordFields:
    """Tests verifying RenameEditRecord has all required fields."""

    def test_rename_edit_record_has_file_field(self, sample_range: Range) -> None:
        """Verify RenameEditRecord has file field."""
        from llm_lsp_cli.output.formatter import RenameEditRecord

        record = RenameEditRecord(
            file="src/main.py",
            range=sample_range,
            old_text="OldClassName",
            new_text="NewClassName",
        )
        assert record.file == "src/main.py"

    def test_rename_edit_record_has_range_field(self, sample_range: Range) -> None:
        """Verify RenameEditRecord has range field as Range object."""
        from llm_lsp_cli.output.formatter import RenameEditRecord

        record = RenameEditRecord(
            file="src/main.py",
            range=sample_range,
            old_text="OldClassName",
            new_text="NewClassName",
        )
        assert isinstance(record.range, Range)

    def test_rename_edit_record_has_old_text_field(self, sample_range: Range) -> None:
        """Verify RenameEditRecord has old_text field."""
        from llm_lsp_cli.output.formatter import RenameEditRecord

        record = RenameEditRecord(
            file="src/main.py",
            range=sample_range,
            old_text="OldClassName",
            new_text="NewClassName",
        )
        assert record.old_text == "OldClassName"

    def test_rename_edit_record_has_new_text_field(self, sample_range: Range) -> None:
        """Verify RenameEditRecord has new_text field."""
        from llm_lsp_cli.output.formatter import RenameEditRecord

        record = RenameEditRecord(
            file="src/main.py",
            range=sample_range,
            old_text="OldClassName",
            new_text="NewClassName",
        )
        assert record.new_text == "NewClassName"


# =============================================================================
# Test Class: TestRenameEditRecordFormattableRecord
# =============================================================================


class TestRenameEditRecordFormattableRecord:
    """Tests verifying RenameEditRecord implements FormattableRecord protocol."""

    def test_implements_formattable_record_protocol(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify RenameEditRecord implements FormattableRecord protocol."""
        assert isinstance(sample_rename_edit_record, FormattableRecord)

    def test_has_to_compact_dict_method(self, sample_rename_edit_record: Any) -> None:
        """Verify RenameEditRecord has to_compact_dict method."""
        assert callable(sample_rename_edit_record.to_compact_dict)

    def test_has_get_csv_headers_method(self, sample_rename_edit_record: Any) -> None:
        """Verify RenameEditRecord has get_csv_headers method."""
        assert callable(sample_rename_edit_record.get_csv_headers)

    def test_has_get_csv_row_method(self, sample_rename_edit_record: Any) -> None:
        """Verify RenameEditRecord has get_csv_row method."""
        assert callable(sample_rename_edit_record.get_csv_row)

    def test_has_get_text_line_method(self, sample_rename_edit_record: Any) -> None:
        """Verify RenameEditRecord has get_text_line method."""
        assert callable(sample_rename_edit_record.get_text_line)


# =============================================================================
# Test Class: TestRenameEditRecordToCompactDict
# =============================================================================


class TestRenameEditRecordToCompactDict:
    """Tests for RenameEditRecord.to_compact_dict method."""

    def test_to_compact_dict_returns_dict(self, sample_rename_edit_record: Any) -> None:
        """Verify to_compact_dict returns a dict."""
        result = sample_rename_edit_record.to_compact_dict()
        assert isinstance(result, dict)

    def test_to_compact_dict_has_file_key(self, sample_rename_edit_record: Any) -> None:
        """Verify to_compact_dict has file key."""
        result = sample_rename_edit_record.to_compact_dict()
        assert "file" in result

    def test_to_compact_dict_has_range_key(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify to_compact_dict has range key."""
        result = sample_rename_edit_record.to_compact_dict()
        assert "range" in result

    def test_to_compact_dict_has_old_text_key(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify to_compact_dict has old_text key."""
        result = sample_rename_edit_record.to_compact_dict()
        assert "old_text" in result

    def test_to_compact_dict_has_new_text_key(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify to_compact_dict has new_text key."""
        result = sample_rename_edit_record.to_compact_dict()
        assert "new_text" in result

    def test_to_compact_dict_range_is_compact_string(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify range is formatted as compact string (1-based)."""
        result = sample_rename_edit_record.to_compact_dict()
        # Range is 0-based line=10, char=6 to line=10, char=18
        # Compact format is 1-based: 11:7-11:19
        assert result["range"] == "11:7-11:19"


# =============================================================================
# Test Class: TestRenameEditRecordCsvMethods
# =============================================================================


class TestRenameEditRecordCsvMethods:
    """Tests for RenameEditRecord CSV methods."""

    def test_get_csv_headers_returns_list(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify get_csv_headers returns a list."""
        headers = sample_rename_edit_record.get_csv_headers()
        assert isinstance(headers, list)

    def test_get_csv_headers_contains_expected_fields(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify get_csv_headers contains expected field names."""
        headers = sample_rename_edit_record.get_csv_headers()
        expected = ["file", "range", "old_text", "new_text"]
        assert headers == expected

    def test_get_csv_row_returns_dict(self, sample_rename_edit_record: Any) -> None:
        """Verify get_csv_row returns a dict."""
        row = sample_rename_edit_record.get_csv_row()
        assert isinstance(row, dict)

    def test_get_csv_row_has_all_headers(self, sample_rename_edit_record: Any) -> None:
        """Verify get_csv_row has all headers as keys."""
        headers = sample_rename_edit_record.get_csv_headers()
        row = sample_rename_edit_record.get_csv_row()
        assert all(h in row for h in headers)

    def test_get_csv_row_range_is_compact(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify CSV row range is compact string format."""
        row = sample_rename_edit_record.get_csv_row()
        # Range is 0-based line=10, char=6 to line=10, char=18
        # Compact format is 1-based: 11:7-11:19
        assert row["range"] == "11:7-11:19"


# =============================================================================
# Test Class: TestRenameEditRecordTextLine
# =============================================================================


class TestRenameEditRecordTextLine:
    """Tests for RenameEditRecord.get_text_line method."""

    def test_get_text_line_returns_string(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify get_text_line returns a string."""
        line = sample_rename_edit_record.get_text_line()
        assert isinstance(line, str)

    def test_get_text_line_contains_file(self, sample_rename_edit_record: Any) -> None:
        """Verify get_text_line contains file path."""
        line = sample_rename_edit_record.get_text_line()
        assert "src/main.py" in line

    def test_get_text_line_contains_range(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify get_text_line contains compact range."""
        line = sample_rename_edit_record.get_text_line()
        assert "11:7-11:19" in line

    def test_get_text_line_contains_old_text(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify get_text_line contains old_text."""
        line = sample_rename_edit_record.get_text_line()
        assert "OldClassName" in line

    def test_get_text_line_contains_new_text(
        self, sample_rename_edit_record: Any
    ) -> None:
        """Verify get_text_line contains new_text."""
        line = sample_rename_edit_record.get_text_line()
        assert "NewClassName" in line

    def test_get_text_line_format(self, sample_rename_edit_record: Any) -> None:
        """Verify exact format of text line output."""
        line = sample_rename_edit_record.get_text_line()
        # Format: "file:range 'old_text' -> 'new_text'"
        expected = "src/main.py:11:7-11:19 'OldClassName' -> 'NewClassName'"
        assert line == expected
