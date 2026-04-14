"""Symbol filtering for controlling variable-level symbol output."""

from typing import Any

from llm_lsp_cli.output.verbosity import VerbosityLevel

# Variable-level symbol kinds that are excluded by default
# Using frozenset for O(1) lookup and immutability
VARIABLE_KINDS: frozenset[int] = frozenset({
    8,   # SYMBOL_KIND_FIELD
    13,  # SYMBOL_KIND_VARIABLE
})


def is_variable_symbol(symbol: dict[str, Any]) -> bool:
    """Check if a symbol is a variable-level symbol.

    Variable-level symbols include:
    - SYMBOL_KIND_VARIABLE (13)
    - SYMBOL_KIND_FIELD (8)

    Args:
        symbol: Symbol dictionary with 'kind' field

    Returns:
        True if symbol is variable-level, False otherwise
    """
    kind = symbol.get("kind")
    if kind is None:
        return False
    return kind in VARIABLE_KINDS


def filter_symbols(
    symbols: list[dict[str, Any]],
    verbosity: VerbosityLevel,
) -> list[dict[str, Any]]:
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

    filtered: list[dict[str, Any]] = []
    for symbol in symbols:
        if not is_variable_symbol(symbol):
            if "children" in symbol:
                filtered_children = filter_symbols(symbol["children"], verbosity)
                symbol = {**symbol, "children": filtered_children}
                filtered.append(symbol)
            else:
                filtered.append(symbol)
    return filtered
