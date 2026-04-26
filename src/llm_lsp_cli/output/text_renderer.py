"""Text renderer for tree-structured symbol output.

This module implements ADR-0014: tree-structured TEXT format with
complete field display, null field omission, and tree connectors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_lsp_cli.output.symbol_transformer import SymbolNode

# Tree connector constants per ADR-0014
CONNECTOR_INTERMEDIATE = "├──"
CONNECTOR_LAST = "└──"
PREFIX_CONTINUE = "│   "
PREFIX_TERMINATE = "    "


def _render_node_line(node: SymbolNode) -> str:
    """Render a single SymbolNode as a text line.

    Format: name (kind_name) range sel[selection_range] [tags] detail
    Null/empty fields are omitted.
    Range uses bare format (no brackets) for token efficiency.

    Args:
        node: SymbolNode to render

    Returns:
        Formatted string without tree prefix
    """
    parts: list[str] = [f"{node.name} ({node.kind_name}) {node.range}"]

    # Add selection range if present
    if node.selection_range:
        parts.append(f"sel[{node.selection_range}]")

    # Add tags if present
    if node.tags:
        tag_str = " ".join(node.tags)
        parts.append(f"[{tag_str}]")

    # Add detail if present
    if node.detail:
        parts.append(node.detail)

    return " ".join(parts)


def _render_tree(
    nodes: tuple[SymbolNode, ...],
    prefix: str = "",
) -> list[str]:
    """Recursively render tree structure with connectors.

    Args:
        nodes: Tuple of SymbolNodes at current level
        prefix: Current indent prefix for tree structure

    Returns:
        List of formatted lines
    """
    if not nodes:
        return []

    lines: list[str] = []

    for i, node in enumerate(nodes):
        is_last = i == len(nodes) - 1

        # Determine connector for this node
        connector = CONNECTOR_LAST if is_last else CONNECTOR_INTERMEDIATE

        # Build the line: prefix + connector + content
        line_prefix = prefix + connector
        line_content = _render_node_line(node)
        lines.append(f"{line_prefix} {line_content}")

        # Render children if present
        if node.children:
            # Determine the prefix for children
            # Last sibling: terminated branch; intermediate: continuing branch
            child_prefix = prefix + PREFIX_TERMINATE if is_last else prefix + PREFIX_CONTINUE

            child_lines = _render_tree(node.children, child_prefix)
            lines.extend(child_lines)

    return lines


def render_text(
    nodes: tuple[SymbolNode, ...],
    file_header: str | None = None,
) -> str:
    """Render SymbolNode tuple as tree-structured TEXT format.

    Per ADR-0014:
    - Root level starts with 2-space indent
    - Connectors at all levels: ├── for intermediate, └── for last sibling
    - Continuation prefix: │   for ongoing,     for terminated

    Args:
        nodes: Tuple of SymbolNode objects
        file_header: Optional file header to prepend (e.g., "src/models.py:")

    Returns:
        Formatted tree string with connectors and proper indentation
    """
    if not nodes:
        return "No symbols found."

    lines: list[str] = []

    # Add file header if provided
    if file_header:
        lines.append(file_header)

    # Render the tree with 2-space base indent for root level
    tree_lines = _render_tree(nodes, prefix="  ")
    lines.extend(tree_lines)

    return "\n".join(lines)
