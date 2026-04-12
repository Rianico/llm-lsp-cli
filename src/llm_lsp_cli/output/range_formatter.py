"""Range formatting utilities for compact output."""

from __future__ import annotations

from typing import Any


def format_range_compact(range_obj: dict[str, Any]) -> str:
    """Format an LSP range into a compact string representation.

    Converts 0-based LSP line/character positions to 1-based human-readable format.

    Args:
        range_obj: LSP range object with optional start/end positions

    Returns:
        Compact range string "start_line:start_char-end_line:end_char"

    Example:
        {"start": {"line": 0, "character": 0}, "end": {"line": 49, "character": 0}}
        -> "1:1-50:1"
    """
    # Extract start positions (default to 0 if missing)
    start = range_obj.get("start", {})
    start_line = (start.get("line", 0) or 0) + 1
    start_char = (start.get("character", 0) or 0) + 1

    # Extract end positions (default to 0 if missing)
    end = range_obj.get("end", {})
    end_line = (end.get("line", 0) or 0) + 1
    end_char = (end.get("character", 0) or 0) + 1

    return f"{start_line}:{start_char}-{end_line}:{end_char}"
