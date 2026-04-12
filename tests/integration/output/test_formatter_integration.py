"""Integration tests for compact output formatter with full command workflows."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from llm_lsp_cli.output.formatter import CompactFormatter, LocationRecord, SymbolRecord


class TestWorkspaceSymbolWorkflow:
    """Integration tests for workspace_symbol command output."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def workspace_symbols_response(self, temp_dir: Path) -> list[dict[str, Any]]:
        """Simulate a workspace/symbol LSP response."""
        return [
            {
                "name": "MyClass",
                "kind": 5,  # Class
                "location": {
                    "uri": f"file://{temp_dir}/src/models.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}},
                },
                "detail": "class MyClass",
                "containerName": None,
                "tags": [],
            },
            {
                "name": "my_function",
                "kind": 12,  # Function
                "location": {
                    "uri": f"file://{temp_dir}/src/utils.py",
                    "range": {"start": {"line": 10, "character": 0}, "end": {"line": 30, "character": 0}},
                },
                "detail": "def my_function(x: int) -> str",
            },
            {
                "name": "TestClass",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/tests/test_models.py",
                    "range": {"start": {"line": 5, "character": 0}, "end": {"line": 25, "character": 0}},
                },
                "detail": "class TestClass",
                "containerName": None,
            },
        ]

    def test_workflow_text_output(self, formatter: CompactFormatter, workspace_symbols_response: list[dict[str, Any]]) -> None:
        """Test complete text output workflow."""
        records = formatter.transform_symbols(workspace_symbols_response)
        output = formatter.symbols_to_text(records)

        # Verify file grouping
        assert "src/models.py:" in output
        assert "src/utils.py:" in output
        assert "tests/test_models.py:" in output

        # Verify symbol formatting
        assert "MyClass (5) [1:1-51:1]" in output
        assert "my_function (12) [11:1-31:1] -> def my_function(x: int) -> str" in output
        assert "TestClass (5) [6:1-26:1]" in output

    def test_workflow_json_output(self, formatter: CompactFormatter, workspace_symbols_response: list[dict[str, Any]]) -> None:
        """Test complete JSON output workflow."""
        records = formatter.transform_symbols(workspace_symbols_response)
        output = formatter.symbols_to_json(records)
        parsed = json.loads(output)

        assert isinstance(parsed, list)
        assert len(parsed) == 3

        # Verify structure
        for item in parsed:
            assert "file" in item
            assert "name" in item
            assert "kind" in item
            assert "range" in item

        # Verify null omission
        for item in parsed:
            assert "container" not in item  # All were None

    def test_workflow_yaml_output(self, formatter: CompactFormatter, workspace_symbols_response: list[dict[str, Any]]) -> None:
        """Test complete YAML output workflow."""
        records = formatter.transform_symbols(workspace_symbols_response)
        output = formatter.symbols_to_yaml(records)
        parsed = yaml.safe_load(output)

        assert isinstance(parsed, list)
        assert len(parsed) == 3

        # Verify a symbol with detail
        func_item = next((item for item in parsed if item["name"] == "my_function"), None)
        assert func_item is not None
        assert func_item["detail"] == "def my_function(x: int) -> str"

    def test_workflow_csv_output(self, formatter: CompactFormatter, workspace_symbols_response: list[dict[str, Any]]) -> None:
        """Test complete CSV output workflow."""
        records = formatter.transform_symbols(workspace_symbols_response)
        output = formatter.symbols_to_csv(records)
        lines = output.strip().split("\n")

        # Header + 3 data rows
        assert len(lines) == 4

        # Verify header
        assert lines[0] == "file,name,kind,range,detail,container,tags"

        # Verify data rows have correct column count
        for line in lines[1:]:
            assert len(line.split(",")) == 7

    def test_workflow_filter_test_symbols(self, formatter: CompactFormatter, workspace_symbols_response: list[dict[str, Any]]) -> None:
        """Test filtering test file symbols."""
        records = formatter.transform_symbols(workspace_symbols_response)

        # Filter out test symbols
        filtered = [r for r in records if not r.file.startswith("tests/")]

        assert len(filtered) == 2
        assert all(not r.file.startswith("tests/") for r in filtered)


