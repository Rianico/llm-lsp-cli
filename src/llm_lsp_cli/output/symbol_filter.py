"""Symbol filtering for controlling variable-level symbol output.

This module handles LSP response data (dict[str, object]).
LSP responses are inherently dynamic, so object is used for dict value types.
"""

from llm_lsp_cli.output.verbosity import VerbosityLevel
from llm_lsp_cli.utils.type_helpers import get_optional_int, get_optional_list

# Variable-level symbol kinds that are excluded by default
# Using frozenset for O(1) lookup and immutability
VARIABLE_KINDS: frozenset[int] = frozenset(
    {
        8,  # SYMBOL_KIND_FIELD
        13,  # SYMBOL_KIND_VARIABLE
    }
)


def is_variable_symbol(symbol: dict[str, object]) -> bool:
    """Check if a symbol is a variable-level symbol.

    Variable-level symbols include:
    - SYMBOL_KIND_VARIABLE (13)
    - SYMBOL_KIND_FIELD (8)

    Args:
        symbol: Symbol dictionary with 'kind' field

    Returns:
        True if symbol is variable-level, False otherwise
    """
    kind = get_optional_int(symbol, "kind")
    if kind is None:
        return False
    return kind in VARIABLE_KINDS


def filter_symbols(
    symbols: list[dict[str, object]],
    verbosity: VerbosityLevel,
) -> list[dict[str, object]]:
    """Filter symbols based on verbosity level.

    At NORMAL verbosity (default), variable-level symbols are excluded.
    At VERBOSE verbosity or higher, all symbols are included.

    Recursively filters nested children in document symbols.

    Args:
        symbols: List of symbol dictionaries
        verbosity: Verbosity level controlling filter behavior

    Returns:
        Filtered list of symbols. Note: at VERBOSE+ level, returns the same list object (no copy).
    """
    if verbosity >= VerbosityLevel.VERBOSE:
        return symbols

    filtered: list[dict[str, object]] = []
    for symbol in symbols:
        if not is_variable_symbol(symbol):
            children = get_optional_list(symbol, "children")
            if children is not None:
                # Type narrow children to dict list
                child_dicts: list[dict[str, object]] = [c for c in children if isinstance(c, dict)]
                filtered_children = filter_symbols(child_dicts, verbosity)
                symbol = {**symbol, "children": filtered_children}
                filtered.append(symbol)
            else:
                filtered.append(symbol)
    return filtered
