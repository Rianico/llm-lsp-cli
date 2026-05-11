"""Type-safe helper functions for extracting values from object-typed data.

This module provides helper functions for safely extracting typed values from
`object`-typed data, which is used for LSP response data throughout the codebase.

The pattern follows ADR-0025: Use `object` for unknown LSP data at boundaries,
then validate with these helpers to extract concrete types.
"""

from __future__ import annotations

from typing import cast


def _as_str_dict(data: object) -> dict[str, object] | None:
    """Cast object to dict[str, object] if it's a dict, else None."""
    if isinstance(data, dict):
        return cast(dict[str, object], data)
    return None


def get_int(data: object, key: str, default: int = 0) -> int:
    """Extract an integer from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up
        default: Default value if key not found or value is not an int

    Returns:
        The integer value, or default if extraction fails
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key, default)
        if isinstance(val, int):
            return val
    return default


def get_str(data: object, key: str, default: str = "") -> str:
    """Extract a string from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up
        default: Default value if key not found or value is not a string

    Returns:
        The string value, or default if extraction fails
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key, default)
        if isinstance(val, str):
            return val
    return default


def get_optional_str(data: object, key: str) -> str | None:
    """Extract an optional string from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        The string value, None if key is missing or value is None, or None if not a string
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key)
        if val is None:
            return None
        if isinstance(val, str):
            return val
    return None


def get_optional_int(data: object, key: str) -> int | None:
    """Extract an optional integer from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        The integer value, None if key is missing or value is None, or None if not an int
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key)
        if val is None:
            return None
        if isinstance(val, int):
            return val
    return None


def get_list(data: object, key: str) -> list[object]:
    """Extract a list from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        The list value, or empty list if extraction fails
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key, [])
        if isinstance(val, list):
            return cast(list[object], val)
    return []


def get_optional_list(data: object, key: str) -> list[object] | None:
    """Extract an optional list from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        The list value, None if key is missing or value is None, or None if not a list
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key)
        if val is None:
            return None
        if isinstance(val, list):
            return cast(list[object], val)
    return None


def get_dict(data: object, key: str) -> dict[str, object]:
    """Extract a dict from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        The dict value, or empty dict if extraction fails
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key, {})
        if isinstance(val, dict):
            return cast(dict[str, object], val)
    return {}


def get_optional_dict(data: object, key: str) -> dict[str, object] | None:
    """Extract an optional dict from a dict-like object.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        The dict value, None if key is missing or value is None, or None if not a dict
    """
    d = _as_str_dict(data)
    if d is not None:
        val = d.get(key)
        if val is None:
            return None
        if isinstance(val, dict):
            return cast(dict[str, object], val)
    return None


def get_list_of_dicts(data: object, key: str) -> list[dict[str, object]]:
    """Extract a list of dicts from a dict-like object.

    Safely extracts a list of dict values from an object.
    Returns empty list if the value is not a list or contains non-dict items.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        List of dicts, or empty list if extraction fails
    """
    d = _as_str_dict(data)
    if d is None:
        return []
    val = d.get(key)
    if not isinstance(val, list):
        return []
    items = cast(list[object], val)
    result: list[dict[str, object]] = []
    for item in items:
        if isinstance(item, dict):
            result.append(cast(dict[str, object], item))
    return result


def get_list_of_str(data: object, key: str) -> list[str]:
    """Extract a list of strings from a dict-like object.

    Safely extracts a list of string values from an object.
    Returns empty list if the value is not a list or contains non-string items.

    Args:
        data: The object to extract from (typically a dict)
        key: The key to look up

    Returns:
        List of strings, or empty list if extraction fails
    """
    d = _as_str_dict(data)
    if d is None:
        return []
    val = d.get(key)
    if not isinstance(val, list):
        return []
    items = cast(list[object], val)
    result: list[str] = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
    return result
