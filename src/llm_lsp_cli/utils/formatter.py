"""Output formatters for llm-lsp-cli.

This module handles LSP response data for output formatting.
Uses object for unknown data fields; specific types for known structures.
"""

from __future__ import annotations

import json
from enum import StrEnum

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
