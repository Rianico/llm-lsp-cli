"""Integration tests for filter chain (test_filter + symbol_filter)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from tests.fixtures import SYMBOL_KIND_CLASS, SYMBOL_KIND_FIELD, SYMBOL_KIND_VARIABLE

runner = CliRunner()


class TestFilterChainIntegration:
    """Tests for test_filter and symbol_filter working together."""

    def test_test_filter_excludes_test_files(self) -> None:
        """Verify test files are excluded by default."""
        from llm_lsp_cli.cli import app

        # Mock response with test file symbols
        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                },
                {
                    "name": "TestMyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 30, "character": 0},
                        },
                    },
                },
                {
                    "name": "my_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 10, "character": 4},
                            "end": {"line": 10, "character": 20},
                        },
                    },
                },
                {
                    "name": "test_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 5, "character": 20},
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

            # Default: exclude test files (variable-kind filtering no longer at CLI level)
            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "MyClass", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Should exclude test file symbols (TestMyClass, test_variable)
            names = [item["name"] for item in parsed]
            assert "TestMyClass" not in names
            assert "test_variable" not in names

            # Should include source file symbols
            assert "MyClass" in names
            assert "my_variable" in names
            assert len(parsed) == 2

    def test_source_file_with_all_symbols(self) -> None:
        """Verify source files return all symbols (no variable filtering at CLI level)."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                },
                {
                    "name": "my_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 10, "character": 4},
                            "end": {"line": 10, "character": 20},
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
                ["lsp", "workspace-symbol", "MyClass", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Should include both class and variable (no variable filtering at CLI level)
            names = [item["name"] for item in parsed]
            assert "my_variable" in names
            assert "MyClass" in names

    def test_test_file_with_classes(self) -> None:
        """Verify test files: only test filter applied (class symbols pass through)."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "TestMyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 30, "character": 0},
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

            # With --include-tests, test file classes should be included
            result = runner.invoke(
                app,
                [
                    "lsp",
                    "workspace-symbol",
                    "TestMyClass",
                    "-w",
                    "/project",
                    "--include-tests",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Should include test class
            names = [item["name"] for item in parsed]
            assert "TestMyClass" in names

    def test_filter_order_preserves_semantics(self) -> None:
        """Verify filter order: test_filter first."""
        from llm_lsp_cli.cli import app

        # Complex scenario: test files with variables, source files with variables
        mock_response = {
            "symbols": [
                # Source file symbols
                {
                    "name": "SourceClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                },
                {
                    "name": "source_var",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 10, "character": 4},
                            "end": {"line": 10, "character": 20},
                        },
                    },
                },
                # Test file symbols
                {
                    "name": "TestClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 30, "character": 0},
                        },
                    },
                },
                {
                    "name": "test_var",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 5, "character": 20},
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

            # Default: exclude test files (no variable filtering at CLI level)
            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "Class", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # SourceClass and source_var should remain (test symbols filtered)
            names = [item["name"] for item in parsed]
            assert set(names) == {"SourceClass", "source_var"}

    def test_include_tests_includes_all_source_files(self) -> None:
        """Verify --include-tests includes all symbols from both source and test files."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 50, "character": 0},
                        },
                    },
                },
                {
                    "name": "my_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 10, "character": 4},
                            "end": {"line": 10, "character": 20},
                        },
                    },
                },
                {
                    "name": "my_field",
                    "kind": SYMBOL_KIND_FIELD,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {
                            "start": {"line": 5, "character": 8},
                            "end": {"line": 5, "character": 24},
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

            # All symbols should be included (no variable filtering at CLI level)
            result = runner.invoke(
                app,
                ["lsp", "workspace-symbol", "MyClass", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # All 3 symbols should be present
            names = [item["name"] for item in parsed]
            assert len(parsed) == 3
            assert "MyClass" in names
            assert "my_variable" in names
            assert "my_field" in names
