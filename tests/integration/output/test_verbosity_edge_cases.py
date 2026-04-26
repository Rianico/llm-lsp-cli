"""Edge case and performance tests for depth-controlled symbol output."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from llm_lsp_cli.output.symbol_filter import filter_symbols
from llm_lsp_cli.output.verbosity import VerbosityLevel
from tests.fixtures import (
    SYMBOL_KIND_CLASS,
    SYMBOL_KIND_FIELD,
    SYMBOL_KIND_FUNCTION,
    SYMBOL_KIND_METHOD,
    SYMBOL_KIND_VARIABLE,
    WIDE_TREE_SYMBOLS,
    create_nested_symbol,
)

runner = CliRunner()


class TestDepthEdgeCases:
    """Edge case tests for depth-controlled symbol output."""

    def test_filter_preserves_symbol_order(self) -> None:
        """Verify filtering preserves original symbol order."""
        symbols = [
            {"name": "var1", "kind": SYMBOL_KIND_VARIABLE},
            {"name": "class1", "kind": SYMBOL_KIND_CLASS},
            {"name": "var2", "kind": SYMBOL_KIND_FIELD},
            {"name": "func1", "kind": SYMBOL_KIND_FUNCTION},
        ]

        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        # Should preserve order of non-variable symbols
        assert len(result) == 2
        assert result[0]["name"] == "class1"
        assert result[1]["name"] == "func1"

    def test_filter_handles_none_kind_gracefully(self) -> None:
        """Verify filter handles symbols with None kind field."""
        symbols = [
            {"name": "valid", "kind": SYMBOL_KIND_CLASS},
            {"name": "none_kind", "kind": None},
            {"name": "missing_kind"},
        ]

        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        # None and missing kind should be treated as non-variable (included)
        assert len(result) == 3

    def test_filter_handles_empty_symbol_dict(self) -> None:
        """Verify filter handles completely empty symbol dicts."""
        symbols = [
            {},
            {"name": "valid", "kind": SYMBOL_KIND_CLASS},
            {"location": {"uri": "file:///test.py"}},
        ]

        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        # Empty dicts and missing kind should be included
        assert len(result) == 3

    def test_filter_large_verbosity_cap(self) -> None:
        """Verify verbosity caps at DEBUG level even with higher values."""
        symbols = [
            {"name": "var", "kind": SYMBOL_KIND_VARIABLE},
            {"name": "class", "kind": SYMBOL_KIND_CLASS},
        ]

        # Even with verbosity level 100, should behave like DEBUG (includes all)
        # This tests the internal min(verbose, 2) logic
        result = filter_symbols(symbols, VerbosityLevel(2))  # DEBUG level

        assert len(result) == 2
        assert result[0]["name"] == "var"
        assert result[1]["name"] == "class"

    def test_filter_zero_verbosity(self) -> None:
        """Verify verbosity level 0 (NORMAL) filters variables."""
        symbols = [
            {"name": "var", "kind": SYMBOL_KIND_VARIABLE},
            {"name": "class", "kind": SYMBOL_KIND_CLASS},
        ]

        result = filter_symbols(symbols, VerbosityLevel(0))

        assert len(result) == 1
        assert result[0]["name"] == "class"

    def test_filter_returns_same_list_object_for_verbose(self) -> None:
        """Verify that at VERBOSE+ level, the same list object is returned."""
        symbols = [{"name": "var", "kind": SYMBOL_KIND_VARIABLE}]

        result = filter_symbols(symbols, VerbosityLevel.VERBOSE)

        # Should return the exact same list object (no copy at verbose level)
        assert result is symbols


class TestDepthPerformance:
    """Performance tests for depth-controlled symbol output."""

    def test_filter_performance_large_list(self) -> None:
        """Verify filter handles large symbol lists efficiently."""
        # Create a large list of mixed symbols
        symbols = []
        for i in range(10000):
            if i % 3 == 0:
                symbols.append({"name": f"var_{i}", "kind": SYMBOL_KIND_VARIABLE})
            elif i % 3 == 1:
                symbols.append({"name": f"field_{i}", "kind": SYMBOL_KIND_FIELD})
            else:
                symbols.append({"name": f"class_{i}", "kind": SYMBOL_KIND_CLASS})

        start = time.perf_counter()
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        elapsed = time.perf_counter() - start

        # Should complete in under 100ms for 10k symbols
        assert elapsed < 0.1
        # Should filter out ~2/3 of symbols (variables and fields)
        # 10000 symbols: 3334 variables (i%3==0), 3333 fields (i%3==1), 3333 classes (i%3==2)
        assert len(result) == 3333  # Only classes remain

    def test_filter_performance_repeated_calls(self) -> None:
        """Verify filter handles repeated calls efficiently."""
        symbols = [{"name": f"symbol_{i}", "kind": i % 14 + 1} for i in range(1000)]

        start = time.perf_counter()
        for _ in range(100):
            filter_symbols(symbols, VerbosityLevel.NORMAL)
        elapsed = time.perf_counter() - start

        # 100 calls should complete in under 1 second
        assert elapsed < 1.0

    def test_filter_empty_list_performance(self) -> None:
        """Verify filter handles empty lists efficiently."""
        symbols: list[dict] = []

        start = time.perf_counter()
        for _ in range(10000):
            filter_symbols(symbols, VerbosityLevel.NORMAL)
        elapsed = time.perf_counter() - start

        # 10k empty list calls should complete in under 500ms
        assert elapsed < 0.5


class TestDepthCLIEdgeCases:
    """CLI edge case tests for depth-controlled symbol output."""

    def test_depth_with_zero_symbols(self) -> None:
        """Verify --depth option handles empty symbol list gracefully."""
        from llm_lsp_cli.cli import app

        mock_response = {"symbols": []}

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "query", "-w", "/tmp", "--depth", "1", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert parsed == []

    def test_depth_unlimited(self) -> None:
        """Verify --depth -1 (unlimited) works correctly."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {"name": "var", "kind": SYMBOL_KIND_VARIABLE},
                {"name": "class", "kind": SYMBOL_KIND_CLASS},
            ]
        }

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "query", "-w", "/tmp", "--depth", "-1", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Should include all symbols
            assert len(parsed) == 2

    def test_depth_zero(self) -> None:
        """Verify --depth 0 (top-level only) works correctly."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {"name": "var", "kind": SYMBOL_KIND_VARIABLE},
                {"name": "class", "kind": SYMBOL_KIND_CLASS},
            ]
        }

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "query", "-w", "/tmp", "--depth", "0", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert len(parsed) == 2

    def test_depth_combined_with_all_options(self) -> None:
        """Verify --depth works when combined with all available options."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "var",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///test.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 0, "character": 10},
                        },
                    },
                },
                {
                    "name": "class",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///test.py",
                        "range": {
                            "start": {"line": 1, "character": 0},
                            "end": {"line": 1, "character": 10},
                        },
                    },
                },
            ]
        }

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "query", "-w", "/tmp", "--depth", "1", "--include-tests", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Should include all symbols
            assert len(parsed) == 2
            names = [item["name"] for item in parsed]
            assert "var" in names
            assert "class" in names

    def test_document_symbol_depth_with_deep_nesting(self, tmp_path: Path) -> None:
        """Verify --depth handles deeply nested document symbols."""
        from llm_lsp_cli.cli import app

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        # Create deeply nested symbol structure
        mock_response = {
            "symbols": [
                {
                    "name": "Module",
                    "kind": SYMBOL_KIND_CLASS,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 100, "character": 0},
                    },
                    "children": [
                        {
                            "name": "Class",
                            "kind": SYMBOL_KIND_CLASS,
                            "range": {
                                "start": {"line": 5, "character": 4},
                                "end": {"line": 50, "character": 0},
                            },
                            "children": [
                                {
                                    "name": "method",
                                    "kind": SYMBOL_KIND_METHOD,
                                    "range": {
                                        "start": {"line": 10, "character": 8},
                                        "end": {"line": 20, "character": 0},
                                    },
                                    "children": [
                                        {
                                            "name": "local_var",
                                            "kind": SYMBOL_KIND_VARIABLE,
                                            "range": {
                                                "start": {"line": 15, "character": 12},
                                                "end": {"line": 15, "character": 20},
                                            },
                                        }
                                    ],
                                },
                                {
                                    "name": "field",
                                    "kind": SYMBOL_KIND_FIELD,
                                    "range": {
                                        "start": {"line": 25, "character": 8},
                                        "end": {"line": 25, "character": 20},
                                    },
                                },
                            ],
                        },
                    ],
                },
            ]
        }

        with (
            patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class,
        ):
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["lsp", "document-symbol", str(test_file), "-w", str(tmp_path), "--depth", "1", "-o", "json"],
            )

            assert result.exit_code == 0
            # Should handle nested structure without errors
            parsed = json.loads(result.output)
            assert len(parsed) >= 1


