"""Utility functions for llm-lsp-cli."""

from llm_lsp_cli.utils.formatter import (
    OutputFormat,
    format_completions_csv,
    format_document_symbols_csv,
    format_hover_csv,
    format_locations_csv,
    format_output,
    format_workspace_symbols_csv,
    get_symbol_kind_name,
)
from llm_lsp_cli.utils.type_helpers import (
    get_dict,
    get_int,
    get_list,
    get_list_of_dicts,
    get_optional_dict,
    get_optional_int,
    get_optional_list,
    get_optional_str,
    get_str,
)
from llm_lsp_cli.utils.uri import uri_to_absolute_path

__all__ = [
    "OutputFormat",
    "format_output",
    "get_symbol_kind_name",
    "format_locations_csv",
    "format_completions_csv",
    "format_document_symbols_csv",
    "format_workspace_symbols_csv",
    "format_hover_csv",
    "uri_to_absolute_path",
    # Type helpers
    "get_int",
    "get_str",
    "get_optional_str",
    "get_optional_int",
    "get_list",
    "get_optional_list",
    "get_dict",
    "get_optional_dict",
    "get_list_of_dicts",
]
