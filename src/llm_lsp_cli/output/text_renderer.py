"""Text renderer for tree-structured symbol output.

This module implements ADR-0014: tree-structured TEXT format with
complete field display, null field omission, and tree connectors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


def _render_group_with_tree_connectors(
    items: list[dict[str, Any]],
    item_renderer: Any,
) -> list[str]:
    """Render a list of items with tree connectors.

    Args:
        items: List of item dicts to render
        item_renderer: Callable that takes a dict and returns a string

    Returns:
        List of formatted lines with tree connectors
    """
    lines: list[str] = []
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = CONNECTOR_LAST if is_last else CONNECTOR_INTERMEDIATE
        lines.append(f"  {connector} {item_renderer(item)}")
    return lines


def _render_symbol_line(symbol: dict[str, Any]) -> str:
    """Render a single symbol as a text line.

    Args:
        symbol: Symbol dict with name, kind_name, range

    Returns:
        Formatted string: "name (kind_name) range"
    """
    name = symbol.get("name", "")
    kind_name = symbol.get("kind_name", "")
    range_str = symbol.get("range", "")
    return f"{name} ({kind_name}) {range_str}"


def _render_diagnostic_line(diag: dict[str, Any]) -> str:
    """Render a single diagnostic as a text line.

    Args:
        diag: Diagnostic dict with severity_name, message, code, range

    Returns:
        Formatted string: "severity: message [code] range"
    """
    severity = diag.get("severity_name", "Error")
    message = diag.get("message", "")
    range_str = diag.get("range", "")
    code = diag.get("code", "")
    code_str = f" [{code}]" if code else ""
    return f"{severity}: {message}{code_str} {range_str}"


def render_workspace_symbols_grouped(
    grouped_data: list[dict[str, Any]],
    header: str | None = None,
) -> str:
    """Render grouped symbols as hierarchical TEXT output.

    Args:
        grouped_data: List of group dicts with 'file' and 'symbols' keys
        header: Optional alert header to prepend

    Returns:
        Formatted TEXT string with file headers and tree connectors
    """
    if not grouped_data:
        return "No symbols found."

    lines: list[str] = []

    # Add alert header if provided
    if header:
        lines.append(header)

    # Render each file group
    for group in grouped_data:
        file_path = group.get("file", "")
        symbols = group.get("symbols", [])

        # Add file header
        lines.append(f"{file_path}:")

        # Render symbols with tree connectors
        lines.extend(_render_group_with_tree_connectors(symbols, _render_symbol_line))

    return "\n".join(lines)


def render_workspace_diagnostics_grouped(
    grouped_data: list[dict[str, Any]],
    header: str | None = None,
) -> str:
    """Render grouped diagnostics as hierarchical TEXT output.

    Args:
        grouped_data: List of group dicts with 'file' and 'diagnostics' keys
        header: Optional alert header to prepend

    Returns:
        Formatted TEXT string with file headers and tree connectors
    """
    if not grouped_data:
        return "No diagnostics found."

    lines: list[str] = []

    # Add alert header if provided
    if header:
        lines.append(header)

    # Render each file group
    for group in grouped_data:
        file_path = group.get("file", "")
        diagnostics = group.get("diagnostics", [])

        # Add file header
        lines.append(f"{file_path}:")

        # Render diagnostics with tree connectors
        lines.extend(
            _render_group_with_tree_connectors(diagnostics, _render_diagnostic_line)
        )

    return "\n".join(lines)
