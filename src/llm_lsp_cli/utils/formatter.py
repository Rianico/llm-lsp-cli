"""Output formatters for llm-lsp-cli."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

import yaml  # type: ignore[import-untyped]

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


class OutputFormat(str, Enum):
    """Output format options."""

    TEXT = "text"
    YAML = "yaml"
    JSON = "json"


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
    else:
        # TEXT format - should not be used for full response formatting
        # Text formatting is handled by individual commands
        return str(data)
