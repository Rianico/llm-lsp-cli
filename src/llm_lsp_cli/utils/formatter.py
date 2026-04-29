"""Output formatters for llm-lsp-cli."""

from __future__ import annotations

import csv
import io
import json
from enum import Enum
from typing import Any

import yaml

# LSP SymbolKind mapping (3.17 spec)
# Maps numeric kind values to human-readable names
SYMBOL_KIND_MAP: dict[int, str] = {
    1: "File",
    2: "Module",
    3: "Namespace",
    4: "Package",
    5: "Class",
    6: "Method",
    7: "Property",
    8: "Field",
    9: "Constructor",
    10: "Enum",
    11: "Interface",
    12: "Function",
    13: "Variable",
    14: "Constant",
    15: "String",
    16: "Number",
    17: "Boolean",
    18: "Array",
    19: "Object",
    20: "Key",
    21: "Null",
    22: "EnumMember",
    23: "Struct",
    24: "Event",
    25: "Operator",
    26: "TypeParameter",
}


def get_symbol_kind_name(kind: int) -> str:
    """Translate LSP SymbolKind number to human-readable name.

    Args:
        kind: The LSP SymbolKind number (1-26)

    Returns:
        Human-readable kind name, or "Unknown(N)" for unknown kinds
    """
    return SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")


# LSP DiagnosticTag mapping (3.17 spec)
# Maps numeric tag values to human-readable names
DIAGNOSTIC_TAG_MAP: dict[int, str] = {
    1: "Unnecessary",
    2: "Deprecated",
}


def get_diagnostic_tag_name(tag: int) -> str:
    """Translate LSP DiagnosticTag number to human-readable name.

    Args:
        tag: The LSP DiagnosticTag number (1=Unnecessary, 2=Deprecated)

    Returns:
        Human-readable tag name, or "Unknown(N)" for unknown tags
    """
    return DIAGNOSTIC_TAG_MAP.get(tag, f"Unknown({tag})")


class OutputFormat(str, Enum):
    """Output format options."""

    TEXT = "text"
    YAML = "yaml"
    JSON = "json"
    CSV = "csv"


