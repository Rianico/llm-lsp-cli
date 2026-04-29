"""Unit tests for compact formatter module."""

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import CompactFormatter, LocationRecord, Range, SymbolRecord
from llm_lsp_cli.utils import OutputFormat

# =============================================================================
# FIXTURES
# =============================================================================

# Sample LSP range dict for testing
SAMPLE_RANGE_DICT: dict[str, Any] = {
    "start": {"line": 0, "character": 0},
    "end": {"line": 50, "character": 0},
}

SAMPLE_RANGE_DICT_COMPLEX: dict[str, Any] = {
    "start": {"line": 10, "character": 5},
    "end": {"line": 20, "character": 15},
}

SAMPLE_POSITION_DICT: dict[str, Any] = {"line": 10, "character": 5}


# =============================================================================
# RED PHASE: Position and Range dataclass tests
# =============================================================================


class TestPositionDataclass:
    """RED: Tests for Position dataclass - FAILING until implemented."""

    def test_position_exists(self) -> None:
        """RED: Position dataclass exists and can be imported."""
        from llm_lsp_cli.output.formatter import Position

        assert Position is not None

    def test_position_creation(self) -> None:
        """RED: Position can be created with line and character."""
        from llm_lsp_cli.output.formatter import Position

        pos = Position(line=5, character=10)
        assert pos.line == 5
        assert pos.character == 10

    def test_position_equality(self) -> None:
        """RED: Two identical positions are equal."""
        from llm_lsp_cli.output.formatter import Position

        pos1 = Position(line=5, character=10)
        pos2 = Position(line=5, character=10)
        assert pos1 == pos2

    def test_position_inequality(self) -> None:
        """RED: Different positions are not equal."""
        from llm_lsp_cli.output.formatter import Position

        pos1 = Position(line=5, character=10)
        pos2 = Position(line=5, character=11)
        assert pos1 != pos2

    def test_position_to_dict(self) -> None:
        """RED: Position can be converted to dict."""
        from llm_lsp_cli.output.formatter import Position

        pos = Position(line=5, character=10)
        assert pos.to_dict() == {"line": 5, "character": 10}


class TestRangeDataclass:
    """RED: Tests for Range dataclass - FAILING until implemented."""

    def test_range_exists(self) -> None:
        """RED: Range dataclass exists and can be imported."""
        from llm_lsp_cli.output.formatter import Range

        assert Range is not None

    def test_range_creation_with_positions(self) -> None:
        """RED: Range can be created with Position objects."""
        from llm_lsp_cli.output.formatter import Position, Range

        start = Position(line=0, character=0)
        end = Position(line=10, character=0)
        rng = Range(start=start, end=end)
        assert rng.start == start
        assert rng.end == end

    def test_range_from_lsp_dict(self) -> None:
        """RED: Range can be created from LSP range dict."""
        from llm_lsp_cli.output.formatter import Range

        rng = Range.from_dict(SAMPLE_RANGE_DICT)
        assert rng.start.line == 0
        assert rng.start.character == 0
        assert rng.end.line == 50
        assert rng.end.character == 0

    def test_range_to_compact_string(self) -> None:
        """RED: Range can be formatted as compact string for TEXT/CSV."""
        from llm_lsp_cli.output.formatter import Position, Range

        start = Position(line=0, character=0)
        end = Position(line=50, character=0)
        rng = Range(start=start, end=end)
        assert rng.to_compact() == "1:1-51:1"

    def test_range_to_dict(self) -> None:
        """RED: Range can be converted to nested dict structure."""
        from llm_lsp_cli.output.formatter import Position, Range

        start = Position(line=0, character=0)
        end = Position(line=50, character=0)
        rng = Range(start=start, end=end)
        expected = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 50, "character": 0},
        }
        assert rng.to_dict() == expected

    def test_range_equality(self) -> None:
        """RED: Two identical ranges are equal."""
        from llm_lsp_cli.output.formatter import Position, Range

        rng1 = Range(start=Position(line=0, character=0), end=Position(line=10, character=5))
        rng2 = Range(start=Position(line=0, character=0), end=Position(line=10, character=5))
        assert rng1 == rng2


