"""Tests for refined output feature: diagnostics source removal and rename grouping.

RED phase tests - these tests WILL FAIL until implementation is complete.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import (
    DiagnosticRecord,
    Position,
    Range,
    RenameEditRecord,
)
from llm_lsp_cli.utils import OutputFormat


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_diagnostic_record() -> DiagnosticRecord:
    """DiagnosticRecord with source field."""
    return DiagnosticRecord(
        file="src/auth.py",
        range=Range(
            start=Position(line=14, character=9),
            end=Position(line=14, character=24),
        ),
        severity=1,
        severity_name="Error",
        code="reportGeneralTypeIssues",
        source="pyright",
        message="Cannot assign to 'const' variable",
        tags=[],
    )


@pytest.fixture
def sample_diagnostic_records() -> list[DiagnosticRecord]:
    """Multiple DiagnosticRecord objects."""
    return [
        DiagnosticRecord(
            file="src/auth.py",
            range=Range(
                start=Position(line=14, character=9),
                end=Position(line=14, character=24),
            ),
            severity=1,
            severity_name="Error",
            code="reportGeneralTypeIssues",
            source="pyright",
            message="First error",
            tags=[],
        ),
        DiagnosticRecord(
            file="src/auth.py",
            range=Range(
                start=Position(line=41, character=0),
                end=Position(line=41, character=9),
            ),
            severity=2,
            severity_name="Warning",
            code="reportUnusedImport",
            source="pyright",
            message="Unused import",
            tags=[1],
        ),
    ]


@pytest.fixture
def sample_rename_edit_records() -> list[RenameEditRecord]:
    """Multiple RenameEditRecord objects across multiple files."""
    return [
        # File 1: src/main.py (2 edits)
        RenameEditRecord(
            file="src/main.py",
            range=Range(
                start=Position(line=9, character=4),
                end=Position(line=9, character=7),
            ),
            old_text="foo",
            new_text="bar",
        ),
        RenameEditRecord(
            file="src/main.py",
            range=Range(
                start=Position(line=44, character=19),
                end=Position(line=44, character=22),
            ),
            old_text="foo",
            new_text="bar",
        ),
        # File 2: src/utils.py (1 edit)
        RenameEditRecord(
            file="src/utils.py",
            range=Range(
                start=Position(line=4, character=0),
                end=Position(line=4, character=3),
            ),
            old_text="foo",
            new_text="bar",
        ),
        # File 3: tests/test_main.py (2 edits)
        RenameEditRecord(
            file="tests/test_main.py",
            range=Range(
                start=Position(line=11, character=9),
                end=Position(line=11, character=12),
            ),
            old_text="foo",
            new_text="bar",
        ),
        RenameEditRecord(
            file="tests/test_main.py",
            range=Range(
                start=Position(line=29, character=4),
                end=Position(line=29, character=7),
            ),
            old_text="foo",
            new_text="bar",
        ),
    ]


@pytest.fixture
def sample_rename_single_file() -> list[RenameEditRecord]:
    """RenameEditRecord objects all in single file."""
    return [
        RenameEditRecord(
            file="src/main.py",
            range=Range(
                start=Position(line=9, character=4),
                end=Position(line=9, character=7),
            ),
            old_text="foo",
            new_text="bar",
        ),
        RenameEditRecord(
            file="src/main.py",
            range=Range(
                start=Position(line=44, character=19),
                end=Position(line=44, character=22),
            ),
            old_text="foo",
            new_text="bar",
        ),
    ]


@pytest.fixture
def empty_rename_records() -> list[RenameEditRecord]:
    """Empty list of rename records."""
    return []


# =============================================================================
# DR-001: Diagnostics JSON Element Omits Source
# =============================================================================


class TestDiagnosticsJsonSourceRemoval:
    """Tests for diagnostics JSON output omitting source from elements."""

    def test_json_element_omits_source(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """JSON diagnostic elements do NOT contain source field."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.JSON,
            _source="pyright",
            file_path="src/auth.py",
            command="diagnostics",
        )
        data = json.loads(output)

        assert "_source" in data  # Top level has source
        assert "source" not in data["items"][0]  # Element does NOT have source
        assert "source" not in data["items"][1]

    def test_json_structure_contract(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """JSON structure has _source, command, file, items with correct fields."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.JSON,
            _source="pyright",
            file_path="src/auth.py",
            command="diagnostics",
        )
        data = json.loads(output)

        assert "_source" in data
        assert "command" in data
        assert "file" in data
        assert "items" in data
        assert isinstance(data["items"], list)

        # Element fields
        item = data["items"][0]
        assert "range" in item
        assert "severity_name" in item
        assert "message" in item
        assert "source" not in item


# =============================================================================
# DR-002: Diagnostics YAML Element Omits Source
# =============================================================================


class TestDiagnosticsYamlSourceRemoval:
    """Tests for diagnostics YAML output omitting source from elements."""

    def test_yaml_element_omits_source(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """YAML diagnostic elements do NOT contain source field."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.YAML,
            _source="pyright",
            file_path="src/auth.py",
            command="diagnostics",
        )
        data = yaml.safe_load(output)

        assert "_source" in data
        assert "source" not in data["items"][0]


