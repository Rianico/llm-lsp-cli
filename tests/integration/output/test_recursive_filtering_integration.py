"""Integration tests for depth-controlled symbol output through CLI.

These tests verify that the depth-controlled traversal of nested symbol children
works correctly end-to-end through the CLI.
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


class TestDocumentSymbolDepthControl:
    """Integration tests for depth control with document-symbol command."""

    def test_nested_class_with_default_depth(self, tmp_path: Path) -> None:
        """Verify document-symbol: default depth=1 shows class + direct children."""
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
                ["lsp", "document-symbol", str(test_file), "-w", str(tmp_path), "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Now wrapped with _source field
            assert "_source" in parsed
            items = parsed["items"]
            assert len(items) == 1
            class_symbol = items[0]
            assert class_symbol["name"] == "MyClass"
            assert "children" in class_symbol

            # Should have all 4 children (no variable filtering at CLI level)
            children_names = [c["name"] for c in class_symbol["children"]]
            assert "__init__" in children_names
            assert "my_method" in children_names
            assert "instance_field" in children_names
            assert "another_field" in children_names
            assert len(class_symbol["children"]) == 4

    def test_depth_zero_shows_top_level_only(self, tmp_path: Path) -> None:
        """Verify document-symbol: --depth 0 shows only top-level symbols."""
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
                [
                    "lsp",
                    "document-symbol",
                    str(test_file),
                    "-w",
                    str(tmp_path),
                    "--depth",
                    "0",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Now wrapped with _source field
            assert "_source" in parsed
            items = parsed["items"]
            assert len(items) == 1
            class_symbol = items[0]
            assert class_symbol["name"] == "MyClass"
            # No children with depth 0
            assert len(class_symbol["children"]) == 0

    def test_depth_unlimited_shows_all_levels(self, tmp_path: Path) -> None:
        """Verify document-symbol: --depth -1 shows all nested levels."""
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
                [
                    "lsp",
                    "document-symbol",
                    str(test_file),
                    "-w",
                    str(tmp_path),
                    "--depth",
                    "-1",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Now wrapped with _source field
            assert "_source" in parsed
            items = parsed["items"]
            assert len(items) == 1
            module = items[0]
            assert module["name"] == "mymodule"

            my_class = module["children"][0]
            assert my_class["name"] == "MyClass"

            method = my_class["children"][0]
            assert method["name"] == "my_method"
            assert len(method["children"]) == 1  # local_var included
            assert method["children"][0]["name"] == "local_var"


class TestDeepNestedDepthControl:
    """Integration tests for deeply nested depth control."""

    def test_three_level_nesting_with_depth_2(self, tmp_path: Path) -> None:
        """Verify document-symbol: --depth 2 shows 3 levels but not 4th level (method children)."""
        from llm_lsp_cli.cli import app

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        # Module -> Class -> Method -> Local Variable
        # depth=2 means: Module (depth=2) -> Class (depth=1) -> Method (depth=0, no children)
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
                ["lsp", "document-symbol", str(test_file), "-w", str(tmp_path), "--depth", "2", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Now wrapped with _source field
            assert "_source" in parsed
            items = parsed["items"]
            assert len(items) == 1
            module = items[0]
            assert module["name"] == "mymodule"
            assert len(module["children"]) == 1

            my_class = module["children"][0]
            assert my_class["name"] == "MyClass"
            assert len(my_class["children"]) == 2  # method and field

            method = my_class["children"][0]
            assert method["name"] == "my_method"
            # With depth 2, method's children are NOT traversed (depth becomes 0 at method level)
            assert len(method["children"]) == 0

    def test_four_level_nesting_with_depth_3(self, tmp_path: Path) -> None:
        """Verify document-symbol: --depth 3 shows 4 levels including method children."""
        from llm_lsp_cli.cli import app

        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\n")

        # Module -> Class -> Method -> Local Variable
        # depth=3 means: Module (depth=3) -> Class (depth=2) -> Method (depth=1) -> Local (depth=0)
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
                ["lsp", "document-symbol", str(test_file), "-w", str(tmp_path), "--depth", "3", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Now wrapped with _source field
            assert "_source" in parsed
            items = parsed["items"]
            assert len(items) == 1
            module = items[0]
            assert module["name"] == "mymodule"

            my_class = module["children"][0]
            assert my_class["name"] == "MyClass"

            method = my_class["children"][0]
            assert method["name"] == "my_method"
            # With depth 3, method's children ARE traversed
            assert len(method["children"]) == 2
            assert method["children"][0]["name"] == "local_var"


class TestMultiBranchDepthControl:
    """Integration tests for depth control with multiple branches."""

    def test_multiple_children_branches_with_depth_control(self, tmp_path: Path) -> None:
        """Verify document-symbol: multiple children branches all traverse correctly."""
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
                ["lsp", "document-symbol", str(test_file), "-w", str(tmp_path), "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Now wrapped with _source field
            assert "_source" in parsed
            items = parsed["items"]
            assert len(items) == 1
            my_class = items[0]
            assert my_class["name"] == "MyClass"
            # All 3 children at depth 1
            assert len(my_class["children"]) == 3

            children_names = [c["name"] for c in my_class["children"]]
            assert "method_a" in children_names
            assert "method_b" in children_names
            assert "field_c" in children_names

            # method_a's children should be included at depth 2 (default is 1, so no grandchildren)
            method_a = [c for c in my_class["children"] if c["name"] == "method_a"][0]
            assert len(method_a["children"]) == 0  # No grandchildren at depth 1

            # method_b's children same
            method_b = [c for c in my_class["children"] if c["name"] == "method_b"][0]
            assert len(method_b["children"]) == 0  # No grandchildren at depth 1


class TestWorkspaceSymbolDepthControl:
    """Integration tests for depth control with workspace-symbol command."""

    def test_workspace_symbol_flat_no_children(self) -> None:
        """Verify workspace-symbol: flat symbols (no children) work with --depth."""
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
                ["lsp", "workspace-symbol", "test", "-w", "/tmp", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Wrapped with _source and files
            assert "_source" in parsed
            files = parsed["files"]

            # Flatten symbols from grouped output
            all_symbols = []
            for group in files:
                all_symbols.extend(group.get("symbols", []))

            names = [item["name"] for item in all_symbols]
            assert "MyClass" in names
            assert "my_function" in names
            assert "module_var" in names  # Included (no variable filtering at CLI level)
            assert len(all_symbols) == 3


class TestDepthControlWithTestData:
    """Integration tests for depth control with test files."""

    def test_include_tests_with_nested_symbols(self) -> None:
        """Verify --include-tests with nested symbols includes both source and test."""
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
                [
                    "lsp",
                    "workspace-symbol",
                    "Class",
                    "-w",
                    "/tmp",
                    "--include-tests",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)

            # Wrapped with _source and files
            assert "_source" in parsed
            files = parsed["files"]

            # Flatten symbols from grouped output
            all_symbols = []
            for group in files:
                all_symbols.extend(group.get("symbols", []))

            assert len(all_symbols) == 2

            # MyClass children included
            my_class = [s for s in all_symbols if s["name"] == "MyClass"][0]
            assert len(my_class["children"]) == 2
            children_names = [c["name"] for c in my_class["children"]]
            assert "field" in children_names
            assert "method" in children_names

            # TestMyClass children included
            test_class = [s for s in all_symbols if s["name"] == "TestMyClass"][0]
            assert len(test_class["children"]) == 2
            test_children_names = [c["name"] for c in test_class["children"]]
            assert "test_field" in test_children_names
            assert "test_method" in test_children_names
