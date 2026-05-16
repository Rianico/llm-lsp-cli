"""Output formatters for llm-lsp-cli.

This module handles LSP response data for output formatting.
Uses object for unknown data fields; specific types for known structures.
"""

from __future__ import annotations

import csv
import io
import json
from enum import StrEnum
from typing import cast

import yaml

from llm_lsp_cli.utils.type_helpers import (
    get_dict,
    get_int,
    get_optional_dict,
    get_optional_str,
    get_str,
)

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


class OutputFormat(StrEnum):
    """Output format options."""

    TEXT = "text"
    YAML = "yaml"
    JSON = "json"
    CSV = "csv"


def format_output(data: object, output_format: OutputFormat) -> str:
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
    rows: list[dict[str, str]], fieldnames: list[str], lineterminator: str = "\n"
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


def _extract_location_fields(location: object) -> dict[str, str]:
    """Extract flat fields from LSP location for CSV output.

    Args:
        location: LSP location object

    Returns:
        Dictionary with flat CSV fields
    """
    uri = get_str(location, "uri", "")
    range_obj = get_dict(location, "range")
    start = get_dict(range_obj, "start")
    end = get_dict(range_obj, "end")

    return {
        "uri": uri,
        "start_line": str(get_int(start, "line", 0)),
        "start_char": str(get_int(start, "character", 0)),
        "end_line": str(get_int(end, "line", 0)),
        "end_char": str(get_int(end, "character", 0)),
    }


def format_locations_csv(locations: object) -> str:
    """Format location list as CSV.

    Used by definition and references commands.

    Args:
        locations: List of LSP location objects

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not isinstance(locations, list) or not locations:
        return ""

    locations_list = cast(list[object], locations)
    fieldnames = ["uri", "start_line", "start_char", "end_line", "end_char"]
    rows = [_extract_location_fields(loc) for loc in locations_list]
    return _write_csv_rows(rows, fieldnames)


def _extract_completion_fields(item: object) -> dict[str, str]:
    """Extract flat fields from LSP completion item for CSV output.

    Args:
        item: LSP completion item object

    Returns:
        Dictionary with flat CSV fields
    """
    kind = get_int(item, "kind", 0)
    detail = get_optional_str(item, "detail") or ""
    label = get_str(item, "label", "")
    documentation: str = ""

    doc_raw = get_optional_dict(item, "documentation")
    if doc_raw:
        documentation = get_str(doc_raw, "value", "")
    elif isinstance(item, dict):
        item_dict = cast(dict[str, object], item)
        doc_val = item_dict.get("documentation")
        if isinstance(doc_val, str):
            documentation = doc_val

    return {
        "label": label,
        "kind": str(kind),
        "kind_name": get_symbol_kind_name(kind),
        "detail": detail,
        "documentation": documentation,
    }


def format_completions_csv(items: object) -> str:
    """Format completion items as CSV.

    Args:
        items: List of LSP completion items

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not isinstance(items, list) or not items:
        return ""

    items_list = cast(list[object], items)
    fieldnames = ["label", "kind", "kind_name", "detail", "documentation"]
    rows = [_extract_completion_fields(item) for item in items_list]
    return _write_csv_rows(rows, fieldnames)


def _extract_symbol_fields(symbol: object, include_uri: bool = False) -> dict[str, str]:
    """Extract flat fields from LSP symbol for CSV output.

    Args:
        symbol: LSP symbol object
        include_uri: Whether to include URI (for workspace symbols)

    Returns:
        Dictionary with flat CSV fields
    """
    kind = get_int(symbol, "kind", 0)
    name = get_str(symbol, "name", "")
    range_obj = get_dict(symbol, "range")
    location = get_dict(symbol, "location")

    # For workspace symbols, get range from location
    if not range_obj and isinstance(symbol, dict):
        symbol_dict = cast(dict[str, object], symbol)
        if "location" in symbol_dict:
            # symbol is narrowed to dict[Unknown, Unknown], but get_dict accepts object
            location = get_dict(cast(object, symbol), "location")
            range_obj = get_dict(location, "range")

    start = get_dict(range_obj, "start")
    end = get_dict(range_obj, "end")

    result: dict[str, str] = {
        "name": name,
        "kind": str(kind),
        "kind_name": get_symbol_kind_name(kind),
        "start_line": str(get_int(start, "line", 0)),
        "start_char": str(get_int(start, "character", 0)),
        "end_line": str(get_int(end, "line", 0)),
        "end_char": str(get_int(end, "character", 0)),
    }

    if include_uri:
        # Get URI from location for workspace symbols
        result["uri"] = get_str(location, "uri", "")

    return result


def format_document_symbols_csv(symbols: object) -> str:
    """Format document symbols as CSV.

    Args:
        symbols: List of LSP document symbol objects

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not isinstance(symbols, list) or not symbols:
        return ""

    symbols_list = cast(list[object], symbols)
    fieldnames = ["name", "kind", "kind_name", "start_line", "start_char", "end_line", "end_char"]
    rows = [_extract_symbol_fields(symbol, include_uri=False) for symbol in symbols_list]
    return _write_csv_rows(rows, fieldnames)


def format_workspace_symbols_csv(symbols: object) -> str:
    """Format workspace symbols as CSV.

    Args:
        symbols: List of LSP workspace symbol objects

    Returns:
        CSV string with header row, or empty string for empty input
    """
    if not isinstance(symbols, list) or not symbols:
        return ""

    symbols_list = cast(list[object], symbols)
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
    rows = [_extract_symbol_fields(symbol, include_uri=True) for symbol in symbols_list]
    return _write_csv_rows(rows, fieldnames)


def format_hover_csv(hover: object) -> str:
    """Format hover response as CSV.

    Args:
        hover: LSP hover response object or None

    Returns:
        CSV string with header row, or empty string for None/empty input
    """
    if hover is None:
        return ""

    # Extract values BEFORE isinstance checks to avoid type narrowing issues
    contents = get_dict(hover, "contents")
    range_obj = get_optional_dict(hover, "range")

    # Extract content from hover
    content = get_str(contents, "value", "") if contents else ""
    if not content and isinstance(hover, dict):
        hover_dict = cast(dict[str, object], hover)
        cont = hover_dict.get("contents")
        if isinstance(cont, str):
            content = cont

    # Escape embedded newlines for CSV single-line output
    if content:
        content = str(content).replace("\n", "\\n")

    # Extract range if present
    start = get_dict(range_obj, "start") if range_obj else {}
    end = get_dict(range_obj, "end") if range_obj else {}

    row: dict[str, str] = {
        "content": content if content else "",
        "range_start_line": str(get_int(start, "line", 0)) if start else "",
        "range_start_char": str(get_int(start, "character", 0)) if start else "",
        "range_end_line": str(get_int(end, "line", 0)) if end else "",
        "range_end_char": str(get_int(end, "character", 0)) if end else "",
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
