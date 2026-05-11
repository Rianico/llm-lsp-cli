"""Deep merge utilities for configuration layering.

This module handles LSP response data (dict[str, object]).
LSP responses are inherently dynamic, so object is used for dict value types.
"""

from typing import cast


def deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Deep merge two dictionaries. Override takes precedence.

    - Nested dicts are merged recursively
    - Lists are replaced (not concatenation)
    - Non-dict values in override replace base values

    Args:
        base: Base dictionary (lower priority)
        override: Override dictionary (higher priority)

    Returns:
        New merged dictionary (inputs are not modified)
    """
    result: dict[str, object] = dict(base)
    for key, value in override.items():
        base_val = result.get(key)
        if isinstance(base_val, dict) and isinstance(value, dict):
            # Both values are dicts - merge recursively
            # Cast from dict[Unknown, Unknown] to dict[str, object]
            base_dict = cast(dict[str, object], base_val)
            override_dict = cast(dict[str, object], value)
            result[key] = deep_merge(base_dict, override_dict)
        else:
            result[key] = value
    return result
