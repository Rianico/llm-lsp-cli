"""Unit tests for CompactFormatter.transform_completions method."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_lsp_cli.output.formatter import CompactFormatter, CompletionRecord


class TestTransformCompletionsRangeExtraction:
    """Tests for extracting range from completion items."""

    def test_transform_completions_extracts_range_from_text_edit(self, tmp_path: Path) -> None:
        """transform_completions should extract range from textEdit.range."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
                "textEdit": {
                    "range": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 5, "character": 10},
                    },
                    "newText": "my_function",
                },
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert len(records) == 1
        assert records[0].range is not None
        assert records[0].range.start.line == 5
        assert records[0].range.start.character == 0

    def test_transform_completions_handles_missing_text_edit(self, tmp_path: Path) -> None:
        """transform_completions should handle missing textEdit with None range."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert len(records) == 1
        assert records[0].range is None


class TestTransformCompletionsPositionExtraction:
    """Tests for extracting position from completion items."""

    def test_transform_completions_extracts_position_from_data_position(self, tmp_path: Path) -> None:
        """transform_completions should extract position from data.position."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
                "data": {
                    "position": {"line": 5, "character": 5},
                },
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert len(records) == 1
        assert records[0].position is not None
        assert records[0].position.start.line == 5
        assert records[0].position.start.character == 5

    def test_transform_completions_handles_missing_data_position(self, tmp_path: Path) -> None:
        """transform_completions should handle missing data.position with None."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert len(records) == 1
        assert records[0].position is None


class TestTransformCompletionsFieldExtraction:
    """Tests for extracting fields from completion items."""

    def test_transform_completions_normalizes_file_path(self, tmp_path: Path) -> None:
        """transform_completions should normalize file path."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert records[0].file == "src/main.py"

    def test_transform_completions_translates_kind_to_kind_name(self, tmp_path: Path) -> None:
        """transform_completions should translate kind int to kind_name string."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,  # Function
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert records[0].kind == 12
        assert records[0].kind_name == "Function"

    def test_transform_completions_extracts_detail(self, tmp_path: Path) -> None:
        """transform_completions should extract detail field."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
                "detail": "def my_function(x: int) -> str",
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert records[0].detail == "def my_function(x: int) -> str"

    def test_transform_completions_extracts_documentation(self, tmp_path: Path) -> None:
        """transform_completions should extract documentation field."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
                "documentation": "A sample function.",
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert records[0].documentation == "A sample function."

    def test_transform_completions_handles_dict_documentation(self, tmp_path: Path) -> None:
        """transform_completions should extract value from dict documentation."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {
                "label": "my_function",
                "kind": 12,
                "documentation": {
                    "kind": "markdown",
                    "value": "A sample function.",
                },
            }
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert records[0].documentation == "A sample function."


class TestTransformCompletionsListHandling:
    """Tests for handling lists of completion items."""

    def test_transform_completions_handles_empty_items_list(self, tmp_path: Path) -> None:
        """transform_completions should return empty list for empty input."""
        formatter = CompactFormatter(tmp_path)
        records = formatter.transform_completions([], file_path="src/main.py")
        assert records == []

    def test_transform_completions_handles_multiple_items(self, tmp_path: Path) -> None:
        """transform_completions should handle multiple items."""
        formatter = CompactFormatter(tmp_path)
        items = [
            {"label": "foo", "kind": 12},
            {"label": "bar", "kind": 6},
            {"label": "baz", "kind": 13},
        ]
        records = formatter.transform_completions(items, file_path="src/main.py")
        assert len(records) == 3
        assert records[0].label == "foo"
        assert records[1].label == "bar"
        assert records[2].label == "baz"


class TestTransformCompletionsKindNameMapping:
    """Tests for kind to kind_name mapping."""

    def test_kind_1_maps_to_file(self, tmp_path: Path) -> None:
        """Kind 1 should map to 'File' (LSP SymbolKind spec)."""
        formatter = CompactFormatter(tmp_path)
        items = [{"label": "x", "kind": 1}]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].kind_name == "File"

    def test_kind_5_maps_to_class(self, tmp_path: Path) -> None:
        """Kind 5 should map to 'Class'."""
        formatter = CompactFormatter(tmp_path)
        items = [{"label": "MyClass", "kind": 5}]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].kind_name == "Class"

    def test_kind_12_maps_to_function(self, tmp_path: Path) -> None:
        """Kind 12 should map to 'Function'."""
        formatter = CompactFormatter(tmp_path)
        items = [{"label": "my_func", "kind": 12}]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].kind_name == "Function"

    def test_unknown_kind_maps_to_unknown_string(self, tmp_path: Path) -> None:
        """Unknown kind should map to 'Unknown(N)'."""
        formatter = CompactFormatter(tmp_path)
        items = [{"label": "x", "kind": 999}]
        records = formatter.transform_completions(items, file_path="test.py")
        assert records[0].kind_name == "Unknown(999)"