# =============================================================================
# DR-003: Diagnostics CSV Omits Source Column
# =============================================================================


class TestDiagnosticsCsvSourceRemoval:
    """Tests for diagnostics CSV output omitting source column."""

    def test_csv_no_source_column(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """CSV headers do NOT include source column."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.CSV,
        )
        lines = output.strip().split("\n")
        headers = lines[0]

        assert "source" not in headers
        expected_headers = "file,range,severity_name,code,message,tags"
        assert headers == expected_headers

    def test_csv_rows_no_source_value(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """CSV rows do NOT include source value."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.CSV,
        )
        lines = output.strip().split("\n")

        # Check that pyright doesn't appear in data rows
        for line in lines[1:]:
            assert "pyright" not in line


# =============================================================================
# DR-004: Diagnostics TEXT Format Unchanged
# =============================================================================


class TestDiagnosticsTextUnchanged:
    """Tests for diagnostics TEXT format unchanged."""

    def test_text_format_unchanged(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """TEXT format diagnostics remain unchanged."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.TEXT,
        )

        # Verify format still works and doesn't contain source
        assert "Error: First error" in output
        assert "Warning: Unused import" in output
        # TEXT already omits source, verify no regression
        assert output.count(":") > 0  # Has formatting


# =============================================================================
# RG-001: Group Function Returns Correct Structure
# =============================================================================


class TestGroupRenameEditsByFile:
    """Tests for group_rename_edits_by_file helper function."""

    def test_group_function_exists(self) -> None:
        """group_rename_edits_by_file function exists."""
        from llm_lsp_cli.output.formatter import group_rename_edits_by_file

        assert callable(group_rename_edits_by_file)

    def test_group_returns_correct_structure(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """group_rename_edits_by_file returns (old_text, new_text, file_records)."""
        from llm_lsp_cli.output.formatter import RenameFileRecord, group_rename_edits_by_file

        old_text, new_text, file_records = group_rename_edits_by_file(
            sample_rename_edit_records
        )

        assert old_text == "foo"
        assert new_text == "bar"
        assert len(file_records) == 3

        # Check file paths are sorted
        assert file_records[0].file == "src/main.py"
        assert file_records[1].file == "src/utils.py"
        assert file_records[2].file == "tests/test_main.py"

        # Check ranges are grouped
        assert len(file_records[0].ranges) == 2  # src/main.py has 2 edits
        assert len(file_records[1].ranges) == 1  # src/utils.py has 1 edit
        assert len(file_records[2].ranges) == 2  # tests/test_main.py has 2 edits

    def test_group_handles_empty(
        self, empty_rename_records: list[RenameEditRecord]
    ) -> None:
        """group_rename_edits_by_file handles empty list."""
        from llm_lsp_cli.output.formatter import group_rename_edits_by_file

        old_text, new_text, file_records = group_rename_edits_by_file(empty_rename_records)

        assert old_text == ""
        assert new_text == ""
        assert file_records == []


# =============================================================================
# RG-002: Rename JSON Groups Edits by File
# =============================================================================


class TestRenameJsonGrouping:
    """Tests for rename JSON output grouping by file."""

    def test_format_rename_grouped_exists(self) -> None:
        """format_rename_grouped method exists on OutputDispatcher."""
        dispatcher = OutputDispatcher()
        assert hasattr(dispatcher, "format_rename_grouped")
        assert callable(dispatcher.format_rename_grouped)

    def test_json_hoisted_old_new_text(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """Rename JSON has old_text/new_text at command level, not item level."""
        dispatcher = OutputDispatcher()

        output = dispatcher.format_rename_grouped(
            sample_rename_edit_records,
            OutputFormat.JSON,
            _source="pyright",
            command="rename",
        )
        data = json.loads(output)

        # Command level has old_text/new_text
        assert data["old_text"] == "foo"
        assert data["new_text"] == "bar"

        # Items do NOT have old_text/new_text
        for item in data["items"]:
            assert "old_text" not in item
            assert "new_text" not in item
            assert "file" in item
            assert "ranges" in item
            assert isinstance(item["ranges"], list)

    def test_json_grouped_by_file(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """Rename JSON groups edits by file with ranges array."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_rename_grouped(
            sample_rename_edit_records,
            OutputFormat.JSON,
            _source="pyright",
            command="rename",
        )
        data = json.loads(output)

        items = data["items"]
        assert len(items) == 3  # 3 unique files

        # Find src/main.py entry
        main_entry = next(i for i in items if i["file"] == "src/main.py")
        assert len(main_entry["ranges"]) == 2
        assert "10:5-10:8" in main_entry["ranges"]
        assert "45:20-45:23" in main_entry["ranges"]


