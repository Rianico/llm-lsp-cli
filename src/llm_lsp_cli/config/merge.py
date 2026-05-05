# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownArgumentType=false
"""Deep merge utilities for configuration layering.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries. Override takes precedence.

    - Nested dicts are merged recursively
    - Lists are replaced (not concatenated)
    - Non-dict values in override replace base values

    Args:
        base: Base dictionary (lower priority)
        override: Override dictionary (higher priority)

    Returns:
        New merged dictionary (inputs are not modified)
    """
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