# =============================================================================
# RED PHASE: Updated Record class tests
# =============================================================================


class TestSymbolRecordWithRange:
    """RED: Tests for SymbolRecord with Range object - FAILING until implemented."""

    def test_symbol_record_range_is_range_object(self) -> None:
        """RED: SymbolRecord.range should be a Range object, not a string."""
        from llm_lsp_cli.output.formatter import Position, Range, SymbolRecord

        rng = Range(start=Position(line=0, character=0), end=Position(line=50, character=0))
        record = SymbolRecord(
            file="src/models.py",
            name="MyClass",
            kind=5,
            kind_name="Class",
            range=rng,
        )
        assert isinstance(record.range, Range)

    def test_symbol_record_has_selection_range_field(self) -> None:
        """RED: SymbolRecord should have optional selection_range field."""
        from llm_lsp_cli.output.formatter import Position, Range, SymbolRecord

        sel_rng = Range(start=Position(line=0, character=6), end=Position(line=0, character=13))
        record = SymbolRecord(
            file="src/models.py",
            name="MyClass",
            kind=5,
            kind_name="Class",
            range=Range(start=Position(line=0, character=0), end=Position(line=50, character=0)),
            selection_range=sel_rng,
        )
        assert record.selection_range == sel_rng

    def test_symbol_record_has_data_field(self) -> None:
        """RED: SymbolRecord should have optional data field for LSP extensions."""
        from llm_lsp_cli.output.formatter import Position, Range, SymbolRecord

        record = SymbolRecord(
            file="src/models.py",
            name="MyClass",
            kind=5,
            kind_name="Class",
            range=Range(start=Position(line=0, character=0), end=Position(line=50, character=0)),
            data={"serverId": "pyright"},
        )
        assert record.data == {"serverId": "pyright"}


class TestLocationRecordWithRange:
    """RED: Tests for LocationRecord with Range object - FAILING until implemented."""

    def test_location_record_range_is_range_object(self) -> None:
        """RED: LocationRecord.range should be a Range object, not a string."""
        from llm_lsp_cli.output.formatter import LocationRecord, Position, Range

        rng = Range(start=Position(line=10, character=4), end=Position(line=10, character=20))
        record = LocationRecord(file="src/main.py", range=rng)
        assert isinstance(record.range, Range)


class TestCallHierarchyRecordWithRange:
    """RED: Tests for CallHierarchyRecord with Range objects - FAILING until implemented."""

    def test_call_hierarchy_record_range_is_range_object(self) -> None:
        """RED: CallHierarchyRecord.range should be a Range object."""
        from llm_lsp_cli.output.formatter import CallHierarchyRecord, Position, Range

        rng = Range(start=Position(line=5, character=0), end=Position(line=10, character=0))
        record = CallHierarchyRecord(
            file="src/caller.py",
            name="caller_func",
            kind=12,
            kind_name="Function",
            range=rng,
        )
        assert isinstance(record.range, Range)

    def test_call_hierarchy_record_from_ranges_is_list_of_range(self) -> None:
        """RED: CallHierarchyRecord.from_ranges should be list[Range]."""
        from llm_lsp_cli.output.formatter import CallHierarchyRecord, Position, Range

        rng1 = Range(start=Position(line=5, character=4), end=Position(line=5, character=15))
        rng2 = Range(start=Position(line=10, character=8), end=Position(line=10, character=19))
        record = CallHierarchyRecord(
            file="src/caller.py",
            name="caller_func",
            kind=12,
            kind_name="Function",
            range=Range(start=Position(line=0, character=0), end=Position(line=20, character=0)),
            from_ranges=[rng1, rng2],
        )
        assert len(record.from_ranges) == 2
        assert all(isinstance(r, Range) for r in record.from_ranges)