class TestDocumentSymbolWorkflow:
    """Integration tests for document_symbol command output."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def document_symbols_response(self, temp_dir: Path) -> list[dict[str, Any]]:
        """Simulate a textDocument/documentSymbol response."""
        return [
            {
                "name": "MyClass",
                "kind": 5,
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}},
                "selectionRange": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 9}},
                "detail": "class MyClass",
                "children": [
                    {
                        "name": "__init__",
                        "kind": 6,  # Method
                        "range": {"start": {"line": 1, "character": 4}, "end": {"line": 10, "character": 0}},
                        "detail": "def __init__(self, name: str)",
                    },
                    {
                        "name": "greet",
                        "kind": 6,
                        "range": {"start": {"line": 11, "character": 4}, "end": {"line": 20, "character": 0}},
                        "detail": "def greet(self) -> str",
                    },
                ],
            },
            {
                "name": "helper_function",
                "kind": 12,
                "range": {"start": {"line": 52, "character": 0}, "end": {"line": 70, "character": 0}},
                "detail": "def helper_function(x: int) -> int",
                "children": [],
            },
        ]

    def test_workflow_flat_symbols(self, formatter: CompactFormatter, document_symbols_response: list[dict[str, Any]]) -> None:
        """Test flat symbol output (ignoring children)."""
        # For compact output, we flatten - just process top-level symbols
        records = formatter.transform_symbols(document_symbols_response)

        assert len(records) == 2
        assert records[0].name == "MyClass"
        assert records[1].name == "helper_function"

    def test_workflow_text_output(self, formatter: CompactFormatter, document_symbols_response: list[dict[str, Any]]) -> None:
        """Test document symbol text output."""
        records = formatter.transform_symbols(document_symbols_response)
        output = formatter.symbols_to_text(records)

        assert "MyClass (5) [1:1-51:1]" in output
        assert "helper_function (12) [53:1-71:1] -> def helper_function(x: int) -> int" in output

    def test_workflow_json_with_nested_children(self, formatter: CompactFormatter, document_symbols_response: list[dict[str, Any]]) -> None:
        """Test JSON output preserves detail field."""
        records = formatter.transform_symbols(document_symbols_response)
        output = formatter.symbols_to_json(records)
        parsed = json.loads(output)

        # Both symbols have detail
        assert parsed[0]["detail"] == "class MyClass"
        assert parsed[1]["detail"] == "def helper_function(x: int) -> int"


class TestReferencesWorkflow:
    """Integration tests for references command output."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        (temp_dir / "src").mkdir()
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def references_response(self, temp_dir: Path) -> list[dict[str, Any]]:
        """Simulate a textDocument/references response."""
        return [
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 20}},
            },
            {
                "uri": f"file://{temp_dir}/src/utils.py",
                "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 24}},
            },
            {
                "uri": f"file://{temp_dir}/src/main.py",
                "range": {"start": {"line": 25, "character": 8}, "end": {"line": 25, "character": 28}},
            },
        ]

    def test_workflow_text_output(self, formatter: CompactFormatter, references_response: list[dict[str, Any]]) -> None:
        """Test references text output with file grouping."""
        records = formatter.transform_locations(references_response)
        output = formatter.locations_to_text(records)

        # Verify file grouping - main.py should have 2 locations
        assert "src/main.py:" in output
        assert "src/utils.py:" in output

        # Verify location count in output
        main_section = output.split("src/main.py:")[1].split("src/utils.py:")[0] if "src/utils.py:" in output else output.split("src/main.py:")[1]
        assert main_section.count("[") == 2  # Two locations in main.py

    def test_workflow_json_output(self, formatter: CompactFormatter, references_response: list[dict[str, Any]]) -> None:
        """Test references JSON output."""
        records = formatter.transform_locations(references_response)
        output = formatter.locations_to_json(records)
        parsed = json.loads(output)

        assert isinstance(parsed, list)
        assert len(parsed) == 3

        # Verify structure
        for item in parsed:
            assert "file" in item
            assert "range" in item
            assert item["file"] in ["src/main.py", "src/utils.py"]

    def test_workflow_yaml_output(self, formatter: CompactFormatter, references_response: list[dict[str, Any]]) -> None:
        """Test references YAML output."""
        records = formatter.transform_locations(references_response)
        output = formatter.locations_to_yaml(records)
        parsed = yaml.safe_load(output)

        assert isinstance(parsed, list)
        assert len(parsed) == 3

    def test_workflow_csv_output(self, formatter: CompactFormatter, references_response: list[dict[str, Any]]) -> None:
        """Test references CSV output."""
        records = formatter.transform_locations(references_response)
        output = formatter.locations_to_csv(records)
        lines = output.strip().split("\n")

        # Header + 3 data rows
        assert len(lines) == 4
        assert lines[0] == "file,range"

    def test_workflow_filter_test_locations(self, formatter: CompactFormatter, references_response: list[dict[str, Any]]) -> None:
        """Test filtering test file locations."""
        # Add a test location
        references_response_with_test = references_response + [
            {
                "uri": f"file://{formatter.workspace}/tests/test_main.py",
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
            },
        ]

        records = formatter.transform_locations(references_response_with_test)

        # Filter out test locations
        filtered = [r for r in records if not r.file.startswith("tests/")]

        assert len(filtered) == 3
        assert all(not r.file.startswith("tests/") for r in filtered)


