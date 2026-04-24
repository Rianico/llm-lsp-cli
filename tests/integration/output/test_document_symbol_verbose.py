"""Integration tests for document_symbol command with --depth option."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from tests.fixtures import (
    SYMBOL_KIND_CLASS,
    SYMBOL_KIND_FIELD,
    SYMBOL_KIND_METHOD,
    SYMBOL_KIND_VARIABLE,
    create_document_symbol_response_with_variables,
)

runner = CliRunner()


@pytest.fixture
def test_file_in_workspace(temp_dir: Path) -> Path:
    """Create a test file within a temp workspace."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    test_file = src_dir / "test_file.py"
    test_file.write_text("# Test file\n")
    return test_file


class TestDocumentSymbolDepth:
    """Integration tests for document-symbol --depth option."""

    def test_default_depth_includes_children(self, test_file_in_workspace: Path) -> None:
        """Verify default depth=1 includes class children."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                ["document-symbol", str(test_file_in_workspace), "-w", workspace, "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Helper function to recursively check kind_names
            kind_names = self._extract_kind_names(parsed)
            # With depth=1 (default), all symbols are included (no variable filtering at CLI level)
            assert "Class" in kind_names

    def test_depth_includes_all_symbols(self, test_file_in_workspace: Path) -> None:
        """Verify --depth option includes all symbols."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                    str(test_file_in_workspace),
                    "-w",
                    workspace,
                    "--depth",
                    "1",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # All symbols should be included (no variable filtering at CLI level)
            kind_names = [item["kind_name"] for item in parsed]
            names = [item["name"] for item in parsed]
            # Should include Variable since no filtering at CLI level
            assert "Variable" in kind_names
            assert "module_variable" in names

    def test_depth_with_children(self, test_file_in_workspace: Path) -> None:
        """Verify --depth includes nested children."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                    str(test_file_in_workspace),
                    "-w",
                    workspace,
                    "--depth",
                    "1",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Verify symbols are included in output
            names = [item["name"] for item in parsed]
            # module_variable should be present (no variable filtering at CLI level)
            assert "module_variable" in names
            # MyClass should always be present
            assert "MyClass" in names

    def test_depth_json_format(self, test_file_in_workspace: Path) -> None:
        """Verify --depth with JSON output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                    str(test_file_in_workspace),
                    "-w",
                    workspace,
                    "--depth",
                    "1",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)

    def test_depth_yaml_format(self, test_file_in_workspace: Path) -> None:
        """Verify --depth with YAML output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                    str(test_file_in_workspace),
                    "-w",
                    workspace,
                    "--depth",
                    "1",
                    "-o",
                    "yaml",
                ],
            )

            assert result.exit_code == 0
            parsed = yaml.safe_load(result.output)
            assert isinstance(parsed, list)

    def test_depth_csv_format(self, test_file_in_workspace: Path) -> None:
        """Verify --depth with CSV output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                    str(test_file_in_workspace),
                    "-w",
                    workspace,
                    "--depth",
                    "1",
                    "-o",
                    "csv",
                ],
            )

            assert result.exit_code == 0
            # Should have header and data rows
            lines = result.output.strip().split("\n")
            assert len(lines) >= 1  # At least header

    def test_depth_text_format(self, test_file_in_workspace: Path) -> None:
        """Verify --depth with text output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_document_symbol_response_with_variables()
        workspace = str(test_file_in_workspace.parent.parent)

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
                    str(test_file_in_workspace),
                    "-w",
                    workspace,
                    "--depth",
                    "1",
                    "-o",
                    "text",
                ],
            )

            assert result.exit_code == 0
            # Should mention symbol names
            assert "MyClass" in result.output
            assert "module_variable" in result.output

    def test_depth_nonexistent_file(self, temp_dir: Path) -> None:
        """Verify --depth with nonexistent file handles gracefully."""
        from llm_lsp_cli.cli import app

        mock_response = {"symbols": []}
        nonexistent_file = temp_dir / "missing.py"
        workspace = str(temp_dir)

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
                ["document-symbol", str(nonexistent_file), "-w", workspace, "--depth", "1", "-o", "json"],
            )

            # Should handle gracefully (either exit 0 with empty or exit 1 with error)
            assert result.exit_code in (0, 1)

    def test_depth_zero_shows_top_level_only(self, test_file_in_workspace: Path) -> None:
        """Verify --depth 0 shows only top-level symbols."""
        from llm_lsp_cli.cli import app

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
                        {"name": "method", "kind": SYMBOL_KIND_METHOD},
                        {"name": "field", "kind": SYMBOL_KIND_FIELD},
                    ],
                },
            ]
        }
        workspace = str(test_file_in_workspace.parent.parent)

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
                ["document-symbol", str(test_file_in_workspace), "-w", workspace, "--depth", "0", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Only top-level symbols, no children
            assert len(parsed) == 1
            assert parsed[0]["name"] == "MyClass"
            assert len(parsed[0]["children"]) == 0

    def test_depth_unlimited_shows_all(self, test_file_in_workspace: Path) -> None:
        """Verify --depth -1 shows all nested levels."""
        from llm_lsp_cli.cli import app

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
                        {
                            "name": "method",
                            "kind": SYMBOL_KIND_METHOD,
                            "children": [
                                {"name": "local_var", "kind": SYMBOL_KIND_VARIABLE},
                            ],
                        },
                        {"name": "field", "kind": SYMBOL_KIND_FIELD},
                    ],
                },
            ]
        }
        workspace = str(test_file_in_workspace.parent.parent)

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
                ["document-symbol", str(test_file_in_workspace), "-w", workspace, "--depth", "-1", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # All nested levels should be included
            assert len(parsed) == 1
            assert parsed[0]["name"] == "MyClass"
            assert len(parsed[0]["children"]) == 2

            # Method should have children
            method = [c for c in parsed[0]["children"] if c["name"] == "method"][0]
            assert len(method["children"]) == 1
            assert method["children"][0]["name"] == "local_var"

    @staticmethod
    def _extract_kind_names(symbols: list[dict]) -> set[str]:
        """Recursively extract all symbol kind_names from a nested symbol list."""
        kind_names = set()
        for symbol in symbols:
            if isinstance(symbol, dict):
                if "kind_name" in symbol:
                    kind_names.add(symbol["kind_name"])
                if "children" in symbol:
                    kind_names.update(TestDocumentSymbolDepth._extract_kind_names(symbol["children"]))
        return kind_names