# =============================================================================
# RED PHASE: Transformation method tests
# =============================================================================


class TestTransformSymbolsReturnsRange:
    """RED: Tests for transform_symbols returning Range objects."""

    def test_transform_symbols_range_is_range_object(self, temp_dir: Path) -> None:
        """RED: transform_symbols should create Range objects, not strings."""
        from llm_lsp_cli.output.formatter import Range

        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": SAMPLE_RANGE_DICT,
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        assert isinstance(records[0].range, Range)

    def test_transform_symbols_preserves_selection_range(self, temp_dir: Path) -> None:
        """RED: transform_symbols should preserve selectionRange as Range."""
        from llm_lsp_cli.output.formatter import Range

        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": SAMPLE_RANGE_DICT,
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 6},
                    "end": {"line": 0, "character": 13},
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        assert records[0].selection_range is not None
        assert isinstance(records[0].selection_range, Range)

    def test_transform_symbols_preserves_data_field(self, temp_dir: Path) -> None:
        """RED: transform_symbols should preserve data field from LSP."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": SAMPLE_RANGE_DICT,
                },
                "data": {"serverId": "pyright", "opaque": "value"},
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        assert records[0].data == {"serverId": "pyright", "opaque": "value"}


class TestTransformLocationsReturnsRange:
    """RED: Tests for transform_locations returning Range objects."""

    def test_transform_locations_range_is_range_object(self, temp_dir: Path) -> None:
        """RED: transform_locations should create Range objects."""
        from llm_lsp_cli.output.formatter import Range

        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 20},
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_locations(locations)
        assert isinstance(records[0].range, Range)


# =============================================================================
# RED PHASE: JSON/YAML serialization tests (nested Position structure)
# =============================================================================


class TestSymbolsToJsonCompactRange:
    """RED: Tests for JSON output with compact range strings (1-based)."""

    def test_json_symbol_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: JSON output must use compact range string format."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {
                        "start": {"line": 14, "character": 0},
                        "end": {"line": 145, "character": 29},
                    },
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(result)

        # range must be a compact string (1-based), NOT nested dict
        assert parsed[0]["range"] == "15:1-146:30"
        assert not isinstance(parsed[0]["range"], dict)

    def test_json_symbol_excludes_numeric_kind(self, temp_dir: Path) -> None:
        """RED: JSON output must include only kind_name, not numeric kind."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(result)

        # MUST have kind_name
        assert parsed[0]["kind_name"] == "Class"
        # MUST NOT have numeric kind
        assert "kind" not in parsed[0]

    def test_json_selection_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: JSON output must include selectionRange as compact string."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 6},
                    "end": {"line": 0, "character": 13},
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(result)

        # selection_range must be compact string
        assert parsed[0]["selection_range"] == "1:7-1:14"
        assert not isinstance(parsed[0]["selection_range"], dict)

    def test_json_unknown_kind_format(self, temp_dir: Path) -> None:
        """RED: Unknown kind displays as Unknown(N)."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "UnknownSymbol",
                "kind": 99,  # Unknown kind
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed[0]["kind_name"] == "Unknown(99)"
        assert "kind" not in parsed[0]


class TestSymbolsToYamlCompactRange:
    """RED: Tests for YAML output with compact range strings (1-based)."""

    def test_yaml_symbol_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: YAML output must use compact range string format."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {
                        "start": {"line": 14, "character": 0},
                        "end": {"line": 145, "character": 29},
                    },
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.YAML)
        parsed = yaml.safe_load(result)

        # range must be a compact string (1-based)
        assert parsed[0]["range"] == "15:1-146:30"
        assert not isinstance(parsed[0]["range"], dict)

    def test_yaml_symbol_excludes_numeric_kind(self, temp_dir: Path) -> None:
        """RED: YAML output must include only kind_name, not numeric kind."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.YAML)
        parsed = yaml.safe_load(result)

        # MUST have kind_name
        assert parsed[0]["kind_name"] == "Class"
        # MUST NOT have numeric kind
        assert "kind" not in parsed[0]


