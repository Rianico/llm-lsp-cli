"""Unit tests for CompactFormatter.transform_hover method."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_lsp_cli.output.formatter import CompactFormatter, HoverRecord


class TestTransformHoverContentExtraction:
    """Tests for extracting content from hover responses."""

    def test_transform_hover_extracts_content_from_contents_value(self, tmp_path: Path) -> None:
        """transform_hover should extract content from contents.value."""
        formatter = CompactFormatter(tmp_path)
        hover = {
            "contents": {
                "kind": "markdown",
                "value": "```python\ndef my_function(x: int) -> str\n```",
            }
        }
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert "def my_function" in record.content

    def test_transform_hover_extracts_content_from_contents_array(self, tmp_path: Path) -> None:
        """transform_hover should extract content from first item in contents array."""
        formatter = CompactFormatter(tmp_path)
        hover = {
            "contents": [
                {"language": "python", "value": "def foo(): pass"},
            ]
        }
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert "def foo" in record.content

    def test_transform_hover_handles_string_contents(self, tmp_path: Path) -> None:
        """transform_hover should handle string contents directly."""
        formatter = CompactFormatter(tmp_path)
        hover = {
            "contents": "Simple string content",
        }
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert record.content == "Simple string content"


class TestTransformHoverRangeExtraction:
    """Tests for extracting range from hover responses."""

    def test_transform_hover_extracts_range(self, tmp_path: Path) -> None:
        """transform_hover should extract range field."""
        formatter = CompactFormatter(tmp_path)
        hover = {
            "contents": {"value": "docs"},
            "range": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 15},
            },
        }
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert record.range is not None
        assert record.range.start.line == 10
        assert record.range.start.character == 4

    def test_transform_hover_handles_missing_range(self, tmp_path: Path) -> None:
        """transform_hover should handle missing range with None."""
        formatter = CompactFormatter(tmp_path)
        hover = {
            "contents": {"value": "docs"},
        }
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert record.range is None


class TestTransformHoverNoneHandling:
    """Tests for None and empty hover handling."""

    def test_transform_hover_handles_none_input(self, tmp_path: Path) -> None:
        """transform_hover should return None for None input."""
        formatter = CompactFormatter(tmp_path)
        record = formatter.transform_hover(None, file_path="src/main.py")
        assert record is None

    def test_transform_hover_handles_empty_contents(self, tmp_path: Path) -> None:
        """transform_hover should handle empty contents."""
        formatter = CompactFormatter(tmp_path)
        hover = {"contents": ""}
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert record.content == ""


class TestTransformHoverFilePath:
    """Tests for file path handling."""

    def test_transform_hover_normalizes_file_path(self, tmp_path: Path) -> None:
        """transform_hover should normalize file path."""
        formatter = CompactFormatter(tmp_path)
        hover = {"contents": {"value": "docs"}}
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert record is not None
        assert record.file == "src/main.py"


class TestTransformHoverReturnTypes:
    """Tests for return types and structures."""

    def test_transform_hover_returns_hover_record(self, tmp_path: Path) -> None:
        """transform_hover should return HoverRecord instance."""
        formatter = CompactFormatter(tmp_path)
        hover = {"contents": {"value": "docs"}}
        record = formatter.transform_hover(hover, file_path="src/main.py")
        assert isinstance(record, HoverRecord)

    def test_transform_hover_with_all_fields(self, tmp_path: Path) -> None:
        """transform_hover should populate all fields correctly."""
        formatter = CompactFormatter(tmp_path)
        hover = {
            "contents": {
                "kind": "markdown",
                "value": "def foo(x: int) -> str",
            },
            "range": {
                "start": {"line": 5, "character": 0},
                "end": {"line": 5, "character": 10},
            },
        }
        record = formatter.transform_hover(hover, file_path="test.py")
        assert record is not None
        assert record.file == "test.py"
        assert record.content == "def foo(x: int) -> str"
        assert record.range is not None
        # Verify compact format: 0-based (5,0)-(5,10) -> 1-based "6:1-6:11"
        assert record.range.to_compact() == "6:1-6:11"
