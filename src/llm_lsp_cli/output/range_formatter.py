"""Range formatting utilities for compact output.

This module handles LSP response data (dict[str, object]).
LSP responses are inherently dynamic, so object is used for dict value types.
"""

from __future__ import annotations

from llm_lsp_cli.utils.type_helpers import get_dict, get_int


def format_range_compact(range_obj: dict[str, object]) -> str:
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
    start = get_dict(range_obj, "start")
    start_line = (get_int(start, "line", 0) or 0) + 1
    start_char = (get_int(start, "character", 0) or 0) + 1

    # Extract end positions (default to 0 if missing)
    end = get_dict(range_obj, "end")
    end_line = (get_int(end, "line", 0) or 0) + 1
    end_char = (get_int(end, "character", 0) or 0) + 1

    return f"{start_line}:{start_char}-{end_line}:{end_char}"
