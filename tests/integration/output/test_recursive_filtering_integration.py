"""Integration tests for recursive children filtering through CLI.

These tests verify that the recursive filtering of nested symbol children
works correctly end-to-end through the CLI, not just at the unit level.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from tests.fixtures import (
    SYMBOL_KIND_CLASS,
    SYMBOL_KIND_FIELD,
    SYMBOL_KIND_FUNCTION,
    SYMBOL_KIND_METHOD,
    SYMBOL_KIND_MODULE,
    SYMBOL_KIND_VARIABLE,
)

runner = CliRunner()


class TestDocumentSymbolRecursiveFiltering:
    """Integration tests for recursive filtering with document-symbol command."""

    def test_nested_class_fields_filtered_at_normal_verbosity(self, tmp_path: Path) -> None:
        """Verify document-symbol: nested class fields are filtered at NORMAL verbosity."""
        from llm_lsp_cli.cli import app

        # Create a test file within the workspace boundary
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                    "children": [
                        {"name": "__init__", "kind": SYMBOL_KIND_METHOD},
                        {"name": "instance_field", "kind": SYMBOL_KIND_FIELD},
                        {"name": "my_method", "kind": SYMBOL_KIND_METHOD},
                        {"name": "another_field", "kind": SYMBOL_KIND_FIELD},
                    ],
                },
            ],
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
                ["document-symbol", str(test_file), "-w", str(tmp_path), "-o", "json", "--raw"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            assert len(parsed) == 1
            class_symbol = parsed[0]
            assert class_symbol["name"] == "MyClass"
            assert "children" in class_symbol

            # Should only have methods, not fields
            children_names = [c["name"] for c in class_symbol["children"]]
            assert "__init__" in children_names
            assert "my_method" in children_names
            assert "instance_field" not in children_names
            assert "another_field" not in children_names
            assert len(class_symbol["children"]) == 2

    def test_nested_class_fields_included_at_verbose_verbosity(self, tmp_path: Path) -> None:
        """Verify document-symbol: -v includes all nested class fields."""
        from llm_lsp_cli.cli import app

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                    "children": [
                        {"name": "__init__", "kind": SYMBOL_KIND_METHOD},
                        {"name": "instance_field", "kind": SYMBOL_KIND_FIELD},
                        {"name": "my_method", "kind": SYMBOL_KIND_METHOD},
                    ],
                },
            ],
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
                [
                    "document-symbol",
                    str(test_file),
                    "-w",
                    str(tmp_path),
                    "-v",
                    "-o",
                    "json",
                    "--raw",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            assert len(parsed) == 1
            class_symbol = parsed[0]
            assert class_symbol["name"] == "MyClass"
            assert len(class_symbol["children"]) == 3

            children_names = [c["name"] for c in class_symbol["children"]]
            assert "__init__" in children_names
            assert "instance_field" in children_names
            assert "my_method" in children_names


class TestDeepNestedRecursiveFiltering:
    """Integration tests for deeply nested recursive filtering."""

    def test_three_level_nesting_filters_at_all_levels(self, tmp_path: Path) -> None:
        """Verify document-symbol: 3-level nesting filters variables at all levels."""
        from llm_lsp_cli.cli import app

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        # Module -> Class -> Method -> Local Variable
        # At NORMAL: Module, Class, Method should remain; Local Variable filtered
        mock_response = {
            "symbols": [
                {
                    "name": "mymodule",
                    "kind": SYMBOL_KIND_MODULE,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 100, "character": 0},
                    },
                    "children": [
                        {
                            "name": "MyClass",
                            "kind": SYMBOL_KIND_CLASS,
                            "range": {
                                "start": {"line": 5, "character": 0},
                                "end": {"line": 50, "character": 0},
                            },
                            "children": [
                                {
                                    "name": "my_method",
                                    "kind": SYMBOL_KIND_METHOD,
                                    "range": {
                                        "start": {"line": 10, "character": 4},
                                        "end": {"line": 30, "character": 0},
                                    },
                                    "children": [
                                        {"name": "local_var", "kind": SYMBOL_KIND_VARIABLE},
                                        {"name": "another_local", "kind": SYMBOL_KIND_VARIABLE},
                                    ],
                                },
                                {
                                    "name": "class_field",
                                    "kind": SYMBOL_KIND_FIELD,
                                    "range": {
                                        "start": {"line": 6, "character": 8},
                                        "end": {"line": 6, "character": 20},
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
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
                ["document-symbol", str(test_file), "-w", str(tmp_path), "-o", "json", "--raw"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            assert len(parsed) == 1
            module = parsed[0]
            assert module["name"] == "mymodule"
            assert len(module["children"]) == 1

            my_class = module["children"][0]
            assert my_class["name"] == "MyClass"
            assert len(my_class["children"]) == 1  # Only method, field filtered

            method = my_class["children"][0]
            assert method["name"] == "my_method"
            assert len(method["children"]) == 0  # Both local vars filtered

    def test_deep_nesting_verbose_includes_all(self, tmp_path: Path) -> None:
        """Verify document-symbol: -v includes all 3-level nested symbols."""
        from llm_lsp_cli.cli import app

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        mock_response = {
            "symbols": [
                {
                    "name": "mymodule",
                    "kind": SYMBOL_KIND_MODULE,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 100, "character": 0},
                    },
                    "children": [
                        {
                            "name": "MyClass",
                            "kind": SYMBOL_KIND_CLASS,
                            "range": {
                                "start": {"line": 5, "character": 0},
                                "end": {"line": 50, "character": 0},
                            },
                            "children": [
                                {
                                    "name": "my_method",
                                    "kind": SYMBOL_KIND_METHOD,
                                    "range": {
                                        "start": {"line": 10, "character": 4},
                                        "end": {"line": 30, "character": 0},
                                    },
                                    "children": [
                                        {"name": "local_var", "kind": SYMBOL_KIND_VARIABLE},
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
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
                [
                    "document-symbol",
                    str(test_file),
                    "-w",
                    str(tmp_path),
                    "-v",
                    "-o",
                    "json",
                    "--raw",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            assert len(parsed) == 1
            module = parsed[0]
            assert module["name"] == "mymodule"

            my_class = module["children"][0]
            assert my_class["name"] == "MyClass"

            method = my_class["children"][0]
            assert method["name"] == "my_method"
            assert len(method["children"]) == 1  # local_var included
            assert method["children"][0]["name"] == "local_var"


class TestMultiBranchRecursiveFiltering:
    """Integration tests for recursive filtering with multiple branches."""

    def test_multiple_children_branches_filtered_correctly(self, tmp_path: Path) -> None:
        """Verify document-symbol: multiple children branches all filtered correctly."""
        from llm_lsp_cli.cli import app

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 100, "character": 0},
                    },
                    "children": [
                        {
                            "name": "method_a",
                            "kind": SYMBOL_KIND_METHOD,
                            "children": [
                                {"name": "var_a", "kind": SYMBOL_KIND_VARIABLE},
                            ],
                        },
                        {
                            "name": "method_b",
                            "kind": SYMBOL_KIND_METHOD,
                            "children": [
                                {"name": "func_b", "kind": SYMBOL_KIND_FUNCTION},
                            ],
                        },
                        {
                            "name": "field_c",
                            "kind": SYMBOL_KIND_FIELD,
                            "children": [],
                        },
                    ],
                },
            ],
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
                ["document-symbol", str(test_file), "-w", str(tmp_path), "-o", "json", "--raw"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            assert len(parsed) == 1
            my_class = parsed[0]
            assert my_class["name"] == "MyClass"
            assert len(my_class["children"]) == 2  # method_a, method_b; field_c filtered

            children_names = [c["name"] for c in my_class["children"]]
            assert "method_a" in children_names
            assert "method_b" in children_names
            assert "field_c" not in children_names

            # method_a's children should be filtered (var_a removed)
            method_a = [c for c in my_class["children"] if c["name"] == "method_a"][0]
            assert len(method_a["children"]) == 0

            # method_b's children should pass through (func_b is FUNCTION, not VARIABLE)
            method_b = [c for c in my_class["children"] if c["name"] == "method_b"][0]
            assert len(method_b["children"]) == 1
            assert method_b["children"][0]["name"] == "func_b"


class TestWorkspaceSymbolRecursiveFiltering:
    """Integration tests for recursive filtering with workspace-symbol command."""

    def test_workspace_symbol_flat_no_children(self) -> None:
        """Verify workspace-symbol: flat symbols (no children) filter correctly."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///test.py",
                        "range": {"start": {"line": 0}, "end": {"line": 50}},
                    },
                },
                {
                    "name": "my_function",
                    "kind": SYMBOL_KIND_FUNCTION,
                    "location": {
                        "uri": "file:///test.py",
                        "range": {"start": {"line": 55}, "end": {"line": 70}},
                    },
                },
                {
                    "name": "module_var",
                    "kind": SYMBOL_KIND_VARIABLE,
                    "location": {
                        "uri": "file:///test.py",
                        "range": {"start": {"line": 5}, "end": {"line": 5}},
                    },
                },
            ],
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
                ["workspace-symbol", "test", "-w", "/tmp", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            names = [item["name"] for item in parsed]
            assert "MyClass" in names
            assert "my_function" in names
            assert "module_var" not in names  # Filtered out
            assert len(parsed) == 2


class TestRecursiveFilteringWithTestData:
    """Integration tests for recursive filtering with test files."""

    def test_include_tests_with_nested_variables(self) -> None:
        """Verify --include-tests with nested symbols: test files included, nested vars still filtered."""
        from llm_lsp_cli.cli import app

        mock_response = {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///src/models.py",
                        "range": {"start": {"line": 0}, "end": {"line": 50}},
                    },
                    "children": [
                        {"name": "field", "kind": SYMBOL_KIND_FIELD},
                        {"name": "method", "kind": SYMBOL_KIND_METHOD},
                    ],
                },
                {
                    "name": "TestMyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "location": {
                        "uri": "file:///tests/test_models.py",
                        "range": {"start": {"line": 0}, "end": {"line": 30}},
                    },
                    "children": [
                        {"name": "test_field", "kind": SYMBOL_KIND_FIELD},
                        {"name": "test_method", "kind": SYMBOL_KIND_METHOD},
                    ],
                },
            ],
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

            # With --include-tests but without -v
            result = runner.invoke(
                app,
                [
                    "workspace-symbol",
                    "Class",
                    "-w",
                    "/tmp",
                    "--include-tests",
                    "-o",
                    "json",
                    "--raw",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            assert len(parsed) == 2

            # MyClass children filtered (field removed)
            my_class = [s for s in parsed if s["name"] == "MyClass"][0]
            assert len(my_class["children"]) == 1
            assert my_class["children"][0]["name"] == "method"

            # TestMyClass children also filtered (test_field removed)
            test_class = [s for s in parsed if s["name"] == "TestMyClass"][0]
            assert len(test_class["children"]) == 1
            assert test_class["children"][0]["name"] == "test_method"
