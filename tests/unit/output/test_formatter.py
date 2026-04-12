"""Unit tests for compact formatter module."""

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from llm_lsp_cli.output.formatter import CompactFormatter, SymbolRecord, LocationRecord


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
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}},
            },
            "detail": "class MyClass",
            "containerName": None,
        },
        {
            "name": "my_function",
            "kind": 12,
            "location": {
                "uri": f"file://{temp_dir}/src/utils.py",
                "range": {"start": {"line": 10, "character": 0}, "end": {"line": 30, "character": 0}},
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
        from pathlib import Path
        formatter = CompactFormatter(str(temp_dir))
        assert formatter._workspace == temp_dir.resolve()

    def test_init_resolves_path(self, temp_dir: Path) -> None:
        """Verify workspace path is resolved to absolute."""
        formatter = CompactFormatter("./project")
        assert formatter._workspace.is_absolute()


class TestTransformSymbols:
    """Tests for transform_symbols method."""

    def test_transform_basic(self, sample_workspace_symbols: list[dict[str, Any]], temp_dir: Path) -> None:
        """Verify basic transformation to SymbolRecord list."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.transform_symbols(sample_workspace_symbols)

        assert len(result) == 2
        assert isinstance(result[0], SymbolRecord)
        assert result[0].name == "MyClass"
        assert result[0].kind == 5
        assert result[0].file == "src/models.py"
        assert result[0].range == "1:1-51:1"

    def test_transform_includes_optional_fields(self, temp_dir: Path) -> None:
        """Verify optional field extraction."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "TestSymbol",
                "kind": 5,
                "location": {
                    "uri": "file:///project/src/test.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
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
            {"name": "X", "kind": 1, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
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
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
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
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}},
                },
            },
        ]
        result = formatter.transform_symbols(symbols)
        assert result[0].range == "1:1-51:1"


