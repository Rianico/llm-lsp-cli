"""Tests for diagnostic formatting in CompactFormatter.

This test file follows the test specification for diagnostics-compact-range.
Tests are written in RED phase - they will fail until implementation is complete.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import (
    CompactFormatter,
    DiagnosticRecord,
    LocationRecord,
    Position,
    Range,
    SymbolRecord,
)
from llm_lsp_cli.utils import OutputFormat


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_lsp_diagnostic() -> dict[str, Any]:
    """Sample LSP diagnostic with minimal fields."""
    return {
        "range": {
            "start": {"line": 9, "character": 4},
            "end": {"line": 14, "character": 19},
        },
        "severity": 1,
        "code": "reportGeneralTypeIssues",
        "source": "Pyright",
        "message": "Type 'int' is not assignable to type 'str'",
    }


@pytest.fixture
def sample_lsp_diagnostic_with_tags() -> dict[str, Any]:
    """Sample LSP diagnostic with tags."""
    return {
        "range": {
            "start": {"line": 5, "character": 0},
            "end": {"line": 5, "character": 10},
        },
        "severity": 2,
        "code": "deprecated",
        "source": "Pyright",
        "message": "Function is deprecated",
        "tags": [1, 2],  # Unnecessary + Deprecated
    }


@pytest.fixture
def sample_lsp_diagnostic_unknown_tag() -> dict[str, Any]:
    """Sample LSP diagnostic with unknown tag value."""
    return {
        "range": {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 5},
        },
        "severity": 1,
        "code": "test",
        "source": "Test",
        "message": "Test message",
        "tags": [99],  # Unknown tag
    }


@pytest.fixture
def sample_diagnostic_record() -> DiagnosticRecord:
    """Sample DiagnosticRecord with Range object."""
    return DiagnosticRecord(
        file="/tmp/test/file.py",
        range=Range(
            start=Position(line=9, character=4),
            end=Position(line=14, character=19),
        ),
        severity=1,
        severity_name="Error",
        code="reportGeneralTypeIssues",
        source="Pyright",
        message="Type 'int' is not assignable to type 'str'",
        tags=[1, 2],
    )


# =============================================================================
# Scenario Group A: DIAGNOSTIC_TAG_MAP Constant
# =============================================================================


class TestDiagnosticTagMap:
    """Tests for DIAGNOSTIC_TAG_MAP and get_diagnostic_tag_name."""

    def test_diagnostic_tag_map_has_known_values(self) -> None:
        """DIAGNOSTIC_TAG_MAP contains LSP 3.17 defined tags."""
        from llm_lsp_cli.utils.formatter import DIAGNOSTIC_TAG_MAP

        assert DIAGNOSTIC_TAG_MAP[1] == "Unnecessary"
        assert DIAGNOSTIC_TAG_MAP[2] == "Deprecated"

    def test_get_diagnostic_tag_name_returns_names(self) -> None:
        """get_diagnostic_tag_name returns human-readable names for known tags."""
        from llm_lsp_cli.utils.formatter import get_diagnostic_tag_name

        assert get_diagnostic_tag_name(1) == "Unnecessary"
        assert get_diagnostic_tag_name(2) == "Deprecated"

    def test_get_diagnostic_tag_name_unknown_fallback(self) -> None:
        """get_diagnostic_tag_name returns Unknown(N) for unknown tags."""
        from llm_lsp_cli.utils.formatter import get_diagnostic_tag_name

        assert get_diagnostic_tag_name(99) == "Unknown(99)"
        assert get_diagnostic_tag_name(0) == "Unknown(0)"


# =============================================================================
# Scenario Group B: DiagnosticRecord Dataclass Refactor
# =============================================================================


class TestDiagnosticRecordRefactor:
    """Tests for DiagnosticRecord dataclass refactor to use Range."""

    def test_diagnostic_record_has_range_field(self) -> None:
        """DiagnosticRecord has range field of type Range, not 4 position fields."""
        rec = DiagnosticRecord(
            file="test.py",
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=1, character=5),
            ),
            severity=1,
            severity_name="Error",
            code=None,
            source="Test",
            message="Test",
        )

        assert hasattr(rec, "range")
        assert isinstance(rec.range, Range)
        assert not hasattr(rec, "line")  # Old field removed
        assert not hasattr(rec, "character")  # Old field removed
        assert not hasattr(rec, "end_line")  # Old field removed
        assert not hasattr(rec, "end_character")  # Old field removed

    def test_diagnostic_record_range_compact(self) -> None:
        """Range.to_compact() returns 1-indexed compact format."""
        range_obj = Range(
            start=Position(line=9, character=4),  # 0-indexed
            end=Position(line=14, character=19),  # 0-indexed
        )

        assert range_obj.to_compact() == "10:5-15:20"  # 1-indexed


# =============================================================================
# Scenario Group C: Transform Diagnostics
# =============================================================================


class TestTransformDiagnostics:
    """Tests for transform_diagnostics method."""

    def test_transform_diagnostics_creates_range_objects(
        self, sample_lsp_diagnostic: dict[str, Any]
    ) -> None:
        """transform_diagnostics creates DiagnosticRecord with Range, not 4 fields."""
        formatter = CompactFormatter("/tmp/test")
        records = formatter.transform_diagnostics(
            [sample_lsp_diagnostic], file_path="/tmp/test/file.py"
        )

        assert len(records) == 1
        rec = records[0]
        assert hasattr(rec, "range")
        assert rec.range.to_compact() == "10:5-15:20"

    def test_transform_diagnostics_preserves_severity_int(
        self, sample_lsp_diagnostic: dict[str, Any]
    ) -> None:
        """Internal record keeps severity as int for filtering/sorting."""
        formatter = CompactFormatter("/tmp/test")
        records = formatter.transform_diagnostics(
            [sample_lsp_diagnostic], file_path="/tmp/test/file.py"
        )

        assert records[0].severity == 1
        assert records[0].severity_name == "Error"

    def test_transform_diagnostics_preserves_tags_ints(
        self, sample_lsp_diagnostic_with_tags: dict[str, Any]
    ) -> None:
        """Internal record keeps tags as list[int]."""
        formatter = CompactFormatter("/tmp/test")
        records = formatter.transform_diagnostics(
            [sample_lsp_diagnostic_with_tags], file_path="/tmp/test/file.py"
        )

        assert records[0].tags == [1, 2]


# =============================================================================
# Scenario Group D: JSON Output Format
# =============================================================================


class TestDiagnosticsToJson:
    """Tests for diagnostics_to_json method with compact range."""

    def test_diagnostics_to_json_uses_compact_range(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """JSON output has 'range' as compact string, not 4 position fields."""
        formatter = CompactFormatter("/tmp/test")
        json_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.JSON)
        data = json.loads(json_str)

        assert data["items"][0]["range"] == "10:5-15:20"
        assert "line" not in data["items"][0]
        assert "character" not in data["items"][0]
        assert "end_line" not in data["items"][0]
        assert "end_character" not in data["items"][0]

    def test_diagnostics_to_json_no_severity_int(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """JSON output has severity_name only, no severity integer."""
        formatter = CompactFormatter("/tmp/test")
        json_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.JSON)
        data = json.loads(json_str)

        assert data["items"][0]["severity_name"] == "Error"
        assert "severity" not in data["items"][0]

    def test_diagnostics_to_json_translates_tags(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """JSON output has tag names, not integers."""
        formatter = CompactFormatter("/tmp/test")
        json_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.JSON)
        data = json.loads(json_str)

        assert data["items"][0]["tags"] == ["Unnecessary", "Deprecated"]
        assert 1 not in data["items"][0]["tags"]
        assert 2 not in data["items"][0]["tags"]

    def test_diagnostics_to_json_omits_empty_tags(self) -> None:
        """JSON output omits tags field when tags list is empty."""
        rec = DiagnosticRecord(
            file="test.py",
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=1, character=5),
            ),
            severity=1,
            severity_name="Error",
            code=None,
            source="Test",
            message="Test",
            tags=[],
        )

        formatter = CompactFormatter("/tmp/test")
        json_str = OutputDispatcher().format_list([rec], OutputFormat.JSON)
        data = json.loads(json_str)

        assert "tags" not in data["items"][0]

    def test_diagnostics_to_json_unknown_tag_fallback(
        self, sample_lsp_diagnostic_unknown_tag: dict[str, Any]
    ) -> None:
        """JSON output shows Unknown(N) for unknown tag values."""
        formatter = CompactFormatter("/tmp/test")
        records = formatter.transform_diagnostics(
            [sample_lsp_diagnostic_unknown_tag], file_path="/tmp/test/file.py"
        )
        json_str = OutputDispatcher().format_list(records, OutputFormat.JSON)
        data = json.loads(json_str)

        assert data["items"][0]["tags"] == ["Unknown(99)"]


# =============================================================================
# Scenario Group E: YAML Output Format
# =============================================================================


class TestDiagnosticsToYaml:
    """Tests for diagnostics_to_yaml method with compact range."""

    def test_diagnostics_to_yaml_uses_compact_range(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """YAML output has 'range' as compact string."""
        formatter = CompactFormatter("/tmp/test")
        yaml_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.YAML)
        data = yaml.safe_load(yaml_str)

        assert data["items"][0]["range"] == "10:5-15:20"

    def test_diagnostics_to_yaml_no_severity_int(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """YAML output has severity_name only."""
        formatter = CompactFormatter("/tmp/test")
        yaml_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.YAML)
        data = yaml.safe_load(yaml_str)

        assert data["items"][0]["severity_name"] == "Error"
        assert "severity" not in data["items"][0]

    def test_diagnostics_to_yaml_translates_tags(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """YAML output has tag names."""
        formatter = CompactFormatter("/tmp/test")
        yaml_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.YAML)
        data = yaml.safe_load(yaml_str)

        assert data["items"][0]["tags"] == ["Unnecessary", "Deprecated"]


# =============================================================================
# Scenario Group F: TEXT Output Format
# =============================================================================


class TestDiagnosticsToText:
    """Tests for diagnostics_to_text method with bare range format."""

    def test_diagnostics_to_text_bare_range(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """TEXT output appends bare range (no brackets) after message."""
        formatter = CompactFormatter("/tmp/test")
        text = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.TEXT)

        assert "10:5-15:20" in text
        assert "[10:5-15:20]" not in text  # No brackets

    def test_diagnostics_to_text_format_structure(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """TEXT format: 'severity: message, code: <code>, range: <range>, tags: [<tags>]'."""
        text = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.TEXT)

        # New format: "Error: message, code: <code>, range: <range>, tags: [<tags>]"
        expected = (
            "Error: Type 'int' is not assignable to type 'str', "
            "code: reportGeneralTypeIssues, range: 10:5-15:20, tags: [Unnecessary, Deprecated]"
        )
        assert expected in text

    def test_diagnostics_to_text_empty(self) -> None:
        """Empty diagnostics returns empty string."""
        formatter = CompactFormatter("/tmp/test")
        text = OutputDispatcher().format_list([], OutputFormat.TEXT)

        assert text == ""


# =============================================================================
# Scenario Group G: CSV Output Format
# =============================================================================


class TestDiagnosticsToCsv:
    """Tests for diagnostics_to_csv method with compact range."""

    def test_diagnostics_to_csv_headers(self) -> None:
        """CSV has correct headers: file,range,severity_name,code,message,tags."""
        rec = DiagnosticRecord(
            file="test.py",
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=1, character=5),
            ),
            severity=1,
            severity_name="Error",
            code=None,
            source="Test",
            message="Test",
            tags=[],
        )

        formatter = CompactFormatter("/tmp/test")
        csv_str = OutputDispatcher().format_list([rec], OutputFormat.CSV)

        expected_headers = "file,range,severity_name,code,message,tags"
        assert csv_str.startswith(expected_headers)

    def test_diagnostics_to_csv_compact_range(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """CSV range column uses compact format."""
        formatter = CompactFormatter("/tmp/test")
        csv_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.CSV)

        assert "10:5-15:20" in csv_str

    def test_diagnostics_to_csv_severity_name_only(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """CSV has severity_name column, not severity integer."""
        formatter = CompactFormatter("/tmp/test")
        csv_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.CSV)

        # Header should not have severity column
        assert "severity,severity_name" not in csv_str
        # But should have severity_name
        assert "severity_name" in csv_str

    def test_diagnostics_to_csv_tags_pipe_delimited(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """CSV tags column is pipe-delimited tag names."""
        formatter = CompactFormatter("/tmp/test")
        csv_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.CSV)

        assert "Unnecessary|Deprecated" in csv_str


# =============================================================================
# Scenario Group H: Symbol TEXT Format Consistency
# =============================================================================


class TestSymbolsToTextBareRange:
    """Tests for symbols TEXT format."""

    def test_symbols_to_text_bare_range(self) -> None:
        """Symbol TEXT output uses new format: 'name (kind_name), range: <range>'."""
        rec = SymbolRecord(
            file="test.py",
            name="foo",
            kind=12,
            kind_name="Function",
            range=Range(
                start=Position(line=9, character=4),
                end=Position(line=9, character=19),
            ),
        )

        text = OutputDispatcher().format_list([rec], OutputFormat.TEXT)

        # New format: "name (kind_name), range: <range>"
        assert "foo (Function), range: 10:5-10:20" in text


# =============================================================================
# Scenario Group I: Location TEXT Format Consistency
# =============================================================================


class TestLocationsToTextBareRange:
    """Tests for locations TEXT format."""

    def test_locations_to_text_bare_range(self) -> None:
        """Location TEXT output uses bare range format."""
        rec = LocationRecord(
            file="test.py",
            range=Range(
                start=Position(line=9, character=4),
                end=Position(line=9, character=19),
            ),
        )

        formatter = CompactFormatter("/tmp/test")
        text = OutputDispatcher().format_list([rec], OutputFormat.TEXT)

        # Format: "file: range" (no brackets for locations)
        assert "test.py: 10:5-10:20" in text


# =============================================================================
# Negative Test Cases
# =============================================================================


class TestNegativeCases:
    """Negative test cases ensuring unwanted output is absent."""

    @pytest.mark.parametrize(
        "output_format",
        [OutputFormat.JSON, OutputFormat.YAML, OutputFormat.TEXT, OutputFormat.CSV],
    )
    def test_no_severity_int_in_output(
        self, sample_diagnostic_record: DiagnosticRecord, output_format: OutputFormat
    ) -> None:
        """severity integer does not appear in any output format."""
        formatter = CompactFormatter("/tmp/test")
        output = OutputDispatcher().format_list([sample_diagnostic_record], output_format)

        if output_format in (OutputFormat.JSON, OutputFormat.YAML):
            data = (
                json.loads(output)
                if output_format == OutputFormat.JSON
                else yaml.safe_load(output)
            )
            assert "severity" not in data["items"][0] or not isinstance(
                data["items"][0].get("severity"), int
            )
        else:
            # TEXT/CSV: check raw string doesn't contain "severity": 1 pattern
            assert '"severity": 1' not in output

    def test_no_tag_ints_in_json_output(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """Tag integers do not appear in JSON output."""
        formatter = CompactFormatter("/tmp/test")
        json_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.JSON)

        # Should not contain raw tag integers in the tags array
        assert ": [1, 2]" not in json_str
        assert ": [1" not in json_str

    def test_no_four_field_position_in_json(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """4 position fields do not appear in JSON output."""
        formatter = CompactFormatter("/tmp/test")
        json_str = OutputDispatcher().format_list([sample_diagnostic_record], OutputFormat.JSON)
        data = json.loads(json_str)

        assert "line" not in data["items"][0]
        assert "character" not in data["items"][0]
        assert "end_line" not in data["items"][0]
        assert "end_character" not in data["items"][0]


# =============================================================================
# Regression Test Cases
# =============================================================================


class TestRegressionCases:
    """Regression tests ensuring internal behavior is preserved."""

    def test_internal_severity_accessible(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """severity int is accessible on record for filtering/sorting."""
        assert sample_diagnostic_record.severity == 1
        assert isinstance(sample_diagnostic_record.severity, int)

    def test_internal_tags_accessible(
        self, sample_diagnostic_record: DiagnosticRecord
    ) -> None:
        """tags list[int] is accessible on record."""
        assert sample_diagnostic_record.tags == [1, 2]
        assert all(isinstance(t, int) for t in sample_diagnostic_record.tags)

    def test_empty_diagnostics_message_preserved(self) -> None:
        """Empty diagnostics returns empty string."""
        formatter = CompactFormatter("/tmp/test")
        assert OutputDispatcher().format_list([], OutputFormat.TEXT) == ""
