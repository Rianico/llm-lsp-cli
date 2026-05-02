"""Tests for references grouping in formatter.py.

This module tests the group_locations_by_file function for grouping
reference command output by file path.
"""

from __future__ import annotations

import csv
import inspect
import io
import json

import pytest
import yaml

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.utils import OutputFormat


class TestGroupLocationsByFile:
    """Test LocationRecord grouping for references output."""

    def test_group_locations_by_file_groups_by_path(self) -> None:
        """T-001: Records grouped by unique file paths."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
            group_locations_by_file,
        )

        records = [
            LocationRecord(
                file="src/utils.py",
                range=Range(start=Position(4, 9), end=Position(4, 24)),
            ),
            LocationRecord(
                file="src/main.py",
                range=Range(start=Position(19, 9), end=Position(19, 24)),
            ),
            LocationRecord(
                file="src/utils.py",
                range=Range(start=Position(7, 4), end=Position(7, 19)),
            ),
        ]
        result = group_locations_by_file(records)
        assert len(result) == 2
        files = [g["file"] for g in result]
        assert "src/main.py" in files
        assert "src/utils.py" in files

    def test_groups_sorted_alphabetically(self) -> None:
        """T-002: Groups appear in alphabetical order by file path."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
            group_locations_by_file,
        )

        records = [
            LocationRecord(
                file="z/module.py",
                range=Range(start=Position(0, 0), end=Position(0, 10)),
            ),
            LocationRecord(
                file="a/module.py",
                range=Range(start=Position(0, 0), end=Position(0, 10)),
            ),
            LocationRecord(
                file="m/module.py",
                range=Range(start=Position(0, 0), end=Position(0, 10)),
            ),
        ]
        result = group_locations_by_file(records)
        files = [g["file"] for g in result]
        assert files == ["a/module.py", "m/module.py", "z/module.py"]

    def test_ranges_sorted_by_line_within_group(self) -> None:
        """T-003: Ranges sorted by start line ascending within each file group."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
            group_locations_by_file,
        )

        records = [
            LocationRecord(
                file="src/utils.py",
                range=Range(start=Position(20, 0), end=Position(20, 10)),
            ),
            LocationRecord(
                file="src/utils.py",
                range=Range(start=Position(5, 0), end=Position(5, 10)),
            ),
            LocationRecord(
                file="src/utils.py",
                range=Range(start=Position(15, 0), end=Position(15, 10)),
            ),
        ]
        result = group_locations_by_file(records)
        utils_group = [g for g in result if g["file"] == "src/utils.py"][0]
        lines = [r["range"].split(":")[0] for r in utils_group["references"]]
        assert lines == ["6", "16", "21"]  # 1-based: 5+1, 15+1, 20+1

    def test_group_locations_empty_input(self) -> None:
        """T-010: Empty list returns empty list."""
        from llm_lsp_cli.output.formatter import group_locations_by_file

        result = group_locations_by_file([])
        assert result == []

    def test_group_locations_single_record(self) -> None:
        """T-011: Single record returns single group."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
            group_locations_by_file,
        )

        records = [
            LocationRecord(
                file="src/main.py",
                range=Range(start=Position(0, 0), end=Position(0, 10)),
            )
        ]
        result = group_locations_by_file(records)
        assert len(result) == 1
        assert result[0]["file"] == "src/main.py"
        assert len(result[0]["references"]) == 1

    def test_ranges_same_line_ordered_by_character(self) -> None:
        """T-012: Ranges on same line ordered by character position."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
            group_locations_by_file,
        )

        records = [
            LocationRecord(
                file="src/main.py",
                range=Range(start=Position(10, 20), end=Position(10, 30)),
            ),
            LocationRecord(
                file="src/main.py",
                range=Range(start=Position(10, 5), end=Position(10, 15)),
            ),
        ]
        result = group_locations_by_file(records)
        refs = result[0]["references"]
        # 10:5 should come before 10:20 (0-based -> 1-based: 6 and 21)
        first_range = refs[0]["range"]
        second_range = refs[1]["range"]
        assert first_range.startswith("11:6")  # 0-based 10:5 -> 1-based 11:6
        assert second_range.startswith("11:21")  # 0-based 10:20 -> 1-based 11:21


class TestGroupLocationsByFileSignature:
    """T-008: Contract tests for function signature."""

    def test_group_locations_by_file_signature(self) -> None:
        """Function has correct signature with records parameter."""
        from typing import Any

        from llm_lsp_cli.output.formatter import group_locations_by_file

        sig = inspect.signature(group_locations_by_file)
        params = list(sig.parameters.keys())
        assert "records" in params
        # Return type should be list[dict[str, Any]]
        return_str = str(sig.return_annotation)
        assert "list" in return_str


class TestLocationRecordAttributes:
    """T-009: Contract tests for LocationRecord attributes."""

    def test_location_record_has_required_attributes(self) -> None:
        """LocationRecord has file attribute and to_compact_dict method."""
        from llm_lsp_cli.output.formatter import (
            LocationRecord,
            Position,
            Range,
        )

        record = LocationRecord(
            file="src/main.py",
            range=Range(start=Position(0, 0), end=Position(0, 10)),
        )
        assert hasattr(record, "file")
        assert record.file == "src/main.py"
        compact = record.to_compact_dict()
        assert "range" in compact


class TestTextFormatGrouped:
    """T-004: TEXT format uses grouped structure."""

    def test_text_format_grouped_structure(self) -> None:
        """TEXT format renders file groups with compact single-line format."""
        from llm_lsp_cli.output.text_renderer import render_references_grouped

        grouped_data = [
            {"file": "src/main.py", "references": [{"range": "20:10-20:25"}]},
            {
                "file": "src/utils.py",
                "references": [
                    {"range": "5:10-5:25"},
                    {"range": "8:5-8:20"},
                ],
            },
        ]
        output = render_references_grouped(grouped_data)
        # Single line format: "<file>, ranges: [range1, range2...]"
        assert "src/main.py, ranges: [20:10-20:25]" in output
        assert "src/utils.py, ranges: [5:10-5:25, 8:5-8:20]" in output

    def test_text_format_empty_input(self) -> None:
        """Empty grouped data returns appropriate message."""
        from llm_lsp_cli.output.text_renderer import render_references_grouped

        output = render_references_grouped([])
        assert "No references found" in output


class TestJsonFormatGrouped:
    """T-005: JSON format uses grouped schema."""

    def test_json_format_grouped_schema(self) -> None:
        """JSON format has files array with file and references keys."""
        grouped_data = [
            {"file": "src/main.py", "references": [{"range": "20:10-20:25"}]},
        ]
        dispatcher = OutputDispatcher()
        output = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.JSON,
            items_key="references",
            _source="pyright",
            command="references",
        )
        data = json.loads(output)
        assert "_source" in data
        assert "command" in data
        assert "files" in data
        assert data["files"][0]["file"] == "src/main.py"
        assert data["files"][0]["references"][0]["range"] == "20:10-20:25"


class TestYamlFormatGrouped:
    """T-006: YAML format uses grouped schema."""

    def test_yaml_format_grouped_schema(self) -> None:
        """YAML format has files array with file and references keys."""
        grouped_data = [
            {"file": "src/main.py", "references": [{"range": "20:10-20:25"}]},
        ]
        dispatcher = OutputDispatcher()
        output = dispatcher.format_grouped(
            grouped_data,
            OutputFormat.YAML,
            items_key="references",
            _source="pyright",
        )
        data = yaml.safe_load(output)
        assert "files" in data
        assert data["files"][0]["file"] == "src/main.py"


class TestCsvFormatGrouped:
    """T-007: CSV format uses grouped ranges column."""

    def test_csv_format_grouped_ranges(self) -> None:
        """CSV format has file and ranges columns with bracketed range list."""
        grouped_data = [
            {
                "file": "src/utils.py",
                "references": [
                    {"range": "5:10-5:25"},
                    {"range": "8:5-8:20"},
                ],
            },
            {"file": "src/main.py", "references": [{"range": "20:10-20:25"}]},
        ]
        dispatcher = OutputDispatcher()
        output = dispatcher.format_references_csv(grouped_data)
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        # Each row has file and ranges columns
        assert rows[0]["file"] == "src/utils.py"
        assert rows[0]["ranges"] == "5:10-5:25|8:5-8:20"
        assert rows[1]["file"] == "src/main.py"
        assert rows[1]["ranges"] == "20:10-20:25"