class TestTransformLocations:
    """Tests for transform_locations method."""

    def test_transform_locations_basic(self, sample_locations: list[dict[str, Any]], temp_dir: Path) -> None:
        """Basic transformation to LocationRecord list."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.transform_locations(sample_locations)

        assert len(result) == 2
        assert isinstance(result[0], LocationRecord)
        assert result[0].file == "src/main.py"
        assert result[0].range == "6:1-6:21"

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
    """Tests for symbols_to_text method."""

    def test_text_file_grouping(self, temp_dir: Path) -> None:
        """Verify file grouping in text output."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Sym1",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/file.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 9, "character": 0}},
                },
            },
            {
                "name": "Sym2",
                "kind": 12,
                "location": {
                    "uri": f"file://{temp_dir}/src/file.py",
                    "range": {"start": {"line": 19, "character": 0}, "end": {"line": 29, "character": 0}},
                },
            },
        ]
        result = formatter.symbols_to_text(formatter.transform_symbols(symbols))
        assert "src/file.py:" in result
        assert "Sym1 (5) [1:1-10:1]" in result
        assert "Sym2 (12) [20:1-30:1]" in result

    def test_text_multiple_files(self, temp_dir: Path) -> None:
        """Multi-file grouping with sorted files."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "SymB",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/b_file.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
            },
            {
                "name": "SymA",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/a_file.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
            },
        ]
        result = formatter.symbols_to_text(formatter.transform_symbols(symbols))
        # Files should be sorted alphabetically
        a_file_pos = result.find("src/a_file.py:")
        b_file_pos = result.find("src/b_file.py:")
        assert a_file_pos < b_file_pos

    def test_text_includes_detail(self, temp_dir: Path) -> None:
        """Detail formatting with arrow."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyFunc",
                "kind": 12,
                "location": {
                    "uri": "file:///project/src/utils.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
                "detail": "def my_func() -> str",
            },
        ]
        result = formatter.symbols_to_text(formatter.transform_symbols(symbols))
        assert "MyFunc (12) [1:1-2:1] -> def my_func() -> str" in result

    def test_text_omits_none_detail(self, temp_dir: Path) -> None:
        """Conditional detail omission."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///project/src/models.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
            },
        ]
        result = formatter.symbols_to_text(formatter.transform_symbols(symbols))
        assert "MyClass (5) [1:1-2:1]" in result
        assert "->" not in result

    def test_text_empty_records(self, temp_dir: Path) -> None:
        """Empty state message."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.symbols_to_text([])
        assert result == "No symbols found."

    def test_text_sorted_by_file(self, temp_dir: Path) -> None:
        """Deterministic ordering by file path."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Sym1",
                "kind": 5,
                "location": {"uri": f"file://{temp_dir}/src/z.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
            {
                "name": "Sym2",
                "kind": 5,
                "location": {"uri": f"file://{temp_dir}/src/a.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_text(formatter.transform_symbols(symbols))
        # a.py should appear before z.py
        assert result.index("src/a.py:") < result.index("src/z.py:")


class TestSymbolsToJson:
    """Tests for symbols_to_json method."""

    def test_json_flat_array(self, temp_dir: Path) -> None:
        """Flat array structure."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/test.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
            },
        ]
        result = formatter.symbols_to_json(formatter.transform_symbols(symbols))
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert "file" in parsed[0]
        assert "name" in parsed[0]

    def test_json_omits_null_detail(self, temp_dir: Path) -> None:
        """Token optimization - omit null detail."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_json(formatter.transform_symbols(symbols))
        parsed = json.loads(result)
        assert "detail" not in parsed[0]

    def test_json_omits_null_container(self, temp_dir: Path) -> None:
        """Token optimization - omit null container."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_json(formatter.transform_symbols(symbols))
        parsed = json.loads(result)
        assert "container" not in parsed[0]

    def test_json_omits_empty_tags(self, temp_dir: Path) -> None:
        """Token optimization - omit empty tags."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_json(formatter.transform_symbols(symbols))
        parsed = json.loads(result)
        assert "tags" not in parsed[0]

    def test_json_includes_present_fields(self, temp_dir: Path) -> None:
        """Full record serialization when fields present."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
                "detail": "detail text",
                "containerName": "container",
                "tags": [1],
            },
        ]
        result = formatter.symbols_to_json(formatter.transform_symbols(symbols))
        parsed = json.loads(result)
        assert parsed[0]["detail"] == "detail text"
        assert parsed[0]["container"] == "container"
        assert parsed[0]["tags"] == [1]

    def test_json_empty_records(self, temp_dir: Path) -> None:
        """Empty array."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.symbols_to_json([])
        parsed = json.loads(result)
        assert parsed == []


class TestSymbolsToYaml:
    """Tests for symbols_to_yaml method."""

    def test_yaml_flat_array(self, temp_dir: Path) -> None:
        """YAML structure."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/test.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
            },
        ]
        result = formatter.symbols_to_yaml(formatter.transform_symbols(symbols))
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["file"] == "src/test.py"

    def test_yaml_omits_null_fields(self, temp_dir: Path) -> None:
        """Token optimization - omit null fields."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_yaml(formatter.transform_symbols(symbols))
        parsed = yaml.safe_load(result)
        assert "detail" not in parsed[0]

    def test_yaml_preserves_unicode(self, temp_dir: Path) -> None:
        """Unicode handling."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "\u03b1\u03b2\u03b3_Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_yaml(formatter.transform_symbols(symbols))
        assert "\u03b1\u03b2\u03b3_Test" in result

    def test_yaml_empty_records(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.symbols_to_yaml([])
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
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_csv(formatter.transform_symbols(symbols))
        header = result.split("\n")[0]
        assert "file" in header
        assert "name" in header
        assert "kind" in header
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
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}},
                },
            },
        ]
        result = formatter.symbols_to_csv(formatter.transform_symbols(symbols))
        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row

    def test_csv_empty_records(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.symbols_to_csv([])
        assert result == ""

    def test_csv_tags_pipe_separated(self, temp_dir: Path) -> None:
        """Tag serialization with pipe separator."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
                "tags": [1, 2, 3],
            },
        ]
        result = formatter.symbols_to_csv(formatter.transform_symbols(symbols))
        assert "1|2|3" in result

    def test_csv_escapes_commas(self, temp_dir: Path) -> None:
        """CSV escaping for special characters."""
        formatter = CompactFormatter(str(temp_dir))
        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "location": {"uri": f"file://{temp_dir}/file,with,commas.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_csv(formatter.transform_symbols(symbols))
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
                "location": {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            },
        ]
        result = formatter.symbols_to_csv(formatter.transform_symbols(symbols))
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert rows[0]["detail"] == ""


class TestLocationsToText:
    """Tests for locations_to_text method."""

    def test_locations_text_grouping(self, temp_dir: Path) -> None:
        """File grouping for locations."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {
                "uri": f"file://{temp_dir}/src/file.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 9, "character": 0}},
            },
            {
                "uri": f"file://{temp_dir}/src/file.py",
                "range": {"start": {"line": 19, "character": 0}, "end": {"line": 29, "character": 0}},
            },
        ]
        result = formatter.locations_to_text(formatter.transform_locations(locations))
        assert "src/file.py:" in result
        assert "[1:1-10:1]" in result
        assert "[20:1-30:1]" in result

    def test_locations_text_empty(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.locations_to_text([])
        assert result == "No locations found."

    def test_locations_multiple_files(self, temp_dir: Path) -> None:
        """Multi-file format."""
        (temp_dir / "src").mkdir()
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {"uri": f"file://{temp_dir}/src/a.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
            {"uri": f"file://{temp_dir}/src/b.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
        ]
        result = formatter.locations_to_text(formatter.transform_locations(locations))
        # Should have blank line between files
        assert "\n\n" in result


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
        result = formatter.locations_to_json(formatter.transform_locations(locations))
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["file"] == "src/test.py"

    def test_locations_json_empty(self, temp_dir: Path) -> None:
        """Empty array."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.locations_to_json([])
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
        result = formatter.locations_to_yaml(formatter.transform_locations(locations))
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_locations_yaml_empty(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.locations_to_yaml([])
        parsed = yaml.safe_load(result)
        assert parsed == []


class TestLocationsToCsv:
    """Tests for locations_to_csv method."""

    def test_locations_csv_headers(self, temp_dir: Path) -> None:
        """Compact headers."""
        formatter = CompactFormatter(str(temp_dir))
        locations = [
            {"uri": "file:///project/test.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 1, "character": 0}}},
        ]
        result = formatter.locations_to_csv(formatter.transform_locations(locations))
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
        result = formatter.locations_to_csv(formatter.transform_locations(locations))
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_locations_csv_empty(self, temp_dir: Path) -> None:
        """Empty state."""
        formatter = CompactFormatter(str(temp_dir))
        result = formatter.locations_to_csv([])
        assert result == ""