def format_output(data: Any, output_format: OutputFormat) -> str:
    """Format data according to the specified output format.

    Args:
        data: The data to format (typically an LSP response dict)
        output_format: The desired output format

    Returns:
        Formatted string output
    """
    if output_format == OutputFormat.YAML:
        return str(
            yaml.safe_dump(
                data,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        )
    elif output_format == OutputFormat.JSON:
        return json.dumps(data, indent=2)
    elif output_format == OutputFormat.CSV:
        # CSV format requires command-specific handling
        # This function is a fallback - commands should use their specific CSV formatters
        return str(data)
    else:
        # TEXT format - should not be used for full response formatting
        # Text formatting is handled by individual commands
        return str(data)


# =============================================================================
# CSV Format Functions
# =============================================================================


def _write_csv_rows(
    rows: list[dict[str, Any]], fieldnames: list[str], lineterminator: str = "\n"
) -> str:
    """Write rows to CSV string.

    Args:
        rows: List of row dictionaries
        fieldnames: Column field names
        lineterminator: Line terminator (default: newline)

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator=lineterminator)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _extract_location_fields(location: dict[str, Any]) -> dict[str, str]:
    """Extract flat fields from LSP location for CSV output.

    Args:
        location: LSP location object

    Returns:
        Dictionary with flat CSV fields
    """
    uri = location.get("uri", "")
    range_obj = location.get("range", {})
    start = range_obj.get("start", {})
    end = range_obj.get("end", {})

    return {
        "uri": str(uri) if uri is not None else "",
        "start_line": str(start.get("line", 0)),
        "start_char": str(start.get("character", 0)),
        "end_line": str(end.get("line", 0)),
        "end_char": str(end.get("character", 0)),
    }


def format_locations_csv(locations: list[dict[str, Any]]) -> str:
    """Format location list as CSV.

    Used by definition and references commands.

    Args:
        locations: List of LSP location objects

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not locations:
        return ""

    fieldnames = ["uri", "start_line", "start_char", "end_line", "end_char"]
    rows = [_extract_location_fields(loc) for loc in locations]
    return _write_csv_rows(rows, fieldnames)


def _extract_completion_fields(item: dict[str, Any]) -> dict[str, str]:
    """Extract flat fields from LSP completion item for CSV output.

    Args:
        item: LSP completion item object

    Returns:
        Dictionary with flat CSV fields
    """
    kind = item.get("kind", 0)
    detail = item.get("detail")
    documentation = item.get("documentation")

    # Handle None values - convert to empty string
    if detail is None:
        detail = ""
    if documentation is None:
        documentation = ""

    # Handle dict documentation (MarkdownContent)
    if isinstance(documentation, dict):
        documentation = documentation.get("value", "")

    return {
        "label": str(item.get("label", "")),
        "kind": str(kind),
        "kind_name": get_symbol_kind_name(kind),
        "detail": str(detail) if detail is not None else "",
        "documentation": str(documentation) if documentation else "",
    }


def format_completions_csv(items: list[dict[str, Any]]) -> str:
    """Format completion items as CSV.

    Args:
        items: List of LSP completion items

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not items:
        return ""

    fieldnames = ["label", "kind", "kind_name", "detail", "documentation"]
    rows = [_extract_completion_fields(item) for item in items]
    return _write_csv_rows(rows, fieldnames)


def _extract_symbol_fields(symbol: dict[str, Any], include_uri: bool = False) -> dict[str, str]:
    """Extract flat fields from LSP symbol for CSV output.

    Args:
        symbol: LSP symbol object
        include_uri: Whether to include URI (for workspace symbols)

    Returns:
        Dictionary with flat CSV fields
    """
    kind = symbol.get("kind", 0)
    range_obj = symbol.get("range", {})

    # For workspace symbols, get range from location
    if not range_obj and "location" in symbol:
        location = symbol.get("location", {})
        range_obj = location.get("range", {})

    start = range_obj.get("start", {})
    end = range_obj.get("end", {})

    result: dict[str, str] = {
        "name": str(symbol.get("name", "")),
        "kind": str(kind),
        "kind_name": get_symbol_kind_name(kind),
        "start_line": str(start.get("line", 0)),
        "start_char": str(start.get("character", 0)),
        "end_line": str(end.get("line", 0)),
        "end_char": str(end.get("character", 0)),
    }

    if include_uri:
        # Get URI from location for workspace symbols
        location = symbol.get("location", {})
        result["uri"] = str(location.get("uri", ""))

    return result


def format_document_symbols_csv(symbols: list[dict[str, Any]]) -> str:
    """Format document symbols as CSV.

    Args:
        symbols: List of LSP document symbol objects

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not symbols:
        return ""

    fieldnames = ["name", "kind", "kind_name", "start_line", "start_char", "end_line", "end_char"]
    rows = [_extract_symbol_fields(symbol, include_uri=False) for symbol in symbols]
    return _write_csv_rows(rows, fieldnames)


def format_workspace_symbols_csv(symbols: list[dict[str, Any]]) -> str:
    """Format workspace symbols as CSV.

    Args:
        symbols: List of LSP workspace symbol objects

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not symbols:
        return ""

    fieldnames = [
        "name",
        "kind",
        "kind_name",
        "uri",
        "start_line",
        "start_char",
        "end_line",
        "end_char",
    ]
    rows = [_extract_symbol_fields(symbol, include_uri=True) for symbol in symbols]
    return _write_csv_rows(rows, fieldnames)


def format_hover_csv(hover: dict[str, Any] | None) -> str:
    """Format hover response as CSV.

    Args:
        hover: LSP hover response object or None

    Returns:
        CSV string with header row, or empty string for None/empty input
    """
    if hover is None:
        return ""

    # Extract content from hover
    contents = hover.get("contents", {})
    if isinstance(contents, dict):
        content = contents.get("value", "")
    else:
        content = str(contents) if contents else ""

    # Escape embedded newlines for CSV single-line output
    if content:
        content = str(content).replace("\n", "\\n")

    # Extract range if present
    range_obj = hover.get("range", {})
    start = range_obj.get("start", {}) if range_obj else {}
    end = range_obj.get("end", {}) if range_obj else {}

    row: dict[str, str] = {
        "content": str(content) if content else "",
        "range_start_line": (str(start.get("line", "")) if start.get("line") is not None else ""),
        "range_start_char": (
            str(start.get("character", "")) if start.get("character") is not None else ""
        ),
        "range_end_line": str(end.get("line", "")) if end.get("line") is not None else "",
        "range_end_char": (
            str(end.get("character", "")) if end.get("character") is not None else ""
        ),
    }

    output = io.StringIO()
    fieldnames = [
        "content",
        "range_start_line",
        "range_start_char",
        "range_end_line",
        "range_end_char",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")

    writer.writeheader()
    writer.writerow(row)

    return output.getvalue()