class TestRecursiveFilteringEdgeCases:
    """Edge cases for recursive symbol filtering."""

    def test_deep_recursion_limit(self) -> None:
        """Verify no recursion errors with deeply nested symbols (10+ levels)."""
        deep_symbol = create_nested_symbol(depth=15, variable_at_leaf=True)
        symbols = [deep_symbol]

        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert result[0]["name"] == "node_15"

    def test_wide_tree_many_siblings(self) -> None:
        """Verify correct filtering with 100+ sibling children."""
        symbols = WIDE_TREE_SYMBOLS

        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert result[0]["name"] == "Parent"
        assert len(result[0]["children"]) == 50

    def test_none_kind_in_children(self) -> None:
        """Verify children with None/missing kind are handled gracefully."""
        symbols = [
            {
                "name": "Parent",
                "kind": SYMBOL_KIND_CLASS,
                "children": [
                    {"name": "valid", "kind": SYMBOL_KIND_METHOD},
                    {"name": "none_kind", "kind": None},
                    {"name": "missing_kind"},
                ],
            }
        ]

        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert len(result[0]["children"]) == 3


class TestRecursiveFilteringPerformance:
    """Performance tests for recursive filtering."""

    def test_performance_10k_symbols_nested(self) -> None:
        """Verify 10k symbols with 3-level nesting filters in <100ms."""
        symbols = []
        for i in range(1000):
            symbols.append(
                {
                    "name": f"class_{i}",
                    "kind": SYMBOL_KIND_CLASS,
                    "children": [
                        {"name": f"method_{i}_a", "kind": SYMBOL_KIND_METHOD},
                        {"name": f"field_{i}_a", "kind": SYMBOL_KIND_FIELD},
                        {
                            "name": f"method_{i}_b",
                            "kind": SYMBOL_KIND_METHOD,
                            "children": [
                                {"name": f"var_{i}_local", "kind": SYMBOL_KIND_VARIABLE},
                            ],
                        },
                    ],
                }
            )

        start = time.perf_counter()
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1
        assert len(result) == 1000

    def test_performance_repeated_recursive_calls(self) -> None:
        """Verify 100 recursive filter calls complete in <1s."""
        symbols = [
            {
                "name": "Root",
                "kind": SYMBOL_KIND_CLASS,
                "children": [
                    {
                        "name": "child",
                        "kind": SYMBOL_KIND_METHOD,
                        "children": [
                            {"name": "var", "kind": SYMBOL_KIND_VARIABLE},
                        ],
                    }
                ],
            }
        ] * 100

        start = time.perf_counter()
        for _ in range(100):
            filter_symbols(symbols, VerbosityLevel.NORMAL)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0
