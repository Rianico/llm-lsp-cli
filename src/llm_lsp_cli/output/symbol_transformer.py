# pyright: reportExplicitAny=false
# pyright: reportAny=false
"""Symbol transformer for depth-controlled hierarchical symbol traversal.

This module implements ADR-0014: hierarchical symbol output with depth-controlled
traversal, returning immutable SymbolNode tuples for tree-structured rendering.
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_lsp_cli.utils.formatter import get_symbol_kind_name

# Tag mapping: LSP SymbolTag numeric values to string representations
TAG_MAP: dict[int, str] = {
    1: "@deprecated",
    2: "@abstract",
}


@dataclass(frozen=True)
class SymbolNode:
    """Immutable symbol node for hierarchical tree representation.

    A frozen dataclass representing a single symbol in a tree structure.
    All fields are immutable; children and tags are tuples for immutability.

    Attributes:
        name: Symbol name
        kind: LSP SymbolKind numeric value
        kind_name: Human-readable kind name (e.g., "Class", "Method")
        range: Compact range string "line:char-line:char" (1-based)
        selection_range: Optional compact selection range string
        detail: Optional detail string from LSP
        tags: Tuple of string tags (e.g., "@deprecated")
        children: Tuple of child SymbolNodes
        depth: Depth in the tree (0 = root)
    """

    name: str
    kind: int
    kind_name: str
    range: str
    selection_range: str | None
    detail: str | None
    tags: tuple[str, ...]
    children: tuple[SymbolNode, ...]
    depth: int


def _format_range(range_obj: dict[str, Any]) -> str:
    """Convert LSP range dict to compact string format (1-based).

    Args:
        range_obj: LSP Range dict with start/end Position dicts

    Returns:
        Compact string "line:char-line:char" (1-based)
    """
    start = range_obj.get("start", {})
    end = range_obj.get("end", {})

    start_line = (start.get("line", 0) or 0) + 1
    start_char = (start.get("character", 0) or 0) + 1
    end_line = (end.get("line", 0) or 0) + 1
    end_char = (end.get("character", 0) or 0) + 1

    return f"{start_line}:{start_char}-{end_line}:{end_char}"


def _map_tags(tag_values: list[int] | None) -> tuple[str, ...]:
    """Convert numeric LSP tags to string representations.

    Args:
        tag_values: List of LSP SymbolTag numeric values

    Returns:
        Tuple of string tag representations
    """
    if not tag_values:
        return ()

    result: list[str] = []
    for tag in tag_values:
        if tag in TAG_MAP:
            result.append(TAG_MAP[tag])
        else:
            result.append(f"@{tag}")
    return tuple(result)


def _transform_symbol(
    sym: dict[str, Any],
    depth_limit: int,
    current_depth: int,
) -> SymbolNode:
    """Transform a single symbol with depth-controlled traversal.

    Args:
        sym: LSP symbol dict
        depth_limit: Maximum depth (-1 = unlimited)
        current_depth: Current depth in the tree

    Returns:
        SymbolNode with nested children
    """
    # Get range - handle both document and workspace symbol formats
    location = sym.get("location", sym)
    range_obj = location.get("range", sym.get("range", {}))

    # Format range as compact string
    range_str = _format_range(range_obj)

    # Format selection range if present
    selection_range_str: str | None = None
    if "selectionRange" in sym:
        selection_range_str = _format_range(sym["selectionRange"])

    # Get kind info
    kind = sym.get("kind", 0)
    kind_name = get_symbol_kind_name(kind)

    # Map tags
    tags = _map_tags(sym.get("tags"))

    # Get detail
    detail = sym.get("detail")

    # Process children if depth allows
    children: tuple[SymbolNode, ...] = ()
    if depth_limit != 0:
        raw_children = sym.get("children")
        if raw_children:
            child_depth = depth_limit - 1 if depth_limit > 0 else -1
            child_nodes: list[SymbolNode] = []
            for child_sym in raw_children:
                child_node = _transform_symbol(child_sym, child_depth, current_depth + 1)
                child_nodes.append(child_node)
            children = tuple(child_nodes)

    return SymbolNode(
        name=sym.get("name", ""),
        kind=kind,
        kind_name=kind_name,
        range=range_str,
        selection_range=selection_range_str,
        detail=detail,
        tags=tags,
        children=children,
        depth=current_depth,
    )


def transform_symbols(
    symbols: list[dict[str, Any]],
    depth_limit: int,
    workspace: Path,  # pyright: ignore[reportUnusedParameter]
) -> tuple[SymbolNode, ...]:
    """Transform LSP symbols to SymbolNode tuple with depth-controlled traversal.

    Handles both workspace symbols (with location wrapper) and
    document symbols (hierarchical structure with children).

    Args:
        symbols: LSP symbol list
        depth_limit: Maximum traversal depth. -1 = unlimited, 0 = top-level only
        workspace: Workspace root path (for future URI normalization)

    Returns:
        Tuple of SymbolNode objects with nested children
    """
    if not symbols:
        return ()

    result: list[SymbolNode] = []
    for sym in symbols:
        node = _transform_symbol(sym, depth_limit, current_depth=0)
        result.append(node)

    return tuple(result)