class TestLocationsToJsonCompactRange:
    """RED: Tests for locations JSON with compact range strings."""

    def test_json_location_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: Location JSON must use compact range format."""
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 20},
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(result)

        assert parsed[0]["range"] == "6:1-6:21"
        assert not isinstance(parsed[0]["range"], dict)


class TestLocationsToYamlCompactRange:
    """RED: Tests for locations YAML with compact range strings."""

    def test_yaml_location_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: Location YAML must use compact range format."""
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 20},
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.YAML)
        parsed = yaml.safe_load(result)

        assert parsed[0]["range"] == "6:1-6:21"


# =============================================================================
# RED PHASE: TEXT/CSV serialization tests (compact range format preserved)
# =============================================================================


class TestSymbolsToTextCompactRange:
    """RED: Tests for TEXT output with compact range strings."""

    def test_text_symbol_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: TEXT output must use compact range string format."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": SAMPLE_RANGE_DICT,
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)

        # TEXT format uses bare compact range (no brackets)
        assert "1:1-51:1" in result


class TestSymbolsToCsvCompactRange:
    """RED: Tests for CSV output with compact range strings."""

    def test_csv_symbol_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: CSV output must use compact range string format."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": SAMPLE_RANGE_DICT,
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.CSV)

        # CSV range column must be compact string
        assert "1:1-51:1" in result


class TestLocationsToTextCompactRange:
    """RED: Tests for locations TEXT with compact range."""

    def test_text_location_range_is_compact_string(self, temp_dir: Path) -> None:
        """RED: Location TEXT must use compact range format."""
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 20},
                },
            }
        ]
        (temp_dir / "src").mkdir()
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)

        # TEXT format uses bare compact range (no brackets)
        assert "6:1-6:21" in result


# =============================================================================
# EXISTING FIXTURES AND TESTS (preserved for backward compatibility)
# =============================================================================


@pytest.fixture
def sample_workspace_symbols(temp_dir: Path) -> list[dict[str, Any]]:
    """Sample workspace symbols for testing."""
    (temp_dir / "src").mkdir()
    return [
        {
            "name": "MyClass",
            "kind": 5,
            "location": {
                "uri": f"file://{temp_dir}/src/models.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
            },
            "detail": "class MyClass",
            "containerName": None,
        },
        {
            "name": "my_function",
            "kind": 12,
            "location": {
                "uri": f"file://{temp_dir}/src/utils.py",
                "range": {
                    "start": {"line": 10, "character": 0},
                    "end": {"line": 30, "character": 0},
                },
            },
            "detail": "def my_function(x: int) -> str",
        },
    ]


@pytest.fixture
def sample_locations(temp_dir: Path) -> list[dict[str, Any]]:
    """Sample locations for testing."""
    (temp_dir / "src").mkdir()
    return [
        {
            "uri": f"file://{temp_dir}/src/main.py",
            "range": {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 20}},
        },
        {
            "uri": f"file://{temp_dir}/src/utils.py",
            "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 24}},
        },
    ]


class TestCompactFormatterInit:
    """Tests for CompactFormatter initialization."""

    def test_init_stores_workspace(self, temp_dir: Path) -> None:
        """Verify workspace is stored and resolved."""
        formatter = CompactFormatter(str(temp_dir))
        assert formatter._workspace == temp_dir.resolve()

    def test_init_resolves_path(self, temp_dir: Path) -> None:
        """Verify workspace path is resolved to absolute."""
        formatter = CompactFormatter("./project")
        assert formatter._workspace.is_absolute()


