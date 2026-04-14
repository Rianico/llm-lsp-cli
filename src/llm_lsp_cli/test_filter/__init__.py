"""Test path filtering for LSP responses.

Provides utilities to detect and filter test files across multiple languages
using glob-based pattern matching with language-segmented patterns.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from llm_lsp_cli.config.manager import ConfigManager
from llm_lsp_cli.config.schema import TestFilterConfig

from .language_registry import get_registry
from .pattern_engine import PatternSet, PatternSource

# =============================================================================
# Default Patterns (for backward compatibility when no config is loaded)
# =============================================================================

_DEFAULT_DIRECTORY_PATTERNS = (
    "**/tests/**",
    "**/test/**",
    "**/__tests__/**",
    "**/__test__/**",
    "**/src/test/**",
)

_DEFAULT_SUFFIX_PATTERNS = (
    "_test.go",
    ".test.js",
    ".test.ts",
    ".test.jsx",
    ".test.tsx",
    ".spec.js",
    ".spec.ts",
    ".spec.jsx",
    ".spec.tsx",
    ".test.cs",
    ".tests.cs",
    ".spec.cs",
)

_DEFAULT_PREFIX_PATTERNS = ("test_", "_test")


def _create_default_pattern_set() -> PatternSet:
    """Create a PatternSet with default patterns for backward compatibility."""
    pattern_set = PatternSet()

    for pattern in _DEFAULT_DIRECTORY_PATTERNS:
        pattern_set.add_directory_pattern(pattern, PatternSource.DEFAULT)

    for pattern in _DEFAULT_SUFFIX_PATTERNS:
        pattern_set.add_suffix_pattern(pattern, PatternSource.DEFAULT)

    for pattern in _DEFAULT_PREFIX_PATTERNS:
        pattern_set.add_prefix_pattern(pattern, PatternSource.DEFAULT)

    return pattern_set


def _get_pattern_set_for_language(language: str | None) -> PatternSet:
    """Get or create a PatternSet for the given language.

    Args:
        language: Language identifier (auto-detected if None)

    Returns:
        PatternSet with patterns for the language
    """
    if language is None:
        return _create_default_pattern_set()

    registry = get_registry()
    pattern_set = registry.get_filter(language)

    # If no patterns configured for this language, use defaults
    if (
        not pattern_set._directory_patterns
        and not pattern_set._suffix_patterns
        and not pattern_set._prefix_patterns
    ):
        return _create_default_pattern_set()

    return pattern_set


def _is_test_path(uri: str, language: str | None = None) -> bool:
    """Check if a URI points to a test file or directory.

    Uses pattern matching on the URI path to detect test files.
    Results are cached for performance.

    Args:
        uri: LSP URI string (e.g., 'file:///path/to/file.py')
        language: Language identifier (auto-detected if None)

    Returns:
        True if the URI matches test patterns, False otherwise
    """
    if not uri:
        return False

    pattern_set = _get_pattern_set_for_language(language)
    result = pattern_set.match(uri)
    return result.is_match


# Apply LRU cache to _is_test_path
_is_test_path = lru_cache(maxsize=4096)(_is_test_path)


def _is_test_uri(uri: str, language: str | None = None) -> bool:
    """Check if a URI points to a test file or directory.

    Uses pattern matching on the URI path to detect test files.
    Results are cached via the wrapped _is_test_path function.

    Args:
        uri: LSP URI string (e.g., 'file:///path/to/file.py')
        language: Language identifier (auto-detected if None)

    Returns:
        True if the URI matches test patterns, False otherwise
    """
    return _is_test_path(uri, language=language)


def _filter_by_uri(
    items: list[dict[str, Any]],
    include_tests: bool = False,
    language: str | None = None,
    uri_key: str = "uri",
) -> list[dict[str, Any]]:
    """Filter out items with test URIs unless include_tests is True.

    Args:
        items: List of items with URI fields
        include_tests: If True, return all items without filtering
        language: Language identifier for pattern selection
        uri_key: Key name for URI field (default: "uri")

    Returns:
        Filtered list of items
    """
    if include_tests:
        return items

    return [
        item for item in items
        if not _is_test_uri(item.get(uri_key, ""), language=language)
    ]


def _filter_test_locations(
    locations: list[dict[str, Any]],
    include_tests: bool = False,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Filter out test locations unless include_tests is True.

    Args:
        locations: List of LSP location objects with 'uri' field
        include_tests: If True, return all locations without filtering
        language: Language identifier for pattern selection

    Returns:
        Filtered list of locations
    """
    return _filter_by_uri(locations, include_tests, language, uri_key="uri")


def _filter_test_symbols(
    symbols: list[dict[str, Any]],
    include_tests: bool = False,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Filter out symbols in test files unless include_tests is True.

    Args:
        symbols: List of LSP workspace symbol objects with 'location.uri' field
        include_tests: If True, return all symbols without filtering
        language: Language identifier for pattern selection

    Returns:
        Filtered list of symbols
    """
    if include_tests:
        return symbols

    return [
        sym
        for sym in symbols
        if not _is_test_uri(
            sym.get("location", {}).get("uri", ""),
            language=language
        )
    ]


def _filter_test_diagnostic_items(
    items: list[dict[str, Any]],
    include_tests: bool = False,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Filter out test file diagnostics from workspace results.

    Args:
        items: List of WorkspaceDiagnosticItem objects
        include_tests: If True, include test files
        language: Language identifier for pattern selection

    Returns:
        Filtered list of diagnostic items
    """
    return _filter_by_uri(items, include_tests, language, uri_key="uri")


def reload_config() -> None:
    """Reload configuration and clear cached filters.

    This function loads the test filter configuration from config.json
    and updates the language registry. If config loading fails or has no
    patterns, falls back to default configuration.
    """
    from llm_lsp_cli.config.defaults import DEFAULT_TEST_FILTER_CONFIG

    from .language_registry import get_registry

    # Clear the LRU cache
    _is_test_path.cache_clear()  # type: ignore[attr-defined]

    registry = get_registry()

    try:
        config = ConfigManager.load()
        if _config_has_patterns(config.test_filter):
            registry.configure(config.test_filter)
        else:
            registry.configure(DEFAULT_TEST_FILTER_CONFIG)
    except Exception:
        registry.configure(DEFAULT_TEST_FILTER_CONFIG)


def _config_has_patterns(config: TestFilterConfig) -> bool:
    """Check if the configuration has any test filter patterns.

    Args:
        config: TestFilterConfig to check

    Returns:
        True if any patterns are configured
    """
    return bool(
        config.languages
        or config.defaults.directory_patterns
        or config.defaults.suffix_patterns
        or config.defaults.prefix_patterns
    )


def _initialize_default_config() -> None:
    """Initialize the registry with default test filter patterns."""
    from llm_lsp_cli.config.defaults import DEFAULT_TEST_FILTER_CONFIG

    registry = get_registry()
    registry.configure(DEFAULT_TEST_FILTER_CONFIG)


# Initialize on import
_initialize_default_config()

# Export public API
__all__ = [
    "_is_test_path",
    "_filter_test_locations",
    "_filter_test_symbols",
    "_filter_test_diagnostic_items",
    "reload_config",
    "get_registry",
    "PatternSet",
    "PatternSource",
]