class TestEdgeCases:
    """Edge case tests for compact formatter."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        return CompactFormatter(temp_dir)

    def test_empty_symbols_list(self, formatter: CompactFormatter) -> None:
        """Test handling empty symbol list."""
        output_text = formatter.symbols_to_text([])
        output_json = formatter.symbols_to_json([])
        output_yaml = formatter.symbols_to_yaml([])
        output_csv = formatter.symbols_to_csv([])

        assert output_text == "No symbols found."
        assert json.loads(output_json) == []
        assert yaml.safe_load(output_yaml) == []
        assert output_csv == ""

    def test_empty_locations_list(self, formatter: CompactFormatter) -> None:
        """Test handling empty location list."""
        output_text = formatter.locations_to_text([])
        output_json = formatter.locations_to_json([])
        output_yaml = formatter.locations_to_yaml([])
        output_csv = formatter.locations_to_csv([])

        assert output_text == "No locations found."
        assert json.loads(output_json) == []
        assert yaml.safe_load(output_yaml) == []
        assert output_csv == ""

    def test_uri_outside_workspace(self, formatter: CompactFormatter) -> None:
        """Test handling URIs outside workspace."""
        symbols = [
            {
                "name": "ExternalSymbol",
                "kind": 5,
                "location": {
                    "uri": "file:///outside/workspace/lib.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                },
            },
        ]
        records = formatter.transform_symbols(symbols)

        # Should return absolute path
        assert records[0].file == "/outside/workspace/lib.py"

    def test_non_file_uri(self, formatter: CompactFormatter) -> None:
        """Test handling non-file URIs."""
        symbols = [
            {
                "name": "VirtualSymbol",
                "kind": 5,
                "location": {
                    "uri": "untitled:Untitled-1",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                },
            },
        ]
        records = formatter.transform_symbols(symbols)

        # Should return the original URI
        assert records[0].file == "untitled:Untitled-1"

    def test_missing_range_fields(self, formatter: CompactFormatter) -> None:
        """Test handling symbols with missing range fields."""
        symbols = [
            {
                "name": "IncompleteSymbol",
                "kind": 5,
                "location": {
                    "uri": f"file://{formatter.workspace}/test.py",
                    "range": {},  # Empty range
                },
            },
        ]
        records = formatter.transform_symbols(symbols)

        # Should use defaults (1:1-1:1)
        assert records[0].range == "1:1-1:1"

    def test_unicode_in_symbol_names(self, formatter: CompactFormatter) -> None:
        """Test handling unicode characters in symbol names."""
        symbols = [
            {
                "name": "\u03b1\u03b2\u03b3_func",  # Greek letters
                "kind": 12,
                "location": {
                    "uri": f"file://{formatter.workspace}/test.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                },
                "detail": "\u00e9\u00e8\u00ea",  # Accented characters
            },
        ]
        records = formatter.transform_symbols(symbols)

        # Text output
        output_text = formatter.symbols_to_text(records)
        assert "\u03b1\u03b2\u03b3_func" in output_text

        # YAML output should preserve unicode
        output_yaml = formatter.symbols_to_yaml(records)
        assert "\u03b1\u03b2\u03b3_func" in output_yaml

    def test_special_characters_in_detail(self, formatter: CompactFormatter) -> None:
        """Test handling special characters in detail field."""
        symbols = [
            {
                "name": "FuncWithSpecial",
                "kind": 12,
                "location": {
                    "uri": f"file://{formatter.workspace}/test.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                },
                "detail": "def func(x: list[str], y: dict[str, Any]) -> tuple[int, ...]",
            },
        ]
        records = formatter.transform_symbols(symbols)
        output_csv = formatter.symbols_to_csv(records)

        # CSV should handle commas in detail field
        lines = output_csv.strip().split("\n")
        assert len(lines) == 2  # header + 1 row

    def test_many_symbols_performance(self, formatter: CompactFormatter, temp_dir: Path) -> None:
        """Test performance with many symbols."""
        (temp_dir / "src").mkdir()

        # Generate 100 symbols
        symbols = [
            {
                "name": f"Symbol_{i}",
                "kind": 5,
                "location": {
                    "uri": f"file://{temp_dir}/src/file_{i // 10}.py",
                    "range": {"start": {"line": i, "character": 0}, "end": {"line": i + 10, "character": 0}},
                },
                "detail": f"def symbol_{i}() -> None",
            }
            for i in range(100)
        ]

        records = formatter.transform_symbols(symbols)
        assert len(records) == 100

        # Text output should be fast
        output_text = formatter.symbols_to_text(records)
        assert "Symbol_0" in output_text
        assert "Symbol_99" in output_text

        # JSON output
        output_json = formatter.symbols_to_json(records)
        parsed = json.loads(output_json)
        assert len(parsed) == 100


class TestTokenEfficiency:
    """Tests to verify token efficiency of compact output formats."""

    @pytest.fixture
    def formatter(self, temp_dir: Path) -> CompactFormatter:
        """Create a formatter with a test workspace."""
        (temp_dir / "src").mkdir()
        return CompactFormatter(temp_dir)

    @pytest.fixture
    def sample_symbols(self, temp_dir: Path) -> list[dict[str, Any]]:
        """Sample symbols for token efficiency testing."""
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
                "containerName": "MyModule",
                "tags": [1, 2],
            },
        ]

    def test_json_omits_null_fields(self, formatter: CompactFormatter, sample_symbols: list[dict[str, Any]]) -> None:
        """Verify JSON omits null/None fields for token savings."""
        records = formatter.transform_symbols(sample_symbols)
        output = formatter.symbols_to_json(records)
        parsed = json.loads(output)

        # First symbol has no container - should be omitted
        assert "container" not in parsed[0]

        # Second symbol has container - should be included
        assert "container" in parsed[1]
        assert parsed[1]["container"] == "MyModule"

    def test_yaml_omits_null_fields(self, formatter: CompactFormatter, sample_symbols: list[dict[str, Any]]) -> None:
        """Verify YAML omits null fields for token savings."""
        records = formatter.transform_symbols(sample_symbols)
        output = formatter.symbols_to_yaml(records)
        parsed = yaml.safe_load(output)

        # First symbol has no container - should be omitted
        assert "container" not in parsed[0]

    def test_compact_range_format(self, formatter: CompactFormatter, sample_symbols: list[dict[str, Any]]) -> None:
        """Verify range uses compact format (saves tokens vs verbose)."""
        records = formatter.transform_symbols(sample_symbols)

        # Range should be compact: "1:1-51:1" not verbose like "line 1, column 1 to line 51, column 1"
        assert records[0].range == "1:1-51:1"
        assert records[1].range == "11:1-31:1"

    def test_relative_paths(self, formatter: CompactFormatter, sample_symbols: list[dict[str, Any]]) -> None:
        """Verify paths are relative (saves tokens vs absolute URIs)."""
        records = formatter.transform_symbols(sample_symbols)

        # Should use relative paths, not full URIs
        assert records[0].file == "src/models.py"
        assert records[1].file == "src/utils.py"
        assert not records[0].file.startswith("file://")
