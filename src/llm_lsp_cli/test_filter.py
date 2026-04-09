"""Test path filtering for LSP responses.

Provides utilities to detect and filter test files across multiple languages.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any


# =============================================================================
# Test Path Patterns (Expanded for multiple languages)
# =============================================================================

# Directory patterns (path contains these strings)
TEST_PATH_PATTERNS: tuple[str, ...] = (
    # Python, Rust, C/C++, generic
    "/tests/",
    "/test/",
    # JavaScript/TypeScript (Jest, Vitest convention)
    "/__tests__/",
    "/__test__/",
    # Java (Maven/Gradle convention)
    "/src/test/",
    "/src/tests/",
    "/test/java/",
    # C# (.NET convention)
    "/Tests/",
    "/Test/",
    # C/C++ (common conventions)
    "/unittests/",
    "/unittest/",
    # Ruby (RSpec, Jasmine)
    "/spec/",
    "/specs/",
)

# File suffix patterns (filename ends with these)
TEST_FILE_SUFFIXES: tuple[str, ...] = (
    # Go
    "_test.go",
    # JavaScript/TypeScript (Jest, Mocha, Vitest)
    ".test.js",
    ".test.ts",
    ".test.jsx",
    ".test.tsx",
    ".spec.js",
    ".spec.ts",
    ".spec.jsx",
    ".spec.tsx",
    # C# (NUnit, xUnit, MSTest)
    ".test.cs",
    ".tests.cs",
    ".spec.cs",
)

# File prefix patterns (filename starts with these)
TEST_FILE_PREFIXES: tuple[str, ...] = ("test_", "_test")

# Pre-compute lowercase versions for efficient matching
_TEST_PATH_PATTERNS_LOWER = tuple(p.lower() for p in TEST_PATH_PATTERNS)
_TEST_FILE_SUFFIXES_LOWER = tuple(p.lower() for p in TEST_FILE_SUFFIXES)
_TEST_FILE_PREFIXES_LOWER = tuple(p.lower() for p in TEST_FILE_PREFIXES)


@lru_cache(maxsize=1024)
def _is_test_path(uri: str) -> bool:
    """Check if a URI points to a test file or directory.

    Uses pattern matching on the URI path to detect test files.
    Results are cached for performance.

    Args:
        uri: LSP URI string (e.g., 'file:///path/to/file.py')

    Returns:
        True if the URI matches test patterns, False otherwise
    """
    if not uri:
        return False

    uri_lower = uri.lower()

    # Check directory patterns
    for pattern in _TEST_PATH_PATTERNS_LOWER:
        if pattern in uri_lower:
            return True

    # Check file suffix patterns
    for pattern in _TEST_FILE_SUFFIXES_LOWER:
        if uri_lower.endswith(pattern):
            return True

    # Check file prefix patterns (need to extract filename)
    try:
        # Parse URI to get path component
        if uri.startswith("file://"):
            path_str = uri[7:]  # Remove 'file://' prefix
        else:
            path_str = uri

        filename = Path(path_str).name.lower()
        for prefix in _TEST_FILE_PREFIXES_LOWER:
            if filename.startswith(prefix):
                return True
    except (ValueError, OSError):
        # If path parsing fails, skip prefix checks
        pass

    return False


def _filter_test_locations(
    locations: list[dict[str, Any]],
    include_tests: bool = False,
) -> list[dict[str, Any]]:
    """Filter out test locations unless include_tests is True.

    Args:
        locations: List of LSP location objects with 'uri' field
        include_tests: If True, return all locations without filtering

    Returns:
        Filtered list of locations
    """
    if include_tests:
        return locations

    return [loc for loc in locations if not _is_test_path(loc.get("uri", ""))]


def _filter_test_symbols(
    symbols: list[dict[str, Any]],
    include_tests: bool = False,
) -> list[dict[str, Any]]:
    """Filter out symbols in test files unless include_tests is True.

    Args:
        symbols: List of LSP workspace symbol objects with 'location.uri' field
        include_tests: If True, return all symbols without filtering

    Returns:
        Filtered list of symbols
    """
    if include_tests:
        return symbols

    return [sym for sym in symbols if not _is_test_path(sym.get("location", {}).get("uri", ""))]
