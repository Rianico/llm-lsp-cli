"""Integration tests for filter chain (test_filter + symbol_filter)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from tests.fixtures import SYMBOL_KIND_CLASS, SYMBOL_KIND_FIELD, SYMBOL_KIND_VARIABLE

runner = CliRunner()


class TestFilterChainIntegration:
    """Tests for test_filter and symbol_filter working together."""

    def test_test_filter_then_symbol_filter(self) -> None:
        """Verify both filters are applied: test files excluded, then variables excluded."""
        from llm_lsp_cli.cli import app

        # Mock response with test file symbols including variables
        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}},
                    },
                },
                {
                    "name": "TestMyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 30, "character": 0}},
                    },
                },
                {
                    "name": "my_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/src/models.py",
                        "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 20}},
                    },
                },
                {
                    "name": "test_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///project/tests/test_models.py",
                        "range": {"start": {"line": 5, "character": 4}, "end": {"line": 5, "character": 20}},
                    },
                },
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # Default: exclude test files AND exclude variables
            result = runner.invoke(
                app,
                ["workspace-symbol", "MyClass", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Should exclude test file (TestMyClass, test_variable)
            names = [item["name"] for item in parsed]
            assert "TestMyClass" not in names
            assert "test_variable" not in names

            # Should exclude variable from source file
            assert "my_variable" not in names

            # Should only include MyClass
            assert len(parsed) == 1
            assert parsed[0]["name"] == "MyClass"

    def test_source_file_with_variables(self) -> None:
        """Verify source files: only symbol filter applied (variables excluded by default)."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}}},
                },
                {
                    "name": "my_variable",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 20}}},
                },
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(
                app,
                ["workspace-symbol", "MyClass", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Should exclude variable but include class
            names = [item["name"] for item in parsed]
            assert "my_variable" not in names
            assert "MyClass" in names

    def test_test_file_with_classes(self) -> None:
        """Verify test files: only test filter applied (class symbols pass through)."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "TestMyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {"uri": "file:///project/tests/test_models.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 30, "character": 0}}},
                },
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
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
                ["workspace-symbol", "TestMyClass", "-w", "/project", "--include-tests", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Should include test class
            names = [item["name"] for item in parsed]
            assert "TestMyClass" in names

    def test_filter_order_preserves_semantics(self) -> None:
        """Verify filter order: test_filter first, then symbol_filter."""
        from llm_lsp_cli.cli import app

        # Complex scenario: test files with variables, source files with variables
        mock_response = {
            "symbols": [
                # Source file symbols
                {"name": "SourceClass", "kind": SYMBOL_KIND_CLASS, "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}}}},
                {"name": "source_var", "kind": SYMBOL_KIND_VARIABLE, "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 20}}}},
                # Test file symbols
                {"name": "TestClass", "kind": SYMBOL_KIND_CLASS, "location": {"uri": "file:///project/tests/test_models.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 30, "character": 0}}}},
                {"name": "test_var", "kind": SYMBOL_KIND_VARIABLE, "location": {"uri": "file:///project/tests/test_models.py", "range": {"start": {"line": 5, "character": 4}, "end": {"line": 5, "character": 20}}}},
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # Default: exclude test files AND exclude variables
            result = runner.invoke(
                app,
                ["workspace-symbol", "Class", "-w", "/project", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Only SourceClass should remain
            names = [item["name"] for item in parsed]
            assert names == ["SourceClass"]

    def test_verbose_overrides_symbol_filter(self) -> None:
        """Verify -v flag: symbol filter disabled, all symbols included."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {"name": "MyClass", "kind": SYMBOL_KIND_CLASS, "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}}}},
                {"name": "my_variable", "kind": SYMBOL_KIND_VARIABLE, "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 20}}}},
                {"name": "my_field", "kind": SYMBOL_KIND_FIELD, "location": {"uri": "file:///project/src/models.py", "range": {"start": {"line": 5, "character": 8}, "end": {"line": 5, "character": 24}}}},
            ]
        }

        with patch("llm_lsp_cli.daemon.DaemonManager") as mock_manager, \
             patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_instance.is_running.return_value = True
            mock_manager.return_value = mock_instance

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # With -v, all symbols should be included
            result = runner.invoke(
                app,
                ["workspace-symbol", "MyClass", "-w", "/project", "-v", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # All 3 symbols should be present
            names = [item["name"] for item in parsed]
            assert len(parsed) == 3
            assert "MyClass" in names
            assert "my_variable" in names
            assert "my_field" in names
