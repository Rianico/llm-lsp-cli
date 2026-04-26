"""Tests for OutputDispatcher class."""

from __future__ import annotations

import inspect
import json
from typing import Any

import pytest
import yaml

from llm_lsp_cli.utils import OutputFormat


class TestDispatcherClassExists:
    """Tests for OutputDispatcher class existence."""

    def test_dispatcher_module_exists(self) -> None:
        """Verify dispatcher.py module can be imported."""
        from llm_lsp_cli.output import dispatcher  # noqa: F401

    def test_dispatcher_class_exists(self) -> None:
        """Verify OutputDispatcher class exists."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert OutputDispatcher is not None

    def test_dispatcher_can_be_instantiated(self) -> None:
        """Verify OutputDispatcher can be instantiated without args."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        assert dispatcher is not None


class TestDispatcherFormatMethod:
    """Tests for OutputDispatcher.format() method."""

    def test_dispatcher_has_format_method(self) -> None:
        """Verify OutputDispatcher has format method."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format")
        assert callable(getattr(OutputDispatcher, "format"))

    def test_dispatcher_format_json(self, symbol_record: Any) -> None:
        """Verify format() with JSON returns properly indented JSON."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format(symbol_record, OutputFormat.JSON)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["name"] == symbol_record.name

        # Should have indent=2 (check for 2-space indentation pattern)
        assert "  " in result  # indent=2 produces 2-space indentation
        assert result.startswith("{")

    def test_dispatcher_format_yaml(self, symbol_record: Any) -> None:
        """Verify format() with YAML returns block-style YAML."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format(symbol_record, OutputFormat.YAML)

        # Should contain YAML markers
        assert ":" in result

        # Should not be flow style (no curly braces wrapping content)
        assert not result.strip().startswith("{")

    def test_dispatcher_format_csv_single(self, symbol_record: Any) -> None:
        """Verify format() with CSV returns header + single data row."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format(symbol_record, OutputFormat.CSV)

        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + data row

        # First line should be header
        expected_headers = ",".join(symbol_record.get_csv_headers())
        assert lines[0] == expected_headers

    def test_dispatcher_format_text(self, symbol_record: Any) -> None:
        """Verify format() with TEXT returns get_text_line() result."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format(symbol_record, OutputFormat.TEXT)

        # Should match what the record's get_text_line returns
        assert result == symbol_record.get_text_line()


class TestDispatcherFormatListMethod:
    """Tests for OutputDispatcher.format_list() method."""

    def test_dispatcher_has_format_list_method(self) -> None:
        """Verify OutputDispatcher has format_list method."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format_list")
        assert callable(getattr(OutputDispatcher, "format_list"))

    def test_dispatcher_format_list_empty(self) -> None:
        """Verify format_list() with empty list returns empty JSON array for JSON."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()

        # JSON should return "[]" (valid empty array)
        result = dispatcher.format_list([], OutputFormat.JSON)
        assert result == "[]"

        # YAML should return "[]\n" (valid empty array)
        result = dispatcher.format_list([], OutputFormat.YAML)
        assert result == "[]\n"

        # CSV should return "" (no output)
        result = dispatcher.format_list([], OutputFormat.CSV)
        assert result == ""

        # TEXT should return "" (no output)
        result = dispatcher.format_list([], OutputFormat.TEXT)
        assert result == ""

    def test_dispatcher_format_list_json(self, symbol_list: list[Any]) -> None:
        """Verify format_list() with JSON returns JSON array with indent=2."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(symbol_list, OutputFormat.JSON)

        # Should be valid JSON array
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == len(symbol_list)
        assert result.startswith("[")

        # Should have indent=2
        assert "  " in result

    def test_dispatcher_format_list_yaml(self, symbol_list: list[Any]) -> None:
        """Verify format_list() with YAML returns block-style YAML list."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(symbol_list, OutputFormat.YAML)

        # Should contain YAML list marker
        assert "-" in result

        # Should not be flow style
        assert not result.strip().startswith("[")

    def test_dispatcher_format_list_csv(self, symbol_list: list[Any]) -> None:
        """Verify format_list() with CSV returns header + data rows."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(symbol_list, OutputFormat.CSV)

        lines = result.strip().split("\n")
        # header + one row per record
        assert len(lines) == 1 + len(symbol_list)

        # First line should be header
        expected_headers = ",".join(symbol_list[0].get_csv_headers())
        assert lines[0] == expected_headers

    def test_dispatcher_format_list_text(self, symbol_list: list[Any]) -> None:
        """Verify format_list() with TEXT returns one line per record."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        dispatcher = OutputDispatcher()
        result = dispatcher.format_list(symbol_list, OutputFormat.TEXT)

        lines = result.split("\n")
        # Should have one line per record
        assert len(lines) == len(symbol_list)

        # Each line should not contain embedded newlines
        for line in lines:
            assert "\n" not in line


class TestDispatcherUsesMatchCase:
    """Tests verifying OutputDispatcher uses match/case, not if/elif."""

    def test_dispatcher_uses_match_case(self) -> None:
        """Verify format method uses match/case, not if/elif chains."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        source = inspect.getsource(OutputDispatcher.format)

        # Should contain match statement
        assert "match " in source or "match\n" in source

        # Should NOT contain if/elif chains checking output format
        # We look for patterns like "if fmt ==" or "if format =="
        import re

        if_elif_pattern = r"if\s+(fmt|format|output_format)\s*(==|is)"
        matches = re.findall(if_elif_pattern, source)
        assert len(matches) == 0, f"Found if/elif pattern in format method: {matches}"


# =============================================================================
# Fixtures for SymbolRecord
# =============================================================================


class MockSymbolRecord:
    """Mock record implementing FormattableRecord for testing dispatcher."""

    def __init__(self, name: str = "myFunction", kind_name: str = "Function") -> None:
        self.name = name
        self.kind_name = kind_name
        self.file = "test.py"
        self.range_str = "1:1-1:10"

    def to_compact_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind_name": self.kind_name,
            "file": self.file,
            "range": self.range_str,
        }

    def get_csv_headers(self) -> list[str]:
        return ["name", "kind_name", "file", "range"]

    def get_csv_row(self) -> dict[str, str]:
        return {
            "name": self.name,
            "kind_name": self.kind_name,
            "file": self.file,
            "range": self.range_str,
        }

    def get_text_line(self) -> str:
        return f"{self.file}: {self.name} ({self.kind_name}) [{self.range_str}]"


@pytest.fixture
def symbol_record() -> MockSymbolRecord:
    """Provide a single mock SymbolRecord."""
    return MockSymbolRecord(name="myFunction", kind_name="Function")


@pytest.fixture
def symbol_list() -> list[MockSymbolRecord]:
    """Provide a list of mock SymbolRecords."""
    return [
        MockSymbolRecord(name="func1", kind_name="Function"),
        MockSymbolRecord(name="MyClass", kind_name="Class"),
        MockSymbolRecord(name="helper", kind_name="Method"),
    ]
