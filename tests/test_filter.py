"""Tests for test path filtering functionality."""

from __future__ import annotations

import pytest
from typing import Any

# These imports will fail initially - that's expected in RED phase
# from llm_lsp_cli.test_filter import (
#     _is_test_path,
#     _filter_test_locations,
#     _filter_test_symbols,
# )


class TestIsTestPath:
    """Tests for _is_test_path function."""

    def test_is_test_path_tests_directory(self) -> None:
        """Test detection of Python test directories."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/tests/test_file.py") is True
        assert _is_test_path("file:///project/tests/models.py") is True

    def test_is_test_path_test_directory(self) -> None:
        """Test detection of test directories."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/test/test_file.py") is True
        assert _is_test_path("file:///project/test/bar.py") is True

    def test_is_test_path_jest_tests(self) -> None:
        """Test detection of Jest __tests__ directory."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/__tests__/Component.test.tsx") is True
        assert _is_test_path("file:///project/src/__tests__/foo.ts") is True

    def test_is_test_path_java_maven(self) -> None:
        """Test detection of Java test directories."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/src/test/java/MyTest.java") is True
        assert _is_test_path("file:///project/src/tests/java/MyTest.java") is True

    def test_is_test_path_csharp_tests(self) -> None:
        """Test detection of C# test directories."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/Tests/MyTest.cs") is True
        assert _is_test_path("file:///project/Test/MyTest.cs") is True

    def test_is_test_path_go_test_file(self) -> None:
        """Test detection of Go test files."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/handler_test.go") is True
        assert _is_test_path("file:///project/utils/util_test.go") is True

    def test_is_test_path_typescript_test_file(self) -> None:
        """Test detection of TypeScript test files."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/component.test.ts") is True
        assert _is_test_path("file:///project/component.test.tsx") is True
        assert _is_test_path("file:///project/component.spec.ts") is True
        assert _is_test_path("file:///project/component.spec.tsx") is True

    def test_is_test_path_javascript_test_file(self) -> None:
        """Test detection of JavaScript test files."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/component.test.js") is True
        assert _is_test_path("file:///project/component.spec.js") is True
        assert _is_test_path("file:///project/component.test.jsx") is True
        assert _is_test_path("file:///project/component.spec.jsx") is True

    def test_is_test_path_csharp_test_file(self) -> None:
        """Test detection of C# test files."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/MyClass.test.cs") is True
        assert _is_test_path("file:///project/MyClass.tests.cs") is True
        assert _is_test_path("file:///project/MyClass.spec.cs") is True

    def test_is_test_path_python_prefix(self) -> None:
        """Test detection of Python test file prefix."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/test_utils.py") is True
        assert _is_test_path("file:///project/tests/test_models.py") is True

    def test_is_test_path_non_test_file(self) -> None:
        """Test that non-test files are not detected as tests."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/src/main.py") is False
        assert _is_test_path("file:///project/lib/utils.py") is False
        assert _is_test_path("file:///project/app.py") is False

    def test_is_test_path_case_insensitive(self) -> None:
        """Test that detection is case-insensitive."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/TESTS/test.py") is True
        assert _is_test_path("file:///project/Tests/test.py") is True
        assert _is_test_path("file:///project/Component.TEST.ts") is True

    def test_is_test_path_empty_uri(self) -> None:
        """Test that empty URI returns False."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("") is False

    def test_is_test_path_spec_directory(self) -> None:
        """Test detection of spec directories."""
        from llm_lsp_cli.test_filter import _is_test_path

        assert _is_test_path("file:///project/spec/component.spec.ts") is True
        assert _is_test_path("file:///project/specs/component.spec.ts") is True


class TestFilterTestLocations:
    """Tests for _filter_test_locations function."""

    def test_filter_test_locations_empty(self) -> None:
        """Test that empty locations list returns empty list."""
        from llm_lsp_cli.test_filter import _filter_test_locations

        result = _filter_test_locations([], include_tests=False)
        assert result == []

    def test_filter_test_locations_all_tests(self) -> None:
        """Test that all test locations are filtered out."""
        from llm_lsp_cli.test_filter import _filter_test_locations

        locations = [
            {"uri": "file:///tests/test_main.py"},
            {"uri": "file:///spec/utils.spec.ts"},
        ]
        result = _filter_test_locations(locations, include_tests=False)
        assert len(result) == 0

    def test_filter_test_locations_mixed(self) -> None:
        """Test that only test locations are filtered out."""
        from llm_lsp_cli.test_filter import _filter_test_locations

        locations = [
            {"uri": "file:///src/main.py"},
            {"uri": "file:///tests/test_main.py"},
            {"uri": "file:///lib/utils.py"},
            {"uri": "file:///spec/utils.spec.ts"},
        ]
        result = _filter_test_locations(locations, include_tests=False)
        assert len(result) == 2
        assert result[0]["uri"] == "file:///src/main.py"
        assert result[1]["uri"] == "file:///lib/utils.py"

    def test_filter_test_locations_include_true(self) -> None:
        """Test that include_tests=True returns all locations."""
        from llm_lsp_cli.test_filter import _filter_test_locations

        locations = [
            {"uri": "file:///src/main.py"},
            {"uri": "file:///tests/test_main.py"},
        ]
        result = _filter_test_locations(locations, include_tests=True)
        assert len(result) == 2

    def test_filter_test_locations_missing_uri(self) -> None:
        """Test that locations with missing URI are not filtered."""
        from llm_lsp_cli.test_filter import _filter_test_locations

        locations = [
            {"uri": "file:///src/main.py"},
            {},  # Missing uri
            {"range": {}},  # Missing uri
        ]
        result = _filter_test_locations(locations, include_tests=False)
        # Should not filter locations without uri (treated as non-test)
        assert len(result) == 3


class TestFilterTestSymbols:
    """Tests for _filter_test_symbols function."""

    def test_filter_test_symbols_empty(self) -> None:
        """Test that empty symbols list returns empty list."""
        from llm_lsp_cli.test_filter import _filter_test_symbols

        result = _filter_test_symbols([], include_tests=False)
        assert result == []

    def test_filter_test_symbols_all_tests(self) -> None:
        """Test that all test symbols are filtered out."""
        from llm_lsp_cli.test_filter import _filter_test_symbols

        symbols = [
            {"name": "TestClass", "location": {"uri": "file:///tests/test_main.py"}},
            {"name": "TestUtils", "location": {"uri": "file:///spec/utils.spec.ts"}},
        ]
        result = _filter_test_symbols(symbols, include_tests=False)
        assert len(result) == 0

    def test_filter_test_symbols_mixed(self) -> None:
        """Test that only test symbols are filtered out."""
        from llm_lsp_cli.test_filter import _filter_test_symbols

        symbols = [
            {"name": "MyClass", "location": {"uri": "file:///src/main.py"}},
            {"name": "TestClass", "location": {"uri": "file:///tests/test_main.py"}},
            {"name": "helper", "location": {"uri": "file:///lib/utils.py"}},
        ]
        result = _filter_test_symbols(symbols, include_tests=False)
        assert len(result) == 2
        assert result[0]["name"] == "MyClass"
        assert result[1]["name"] == "helper"

    def test_filter_test_symbols_include_true(self) -> None:
        """Test that include_tests=True returns all symbols."""
        from llm_lsp_cli.test_filter import _filter_test_symbols

        symbols = [
            {"name": "MyClass", "location": {"uri": "file:///src/main.py"}},
            {"name": "TestClass", "location": {"uri": "file:///tests/test_main.py"}},
        ]
        result = _filter_test_symbols(symbols, include_tests=True)
        assert len(result) == 2

    def test_filter_test_symbols_missing_location(self) -> None:
        """Test symbols with missing location URI."""
        from llm_lsp_cli.test_filter import _filter_test_symbols

        symbols = [
            {"name": "MyClass"},  # No location
            {"name": "Other", "location": {}},  # Empty location
            {"name": "Valid", "location": {"uri": "file:///src/main.py"}},
        ]
        result = _filter_test_symbols(symbols, include_tests=False)
        # Symbols with missing URI should not be treated as test paths
        assert len(result) == 3