class TestTransformSymbols:
    """Tests for transform_symbols method."""

    def test_transform_basic(
        self, sample_workspace_symbols: list[dict[str, Any]], temp_dir: Path
    ) -> None:
        """Verify basic transformation to SymbolRecord list."""
        from llm_lsp_cli.output.formatter import Range

        formatter = CompactFormatter(str(temp_dir))
        result = formatter.transform_symbols(sample_workspace_symbols)

        assert len(result) == 2
        assert isinstance(result[0], SymbolRecord)
        assert result[0].name == "MyClass"
        assert result[0].kind == 5
        assert result[0].file == "src/models.py"
        assert isinstance(result[0].range, Range)
        assert result[0].range.to_compact() == "1:1-51:1"

    def test_transform_includes_optional_fields(self, temp_dir: Path) -> None:
        """Verify optional field extraction."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "TestSymbol",
                "kind": 5,
                "location": {
                    "uri": "file:///project/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
                "detail": "class TestSymbol",
                "containerName": "TestContainer",
                "tags": [1, 2],
            },
        ]
        result = formatter.transform_symbols(symbols)

        assert len(result) == 1
        assert result[0].detail == "class TestSymbol"
        assert result[0].container == "TestContainer"
        assert result[0].tags == [1, 2]

    def test_transform_handles_missing_location(self, temp_dir: Path) -> None:
        """Handle document symbol format (no location wrapper)."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "X",
                "kind": 1,
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        result = formatter.transform_symbols(symbols)

        assert len(result) == 1
        assert result[0].name == "X"

    def test_transform_empty_list(self, temp_dir: Path) -> None:
        """Empty input handling."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.transform_symbols([])
        assert result == []

    def test_transform_normalizes_uri(self, temp_dir: Path) -> None:
        """URI normalization integration."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Utils",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/utils.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = formatter.transform_symbols(symbols)
        assert result[0].file == "src/utils.py"

    def test_transform_formats_range(self, temp_dir: Path) -> None:
        """Range formatting integration."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Func",
                "kind": 12,
                "location": {
                    "uri": "file:///project/src/utils.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            },
        ]
        result = formatter.transform_symbols(symbols)
        assert isinstance(result[0].range, Range)
        assert result[0].range.to_compact() == "1:1-51:1"


class TestTransformLocations:
    """Tests for transform_locations method."""

    def test_transform_locations_basic(
        self, sample_locations: list[dict[str, Any]], temp_dir: Path
    ) -> None:
        """Basic transformation to LocationRecord list."""
        from llm_lsp_cli.output.formatter import Range

        formatter = CompactFormatter(str(temp_dir))
        result = formatter.transform_locations(sample_locations)

        assert len(result) == 2
        assert isinstance(result[0], LocationRecord)
        assert result[0].file == "src/main.py"
        assert isinstance(result[0].range, Range)
        assert result[0].range.to_compact() == "6:1-6:21"

    def test_transform_locations_empty(self, temp_dir: Path) -> None:
        """Empty input."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.transform_locations([])
        assert result == []

    def test_transform_locations_normalizes_uri(self, temp_dir: Path) -> None:
        """URI normalization."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        result = formatter.transform_locations(locations)
        assert result[0].file == "src/main.py"


class TestSymbolsToText:
    """Tests for symbols TEXT output using dispatcher."""

    def test_text_single_symbol(self, temp_dir: Path) -> None:
        """Verify single symbol text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Sym1",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 9, "character": 0},
                    },
                },
            },
        ]
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        assert "src/file.py: Sym1 (Class) [1:1-10:1]" in result

    def test_text_multiple_symbols(self, temp_dir: Path) -> None:
        """Multiple symbols in text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Sym1",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 9, "character": 0},
                    },
                },
            },
            {
                "name": "Sym2",
                "kind": 12,
                "location": {
                    "uri": f"file://{temp_dir}/src/file.py",
                    "range": {
                        "start": {"line": 19, "character": 0},
                        "end": {"line": 29, "character": 0},
                    },
                },
            },
        ]
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        assert "src/file.py: Sym1 (Class) [1:1-10:1]" in result
        assert "src/file.py: Sym2 (Function) [20:1-30:1]" in result

    def test_text_multiple_files(self, temp_dir: Path) -> None:
        """Multiple files in text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "SymB",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/b_file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
            {
                "name": "SymA",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/a_file.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        # Both symbols should be present
        assert "src/a_file.py: SymA (Class) [1:1-2:1]" in result
        assert "src/b_file.py: SymB (Class) [1:1-2:1]" in result

    def test_text_includes_detail(self, temp_dir: Path) -> None:
        """Detail formatting with arrow."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyFunc",
                "kind": 12,
                "location": {
                    "uri": "file:///project/src/utils.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
                "detail": "def my_func() -> str",
            },
        ]
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        # Format: "file: name (kind) [range] -> detail"
        assert "src/utils.py: MyFunc (Function) [1:1-2:1] -> def my_func() -> str" in result

    def test_text_omits_none_detail(self, temp_dir: Path) -> None:
        """Conditional detail omission."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///project/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        records = formatter.transform_symbols(symbols)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        # Format: "file: name (kind) [range]" (no detail)
        assert "src/models.py: MyClass (Class) [1:1-2:1]" in result

    def test_text_empty_records(self, temp_dir: Path) -> None:
        """Empty list returns empty string."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.TEXT)
        assert result == ""


class TestSymbolsToJson:
    """Tests for symbols_to_json method."""

    def test_json_flat_array(self, temp_dir: Path) -> None:
        """Flat array structure with file_path at top level."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(
            formatter.transform_symbols(symbols),
            OutputFormat.JSON,
            _source="TestServer",
            file_path="src/test.py",
        )
        parsed = json.loads(result)
        assert parsed["_source"] == "TestServer"
        assert parsed["file"] == "src/test.py"
        assert len(parsed["items"]) == 1
        assert "file" not in parsed["items"][0]
        assert parsed["items"][0]["name"] == "Test"

    def test_json_omits_null_detail(self, temp_dir: Path) -> None:
        """Token optimization - omit null detail."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.JSON)
        parsed = json.loads(result)
        assert "detail" not in parsed[0]

    def test_json_omits_null_container(self, temp_dir: Path) -> None:
        """Token optimization - omit null container."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.JSON)
        parsed = json.loads(result)
        assert "container" not in parsed[0]

    def test_json_omits_empty_tags(self, temp_dir: Path) -> None:
        """Token optimization - omit empty tags."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.JSON)
        parsed = json.loads(result)
        assert "tags" not in parsed[0]

    def test_json_includes_present_fields(self, temp_dir: Path) -> None:
        """Full record serialization when fields present."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
                "detail": "detail text",
                "containerName": "container",
                "tags": [1],
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed[0]["detail"] == "detail text"
        assert parsed[0]["container"] == "container"
        assert parsed[0]["tags"] == [1]

    def test_json_empty_records(self, temp_dir: Path) -> None:
        """Empty array."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed == []


class TestSymbolsToYaml:
    """Tests for symbols_to_yaml method."""

    def test_yaml_flat_array(self, temp_dir: Path) -> None:
        """YAML structure with file_path at top level."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(
            formatter.transform_symbols(symbols),
            OutputFormat.YAML,
            _source="TestServer",
            file_path="src/test.py",
        )
        parsed = yaml.safe_load(result)
        assert parsed["_source"] == "TestServer"
        assert parsed["file"] == "src/test.py"
        assert len(parsed["items"]) == 1
        assert "file" not in parsed["items"][0]

    def test_yaml_omits_null_fields(self, temp_dir: Path) -> None:
        """Token optimization - omit null fields."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.YAML)
        parsed = yaml.safe_load(result)
        assert "detail" not in parsed[0]

    def test_yaml_preserves_unicode(self, temp_dir: Path) -> None:
        """Unicode handling."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "\u03b1\u03b2\u03b3_Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.YAML)
        assert "\u03b1\u03b2\u03b3_Test" in result

    def test_yaml_empty_records(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.YAML)
        parsed = yaml.safe_load(result)
        assert parsed == []