# =============================================================================
# RG-003: Rename YAML Groups Edits by File
# =============================================================================


class TestRenameYamlGrouping:
    """Tests for rename YAML output grouping by file."""

    def test_yaml_structure_matches_json(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """Rename YAML has same structure as JSON."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_rename_grouped(
            sample_rename_edit_records,
            OutputFormat.YAML,
            _source="pyright",
            command="rename",
        )
        data = yaml.safe_load(output)

        assert data["old_text"] == "foo"
        assert data["new_text"] == "bar"
        assert len(data["items"]) == 3
        assert "file" in data["items"][0]
        assert "ranges" in data["items"][0]


# =============================================================================
# RG-004: Rename TEXT Format Groups by File
# =============================================================================


class TestRenameTextGrouping:
    """Tests for rename TEXT output grouping by file."""

    def test_text_grouped_format(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """Rename TEXT format shows 'Rename: X -> Y' header and groups by file."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_rename_grouped(
            sample_rename_edit_records,
            OutputFormat.TEXT,
        )

        # Header line
        assert "Rename: 'foo' -> 'bar'" in output

        # File grouping
        assert "File: src/main.py" in output
        assert "File: src/utils.py" in output
        assert "File: tests/test_main.py" in output

        # Indented ranges (two-space indent)
        lines = output.split("\n")
        for line in lines:
            if line.strip().startswith("-") and not line.startswith("File:"):
                assert line.startswith("  -")  # Two-space indent for ranges


# =============================================================================
# RG-005: Rename CSV Remains Flat
# =============================================================================


class TestRenameCsvFlat:
    """Tests for rename CSV output remaining flat."""

    def test_csv_flat_format(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """Rename CSV remains flat with repeated old_text/new_text."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_rename_edit_records,
            OutputFormat.CSV,
        )
        lines = output.strip().split("\n")

        # Header unchanged
        assert lines[0] == "file,range,old_text,new_text"

        # 5 data rows (one per edit, not grouped)
        assert len(lines) == 6  # header + 5 rows

        # Each row has old_text and new_text
        for line in lines[1:]:
            assert ",foo,bar" in line


# =============================================================================
# Negative Tests: Fields Must NOT Appear
# =============================================================================


class TestNegativeCases:
    """Negative tests ensuring unwanted fields do not appear."""

    def test_diagnostics_element_must_not_have_source(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """NEGATIVE: Diagnostic elements MUST NOT contain source field."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.JSON,
            _source="pyright",
        )
        data = json.loads(output)

        for item in data["items"]:
            assert "source" not in item, f"Element contains forbidden 'source' field: {item}"

    def test_diagnostics_csv_must_not_have_source_column(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """NEGATIVE: Diagnostic CSV MUST NOT include source column."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.CSV,
        )

        assert "source" not in output.split("\n")[0], "CSV headers contain forbidden 'source' column"

    def test_rename_items_must_not_have_old_new_text(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """NEGATIVE: Rename items MUST NOT contain old_text/new_text at item level."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_rename_grouped(
            sample_rename_edit_records,
            OutputFormat.JSON,
        )
        data = json.loads(output)

        for item in data["items"]:
            assert "old_text" not in item, f"Item contains forbidden 'old_text' field: {item}"
            assert "new_text" not in item, f"Item contains forbidden 'new_text' field: {item}"


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegressionCases:
    """Regression tests ensuring existing behavior is preserved."""

    def test_diagnostics_text_unchanged(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """REGRESSION: Diagnostics TEXT format continues to work."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.TEXT,
        )
        assert output != ""
        assert "Error:" in output

    def test_source_still_at_top_level(
        self, sample_diagnostic_records: list[DiagnosticRecord]
    ) -> None:
        """REGRESSION: _source field still appears at top level."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_diagnostic_records,
            OutputFormat.JSON,
            _source="pyright",
        )
        data = json.loads(output)
        assert data["_source"] == "pyright"

    def test_rename_csv_unchanged(
        self, sample_rename_edit_records: list[RenameEditRecord]
    ) -> None:
        """REGRESSION: Rename CSV format unchanged (flat with repeated columns)."""
        dispatcher = OutputDispatcher()
        output = dispatcher.format_list(
            sample_rename_edit_records,
            OutputFormat.CSV,
        )
        lines = output.strip().split("\n")
        assert len(lines) == 6  # header + 5 flat rows
