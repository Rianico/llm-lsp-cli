"""Unit tests for range formatter module."""

from typing import Any

from llm_lsp_cli.output.range_formatter import format_range_compact


class TestFormatRangeCompact:
    """Tests for format_range_compact function."""

    def test_simple_range(self) -> None:
        """Verify 1-based indexing conversion."""
        range_obj: dict[str, Any] = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 49, "character": 0},
        }
        result = format_range_compact(range_obj)
        assert result == "1:1-50:1"

    def test_single_line_range(self) -> None:
        """Single-line range formatting."""
        range_obj: dict[str, Any] = {
            "start": {"line": 10, "character": 5},
            "end": {"line": 10, "character": 20},
        }
        result = format_range_compact(range_obj)
        assert result == "11:6-11:21"

    def test_zero_based_input(self) -> None:
        """Verify 0-based to 1-based conversion."""
        range_obj: dict[str, Any] = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 10},
        }
        result = format_range_compact(range_obj)
        assert result == "1:1-1:11"

    def test_missing_start(self) -> None:
        """Handle missing start (default to 0)."""
        range_obj: dict[str, Any] = {
            "end": {"line": 10, "character": 5},
        }
        result = format_range_compact(range_obj)
        assert result == "1:1-11:6"

    def test_missing_end(self) -> None:
        """Handle missing end (default to 0)."""
        range_obj: dict[str, Any] = {
            "start": {"line": 5, "character": 2},
        }
        result = format_range_compact(range_obj)
        assert result == "6:3-1:1"

    def test_empty_range_obj(self) -> None:
        """Handle empty range object."""
        range_obj: dict[str, Any] = {}
        result = format_range_compact(range_obj)
        assert result == "1:1-1:1"

    def test_multibyte_characters(self) -> None:
        """Character positions are byte offsets."""
        range_obj: dict[str, Any] = {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 5},
        }
        result = format_range_compact(range_obj)
        assert result == "1:1-1:6"