class TestSymbolsToCsv:
    """Tests for symbols_to_csv method."""

    def test_csv_headers(self, temp_dir: Path) -> None:
        """Header row verification."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.CSV)
        header = result.split("\n")[0]
        assert "file" in header
        assert "name" in header
        assert "kind_name" in header  # Uses kind_name, not numeric kind
        assert "range" in header

    def test_csv_single_record(self, temp_dir: Path) -> None:
        """Basic serialization."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.CSV)
        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row

    def test_csv_empty_records(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.CSV)
        assert result == ""

    def test_csv_tags_pipe_separated(self, temp_dir: Path) -> None:
        """Tag serialization with pipe separator."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
                "tags": [1, 2, 3],
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.CSV)
        assert "1|2|3" in result

    def test_csv_escapes_commas(self, temp_dir: Path) -> None:
        """CSV escaping for special characters."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/file,with,commas.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.CSV)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["file"] == "file,with,commas.py"

    def test_csv_uses_empty_string_for_none(self, temp_dir: Path) -> None:
        """Null handling in CSV."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": "file:///project/test.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 1, "character": 0},
                    },
                },
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_symbols(symbols), OutputFormat.CSV)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert rows[0]["detail"] == ""


class TestLocationsToText:
    """Tests for locations TEXT output using dispatcher."""

    def test_locations_text_single(self, temp_dir: Path) -> None:
        """Single location text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/file.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 9, "character": 0}},
            },
        ]
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        # Format: "file: range"
        assert "src/file.py: 1:1-10:1" in result

    def test_locations_text_multiple(self, temp_dir: Path) -> None:
        """Multiple locations text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/file.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 9, "character": 0}},
            },
            {
                "uri": f"file://{temp_dir}/src/file.py",
                "range": {
                    "start": {"line": 19, "character": 0},
                    "end": {"line": 29, "character": 0},
                },
            },
        ]
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        # Both ranges should be present
        assert "src/file.py: 1:1-10:1" in result
        assert "src/file.py: 20:1-30:1" in result

    def test_locations_text_empty(self, temp_dir: Path) -> None:
        """Empty list returns empty string."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.TEXT)
        assert result == ""

    def test_locations_multiple_files(self, temp_dir: Path) -> None:
        """Multiple files in text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/a.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
            {
                "uri": f"file://{temp_dir}/src/b.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        records = formatter.transform_locations(locations)
        result = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        # Both files should be present
        assert "src/a.py: 1:1-2:1" in result
        assert "src/b.py: 1:1-2:1" in result


class TestLocationsToJson:
    """Tests for locations_to_json method."""

    def test_locations_json_flat(self, temp_dir: Path) -> None:
        """Flat array."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/test.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_locations(locations), OutputFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["file"] == "src/test.py"

    def test_locations_json_empty(self, temp_dir: Path) -> None:
        """Empty array."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.JSON)
        parsed = json.loads(result)
        assert parsed == []


class TestLocationsToYaml:
    """Tests for locations_to_yaml method."""

    def test_locations_yaml_flat(self, temp_dir: Path) -> None:
        """YAML format."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/test.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_locations(locations), OutputFormat.YAML)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_locations_yaml_empty(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.YAML)
        parsed = yaml.safe_load(result)
        assert parsed == []


class TestLocationsToCsv:
    """Tests for locations_to_csv method."""

    def test_locations_csv_headers(self, temp_dir: Path) -> None:
        """Compact headers."""
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": "file:///project/test.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_locations(locations), OutputFormat.CSV)
        header = result.split("\n")[0]
        assert header == "file,range"

    def test_locations_csv_single(self, temp_dir: Path) -> None:
        """Basic serialization."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/test.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
            },
        ]
        result = OutputDispatcher().format_list(formatter.transform_locations(locations), OutputFormat.CSV)
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_locations_csv_empty(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = OutputDispatcher().format_list([], OutputFormat.CSV)
        assert result == ""
