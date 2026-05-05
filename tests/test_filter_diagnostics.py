"""Tests for diagnostic filtering in test_filter module."""

from llm_lsp_cli.test_filter import filter_test_diagnostic_items


class TestFilterDiagnosticItems:
    """Tests for filter_test_diagnostic_items function."""

    def testfilter_test_diagnostic_items(self) -> None:
        """Test that test file diagnostics are filtered out by default."""
        items = [
            {
                "uri": "file:///project/src/main.py",
                "version": 1,
                "diagnostics": [{"severity": 1, "message": "Source error"}],
            },
            {
                "uri": "file:///project/tests/test_main.py",
                "version": 1,
                "diagnostics": [{"severity": 1, "message": "Test error"}],
            },
        ]

        # Filter out test files
        filtered = filter_test_diagnostic_items(items, include_tests=False)

        assert len(filtered) == 1
        assert "main.py" in filtered[0]["uri"]
        assert "test" not in filtered[0]["uri"]

    def testfilter_test_diagnostic_items_include_tests(self) -> None:
        """Test that include_tests=True returns all diagnostic items."""
        items = [
            {
                "uri": "file:///project/src/main.py",
                "version": 1,
                "diagnostics": [{"severity": 1, "message": "Source error"}],
            },
            {
                "uri": "file:///project/tests/test_main.py",
                "version": 1,
                "diagnostics": [{"severity": 1, "message": "Test error"}],
            },
        ]

        # Include test files
        filtered = filter_test_diagnostic_items(items, include_tests=True)

        assert len(filtered) == 2

    def testfilter_test_diagnostic_items_empty(self) -> None:
        """Test that empty items list returns empty list."""
        filtered = filter_test_diagnostic_items([], include_tests=False)
        assert filtered == []

    def testfilter_test_diagnostic_items_no_test_files(self) -> None:
        """Test filtering when no test files are present."""
        items = [
            {
                "uri": "file:///project/src/main.py",
                "version": 1,
                "diagnostics": [{"severity": 1, "message": "Source error"}],
            },
            {
                "uri": "file:///project/src/utils.py",
                "version": 1,
                "diagnostics": [{"severity": 2, "message": "Source warning"}],
            },
        ]

        filtered = filter_test_diagnostic_items(items, include_tests=False)

        # All items should be retained (no test files)
        assert len(filtered) == 2
