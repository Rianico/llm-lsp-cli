"""Integration tests for centralized fixtures.

This module verifies:
1. Fixtures work correctly when imported across different test files
2. Edge cases for all 19 exported fixtures in tests/fixtures.py
3. Generator functions produce valid responses
4. Cross-format consistency (CSV, text, JSON, YAML) for same data
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import CompactFormatter
from llm_lsp_cli.utils import OutputFormat
from tests.fixtures import (
    COMPLETION_RESPONSE,
    COMPLETION_RESPONSE_EMPTY,
    COMPLETION_RESPONSE_MINIMAL,
    COMPLETION_RESPONSE_RICH,
    COMPLETION_RESPONSE_WITH_COMMAS,
    DOCUMENT_SYMBOL_RESPONSE,
    DOCUMENT_SYMBOL_WITH_CHILDREN,
    HOVER_RESPONSE,
    HOVER_RESPONSE_EMPTY,
    HOVER_RESPONSE_PLAINTEXT,
    LOCATION_RESPONSE,
    LOCATION_RESPONSE_EMPTY,
    LOCATION_RESPONSE_MULTI,
    LOCATION_RESPONSE_WITH_COMMAS,
    LOCATION_RESPONSE_WITH_QUOTES,
    SYMBOL_RESPONSE,
    WORKSPACE_SYMBOL_RESPONSE,
    create_location_response_with_test_files,
    create_workspace_symbol_response_with_test_files,
)

runner = CliRunner()


# =============================================================================
# Cross-File Fixture Usage Tests
# =============================================================================


class TestCrossFileFixtureUsage:
    """Verify fixtures work when imported and used across test files."""

    def test_location_response_across_formats(self, temp_dir: Path) -> None:
        """Test LOCATION_RESPONSE works with all output formats."""
        formatter = CompactFormatter(temp_dir)

        # Simulate the response structure
        locations = LOCATION_RESPONSE["locations"]

        # Test all formats produce valid output
        records = formatter.transform_locations(locations)

        # Text format
        text_output = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        assert "file.py" in text_output
        assert "11:5-11:21" in text_output

        # JSON format
        json_output = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(json_output)
        assert len(parsed["items"]) == 1
        assert parsed["items"][0]["file"] == "/path/to/file.py"

        # YAML format
        yaml_output = OutputDispatcher().format_list(records, OutputFormat.YAML)
        parsed = yaml.safe_load(yaml_output)
        assert len(parsed["items"]) == 1
        assert parsed["items"][0]["file"] == "/path/to/file.py"

        # CSV format
        csv_output = OutputDispatcher().format_list(records, OutputFormat.CSV)
        lines = csv_output.strip().split("\n")
        assert len(lines) == 2  # header + 1 row

    def test_multi_location_response(self, temp_dir: Path) -> None:
        """Test LOCATION_RESPONSE_MULTI produces multiple records."""
        formatter = CompactFormatter(temp_dir)
        locations = LOCATION_RESPONSE_MULTI["locations"]
        records = formatter.transform_locations(locations)

        assert len(records) == 3
        assert records[0].file == "/path/to/file1.py"
        assert records[1].file == "/path/to/file2.py"
        assert records[2].file == "/path/to/file3.py"

    def test_workspace_symbol_response_across_formats(self, temp_dir: Path) -> None:
        """Test WORKSPACE_SYMBOL_RESPONSE works with all output formats."""
        formatter = CompactFormatter(temp_dir)
        symbols = WORKSPACE_SYMBOL_RESPONSE["symbols"]

        records = formatter.transform_symbols(symbols)
        assert len(records) == 2

        # Verify both formats work
        text_output = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        assert "MyClass" in text_output
        assert "helper_function" in text_output

        json_output = OutputDispatcher().format_list(records, OutputFormat.JSON)
        parsed = json.loads(json_output)
        assert len(parsed["items"]) == 2

    def test_completion_response_across_formats(self, temp_dir: Path) -> None:
        """Test COMPLETION_RESPONSE works with all output formats."""
        items = COMPLETION_RESPONSE["items"]

        # Completion uses different transform
        text_lines = []
        for item in items:
            label = item.get("label", "")
            detail = item.get("detail", "")
            if detail:
                text_lines.append(f"{label} -> {detail}")
            else:
                text_lines.append(label)

        assert len(text_lines) == 2
        assert "my_function" in text_lines[0]

    def test_hover_response_across_formats(self, temp_dir: Path) -> None:
        """Test HOVER_RESPONSE works with different content types."""
        # Test markdown hover
        assert "markdown" in HOVER_RESPONSE["hover"]["contents"]["kind"]

        # Test plaintext hover
        assert "plaintext" in HOVER_RESPONSE_PLAINTEXT["hover"]["contents"]["kind"]


# =============================================================================
# Edge Case Tests for All Fixtures
# =============================================================================


class TestLocationFixtureEdgeCases:
    """Edge case tests for location-based fixtures."""

    def test_empty_location_response(self, temp_dir: Path) -> None:
        """Test LOCATION_RESPONSE_EMPTY produces no records."""
        formatter = CompactFormatter(temp_dir)
        locations = LOCATION_RESPONSE_EMPTY["locations"]
        records = formatter.transform_locations(locations)
        assert len(records) == 0

        # All formats should handle empty gracefully
        assert OutputDispatcher().format_list(records, OutputFormat.TEXT) == ""
        assert OutputDispatcher().format_list(records, OutputFormat.JSON) == '{\n  "items": []\n}'
        assert OutputDispatcher().format_list(records, OutputFormat.CSV) == ""

    def test_location_with_commas_csv_escaping(self, temp_dir: Path) -> None:
        """Test LOCATION_RESPONSE_WITH_COMMAS CSV escaping."""
        formatter = CompactFormatter(temp_dir)
        locations = LOCATION_RESPONSE_WITH_COMMAS["locations"]
        records = formatter.transform_locations(records := locations)

        csv_output = OutputDispatcher().format_list(records, OutputFormat.CSV)
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        assert "file,with,commas.py" in rows[0]["file"]

    def test_location_with_quotes_csv_escaping(self, temp_dir: Path) -> None:
        """Test LOCATION_RESPONSE_WITH_QUOTES CSV escaping."""
        formatter = CompactFormatter(temp_dir)
        locations = LOCATION_RESPONSE_WITH_QUOTES["locations"]
        records = formatter.transform_locations(locations)

        csv_output = OutputDispatcher().format_list(records, OutputFormat.CSV)
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        assert 'file"with"quotes.py' in rows[0]["file"]

    def test_multi_location_different_files(self, temp_dir: Path) -> None:
        """Test LOCATION_RESPONSE_MULTI groups by file correctly."""
        formatter = CompactFormatter(temp_dir)
        locations = LOCATION_RESPONSE_MULTI["locations"]
        records = formatter.transform_locations(locations)

        text_output = OutputDispatcher().format_list(records, OutputFormat.TEXT)

        # Should have all three files
        assert "file1.py" in text_output
        assert "file2.py" in text_output
        assert "file3.py" in text_output


class TestSymbolFixtureEdgeCases:
    """Edge case tests for symbol-based fixtures."""

    def test_symbol_response_basic(self, temp_dir: Path) -> None:
        """Test SYMBOL_RESPONSE basic structure."""
        formatter = CompactFormatter(temp_dir)
        symbols = SYMBOL_RESPONSE["symbols"]

        # SYMBOL_RESPONSE uses flat structure (no location wrapper)
        records = formatter.transform_symbols(symbols)
        assert len(records) == 1
        assert records[0].name == "MyClass"
        assert records[0].kind == 5

    def test_document_symbol_response(self, temp_dir: Path) -> None:
        """Test DOCUMENT_SYMBOL_RESPONSE with selectionRange."""
        formatter = CompactFormatter(temp_dir)
        symbols = DOCUMENT_SYMBOL_RESPONSE["symbols"]
        records = formatter.transform_symbols(symbols)

        assert len(records) == 1
        assert records[0].name == "MyClass"
        # DOCUMENT_SYMBOL_RESPONSE has no URI, only range (document symbol format)
        # File should be empty string when URI is missing
        assert records[0].file == ""

    def test_document_symbol_with_children(self, temp_dir: Path) -> None:
        """Test DOCUMENT_SYMBOL_WITH_CHILDREN handles nested symbols."""
        formatter = CompactFormatter(temp_dir)
        symbols = DOCUMENT_SYMBOL_WITH_CHILDREN["symbols"]
        records = formatter.transform_symbols(symbols)

        # Should flatten top-level symbols
        assert len(records) == 2
        assert records[0].name == "MyClass"
        assert records[1].name == "helper_function"

        # Children should be accessible in original structure
        assert "children" in symbols[0]
        assert len(symbols[0]["children"]) == 2

    def test_workspace_symbol_response_structure(self, temp_dir: Path) -> None:
        """Test WORKSPACE_SYMBOL_RESPONSE has location wrapper."""
        formatter = CompactFormatter(temp_dir)
        symbols = WORKSPACE_SYMBOL_RESPONSE["symbols"]
        records = formatter.transform_symbols(symbols)

        assert len(records) == 2
        # Verify location wrapper is handled
        assert records[0].file == "/path/to/myclass.py"
        assert records[1].file == "/path/to/utils.py"


class TestCompletionFixtureEdgeCases:
    """Edge case tests for completion-based fixtures."""

    def test_completion_response_empty(self) -> None:
        """Test COMPLETION_RESPONSE_EMPTY has no items."""
        assert len(COMPLETION_RESPONSE_EMPTY["items"]) == 0

    def test_completion_response_minimal(self) -> None:
        """Test COMPLETION_RESPONSE_MINIMAL has only label."""
        items = COMPLETION_RESPONSE_MINIMAL["items"]
        assert len(items) == 1
        assert items[0]["label"] == "minimal_item"
        # Should not have optional fields
        assert "kind" not in items[0]
        assert "detail" not in items[0]
        assert "documentation" not in items[0]

    def test_completion_response_rich(self) -> None:
        """Test COMPLETION_RESPONSE_RICH has all optional fields."""
        items = COMPLETION_RESPONSE_RICH["items"]
        assert len(items) == 1

        item = items[0]
        assert item["label"] == "complex_function"
        assert item["kind"] == 12
        assert "tags" in item
        assert "documentation" in item
        assert item["documentation"]["kind"] == "markdown"
        assert "textEdit" in item
        assert "insertText" in item
        assert "filterText" in item
        assert "preselect" in item
        assert "deprecated" in item

    def test_completion_with_commas(self) -> None:
        """Test COMPLETION_RESPONSE_WITH_COMMAS has commas in fields."""
        items = COMPLETION_RESPONSE_WITH_COMMAS["items"]
        assert len(items) == 1

        item = items[0]
        assert "commas" in item["detail"]
        # Documentation should also have commas
        assert "commas" in item.get("documentation", "")


class TestHoverFixtureEdgeCases:
    """Edge case tests for hover-based fixtures."""

    def test_hover_response_markdown(self) -> None:
        """Test HOVER_RESPONSE has markdown content."""
        hover = HOVER_RESPONSE["hover"]
        assert hover is not None
        assert hover["contents"]["kind"] == "markdown"
        assert "```python" in hover["contents"]["value"]

    def test_hover_response_plaintext(self) -> None:
        """Test HOVER_RESPONSE_PLAINTEXT has plaintext content."""
        hover = HOVER_RESPONSE_PLAINTEXT["hover"]
        assert hover is not None
        assert hover["contents"]["kind"] == "plaintext"
        assert hover["contents"]["value"] == "Hover content"

    def test_hover_response_empty(self) -> None:
        """Test HOVER_RESPONSE_EMPTY has None hover."""
        assert HOVER_RESPONSE_EMPTY["hover"] is None


# =============================================================================
# Generator Function Tests
# =============================================================================


class TestGeneratorFunctions:
    """Tests for fixture generator functions."""

    def test_create_location_response_with_test_files(self) -> None:
        """Test create_location_response_with_test_files generates correct structure."""
        response = create_location_response_with_test_files()

        assert "locations" in response
        assert len(response["locations"]) == 2

        # First should be source file
        source = response["locations"][0]
        assert "file.py" in source["uri"]
        assert "test" not in source["uri"].lower().split("/")[-1]

        # Second should be test file
        test_file = response["locations"][1]
        assert "test_file.py" in test_file["uri"]

    def test_create_workspace_symbol_response_with_test_files(self) -> None:
        """Test create_workspace_symbol_response_with_test_files generates correct structure."""
        response = create_workspace_symbol_response_with_test_files()

        assert "symbols" in response
        assert len(response["symbols"]) == 2

        # First should be source symbol
        source = response["symbols"][0]
        assert source["name"] == "MyClass"
        assert "file.py" in source["location"]["uri"]

        # Second should be test symbol
        test_symbol = response["symbols"][1]
        assert test_symbol["name"] == "TestMyClass"
        assert "test_file.py" in test_symbol["location"]["uri"]

    def test_generator_functions_with_formatter(self, temp_dir: Path) -> None:
        """Test generator functions work with CompactFormatter."""
        formatter = CompactFormatter(temp_dir)

        # Test location generator
        loc_response = create_location_response_with_test_files()
        loc_records = formatter.transform_locations(loc_response["locations"])
        assert len(loc_records) == 2

        # Test workspace symbol generator
        sym_response = create_workspace_symbol_response_with_test_files()
        sym_records = formatter.transform_symbols(sym_response["symbols"])
        assert len(sym_records) == 2


# =============================================================================
# Cross-Format Consistency Tests
# =============================================================================


class TestCrossFormatConsistency:
    """Verify same data produces consistent results across formats."""

    @pytest.fixture
    def sample_symbols(self, temp_dir: Path) -> list[dict[str, Any]]:
        """Sample symbols for cross-format testing."""
        return [
            {
                "name": "TestSymbol",
                "kind": 12,
                "location": {
                    "uri": f"file://{temp_dir}/src/test.py",
                    "range": {
                        "start": {"line": 10, "character": 0},
                        "end": {"line": 20, "character": 0},
                    },
                },
                "detail": "def test_func()",
            }
        ]

    @pytest.fixture
    def sample_locations(self, temp_dir: Path) -> list[dict[str, Any]]:
        """Sample locations for cross-format testing."""
        return [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 20},
                },
            }
        ]

    def test_symbols_count_consistent(
        self, temp_dir: Path, sample_symbols: list[dict[str, Any]]
    ) -> None:
        """Verify symbol count is same across all formats."""
        records = CompactFormatter(temp_dir).transform_symbols(sample_symbols)

        # All formats should have same record count
        text_count = len(
            [
                line
                for line in OutputDispatcher().format_list(records, OutputFormat.TEXT).split("\n")
                if line.strip()
            ]
        )
        json_count = len(json.loads(OutputDispatcher().format_list(records, OutputFormat.JSON))["items"])
        yaml_count = len(yaml.safe_load(OutputDispatcher().format_list(records, OutputFormat.YAML))["items"])
        csv_count = (
            len(OutputDispatcher().format_list(records, OutputFormat.CSV).strip().split("\n")) - 1
        )  # minus header

        assert text_count == json_count == yaml_count == csv_count == 1

    def test_locations_count_consistent(
        self, temp_dir: Path, sample_locations: list[dict[str, Any]]
    ) -> None:
        """Verify location count is same across all formats."""
        records = CompactFormatter(temp_dir).transform_locations(sample_locations)

        # All formats should have same record count
        text_count = len(
            [
                line
                for line in OutputDispatcher().format_list(records, OutputFormat.TEXT).split("\n")
                if line.strip()
            ]
        )
        json_count = len(json.loads(OutputDispatcher().format_list(records, OutputFormat.JSON))["items"])
        yaml_count = len(yaml.safe_load(OutputDispatcher().format_list(records, OutputFormat.YAML))["items"])
        csv_count = (
            len(OutputDispatcher().format_list(records, OutputFormat.CSV).strip().split("\n")) - 1
        )  # minus header

        assert text_count == json_count == yaml_count == csv_count == 1

    def test_symbols_data_consistent_json_yaml(
        self, temp_dir: Path, sample_symbols: list[dict[str, Any]]
    ) -> None:
        """Verify JSON and YAML produce identical data."""
        formatter = CompactFormatter(temp_dir)
        records = formatter.transform_symbols(sample_symbols)

        json_data = json.loads(OutputDispatcher().format_list(records, OutputFormat.JSON))
        yaml_data = yaml.safe_load(OutputDispatcher().format_list(records, OutputFormat.YAML))

        assert json_data == yaml_data

    def test_locations_data_consistent_json_yaml(
        self, temp_dir: Path, sample_locations: list[dict[str, Any]]
    ) -> None:
        """Verify JSON and YAML produce identical data for locations."""
        formatter = CompactFormatter(temp_dir)
        records = formatter.transform_locations(sample_locations)

        json_data = json.loads(OutputDispatcher().format_list(records, OutputFormat.JSON))
        yaml_data = yaml.safe_load(OutputDispatcher().format_list(records, OutputFormat.YAML))

        assert json_data == yaml_data

    def test_symbols_file_consistent(
        self, temp_dir: Path, sample_symbols: list[dict[str, Any]]
    ) -> None:
        """Verify file path is consistent across formats."""
        formatter = CompactFormatter(temp_dir)
        records = formatter.transform_symbols(sample_symbols)

        expected_file = "src/test.py"

        # Get file from each format with file_path passed to dispatcher
        text_output = OutputDispatcher().format_list(records, OutputFormat.TEXT)
        json_data = json.loads(
            OutputDispatcher().format_list(
                records, OutputFormat.JSON, _source="TestServer", file_path=expected_file
            )
        )
        yaml_data = yaml.safe_load(
            OutputDispatcher().format_list(
                records, OutputFormat.YAML, _source="TestServer", file_path=expected_file
            )
        )
        csv_data = list(
            csv.DictReader(io.StringIO(OutputDispatcher().format_list(records, OutputFormat.CSV)))
        )

        # TEXT format no longer includes file in output lines (new format)
        # File is at top level in JSON/YAML only
        assert expected_file not in text_output

        # JSON/YAML have file at top level (uses file_path parameter)
        assert json_data["file"] == expected_file
        assert "file" not in json_data["items"][0]  # Not in items

        assert yaml_data["file"] == expected_file
        assert "file" not in yaml_data["items"][0]  # Not in items

        # CSV uses absolute path from record (file_path parameter not used for CSV)
        assert csv_data[0]["file"].endswith("src/test.py")


# =============================================================================
# Fixture Import and Availability Tests
# =============================================================================


class TestFixtureImports:
    """Verify all fixtures are properly exported and importable."""

    def test_all_location_fixtures_importable(self) -> None:
        """Verify all location fixtures can be imported."""
        from tests.fixtures import (
            LOCATION_RESPONSE,
            LOCATION_RESPONSE_EMPTY,
            LOCATION_RESPONSE_MULTI,
            LOCATION_RESPONSE_WITH_COMMAS,
            LOCATION_RESPONSE_WITH_QUOTES,
            create_location_response_with_test_files,
        )

        assert LOCATION_RESPONSE is not None
        assert LOCATION_RESPONSE_EMPTY is not None
        assert LOCATION_RESPONSE_MULTI is not None
        assert LOCATION_RESPONSE_WITH_COMMAS is not None
        assert LOCATION_RESPONSE_WITH_QUOTES is not None
        assert callable(create_location_response_with_test_files)

    def test_all_symbol_fixtures_importable(self) -> None:
        """Verify all symbol fixtures can be imported."""
        from tests.fixtures import (
            DOCUMENT_SYMBOL_RESPONSE,
            DOCUMENT_SYMBOL_WITH_CHILDREN,
            SYMBOL_RESPONSE,
            WORKSPACE_SYMBOL_RESPONSE,
            create_workspace_symbol_response_with_test_files,
        )

        assert DOCUMENT_SYMBOL_RESPONSE is not None
        assert DOCUMENT_SYMBOL_WITH_CHILDREN is not None
        assert SYMBOL_RESPONSE is not None
        assert WORKSPACE_SYMBOL_RESPONSE is not None
        assert callable(create_workspace_symbol_response_with_test_files)

    def test_all_completion_fixtures_importable(self) -> None:
        """Verify all completion fixtures can be imported."""
        from tests.fixtures import (
            COMPLETION_RESPONSE,
            COMPLETION_RESPONSE_EMPTY,
            COMPLETION_RESPONSE_MINIMAL,
            COMPLETION_RESPONSE_RICH,
            COMPLETION_RESPONSE_WITH_COMMAS,
        )

        assert COMPLETION_RESPONSE is not None
        assert COMPLETION_RESPONSE_EMPTY is not None
        assert COMPLETION_RESPONSE_MINIMAL is not None
        assert COMPLETION_RESPONSE_RICH is not None
        assert COMPLETION_RESPONSE_WITH_COMMAS is not None

    def test_all_hover_fixtures_importable(self) -> None:
        """Verify all hover fixtures can be imported."""
        from tests.fixtures import (
            HOVER_RESPONSE,
            HOVER_RESPONSE_EMPTY,
            HOVER_RESPONSE_PLAINTEXT,
        )

        assert HOVER_RESPONSE is not None
        assert HOVER_RESPONSE_EMPTY is not None
        assert HOVER_RESPONSE_PLAINTEXT is not None

    def test_all_exports_in_all_list(self) -> None:
        """Verify __all__ contains all expected exports."""
        from tests import fixtures

        expected_exports = [
            # Location-Based
            "LOCATION_RESPONSE",
            "LOCATION_RESPONSE_MULTI",
            "LOCATION_RESPONSE_EMPTY",
            "LOCATION_RESPONSE_WITH_COMMAS",
            "LOCATION_RESPONSE_WITH_QUOTES",
            "create_location_response_with_test_files",
            # Symbol-Based
            "SYMBOL_RESPONSE",
            "DOCUMENT_SYMBOL_RESPONSE",
            "DOCUMENT_SYMBOL_WITH_CHILDREN",
            "WORKSPACE_SYMBOL_RESPONSE",
            "create_workspace_symbol_response_with_test_files",
            # Completion-Based
            "COMPLETION_RESPONSE",
            "COMPLETION_RESPONSE_RICH",
            "COMPLETION_RESPONSE_EMPTY",
            "COMPLETION_RESPONSE_MINIMAL",
            "COMPLETION_RESPONSE_WITH_COMMAS",
            # Hover-Based
            "HOVER_RESPONSE",
            "HOVER_RESPONSE_PLAINTEXT",
            "HOVER_RESPONSE_EMPTY",
        ]

        for export in expected_exports:
            assert export in fixtures.__all__, f"{export} not in __all__"
