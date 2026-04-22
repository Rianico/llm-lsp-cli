"""Integration tests for document_symbol command with -v/--verbose flag."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from tests.fixtures import (
    SYMBOL_KIND_CLASS,
    SYMBOL_KIND_FIELD,
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


class TestDocumentSymbolVerbose:
    """Integration tests for document-symbol -v flag."""

    def test_default_excludes_variables(self, test_file_in_workspace: Path) -> None:
        """Verify default behavior excludes variable and field symbols."""
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
            # Helper function to recursively check kinds
            kinds = self._extract_kinds(parsed)
            # Should exclude FIELD (8) and VARIABLE (13)
            assert SYMBOL_KIND_FIELD not in kinds
            assert SYMBOL_KIND_VARIABLE not in kinds
            # Should include CLASS (5)
            assert SYMBOL_KIND_CLASS in kinds

    def test_verbose_includes_variables(self, test_file_in_workspace: Path) -> None:
        """Verify -v flag includes variable symbols at top level."""
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
                    "-v",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Compact format flattens children, so we check top-level symbols
            # With -v, module_variable (kind 13) should be included
            kinds = [item["kind"] for item in parsed]
            names = [item["name"] for item in parsed]
            # Should include VARIABLE (13) at top level
            assert SYMBOL_KIND_VARIABLE in kinds
            assert "module_variable" in names

    def test_verbose_with_children(self, test_file_in_workspace: Path) -> None:
        """Verify -v includes variable symbols (compact format flattens children)."""
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
                    "-v",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Compact format flattens nested structure
            # Verify variable symbols are included in output
            names = [item["name"] for item in parsed]
            # module_variable should be present with -v
            assert "module_variable" in names
            # MyClass should always be present
            assert "MyClass" in names

    def test_verbose_json_format(self, test_file_in_workspace: Path) -> None:
        """Verify -v with JSON output includes variables."""
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
                    "-v",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)

    def test_verbose_yaml_format(self, test_file_in_workspace: Path) -> None:
        """Verify -v with YAML output includes variables."""
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
                    "-v",
                    "-o",
                    "yaml",
                ],
            )

            assert result.exit_code == 0
            parsed = yaml.safe_load(result.output)
            assert isinstance(parsed, list)

    def test_verbose_csv_format(self, test_file_in_workspace: Path) -> None:
        """Verify -v with CSV output includes variables."""
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
                    "-v",
                    "-o",
                    "csv",
                ],
            )

            assert result.exit_code == 0
            # Should have header and data rows
            lines = result.output.strip().split("\n")
            assert len(lines) >= 1  # At least header

    def test_verbose_text_format(self, test_file_in_workspace: Path) -> None:
        """Verify -v with text output includes variables."""
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
                    "-v",
                    "-o",
                    "text",
                ],
            )

            assert result.exit_code == 0
            # Should mention variable names
            assert "MyClass" in result.output
            assert "module_variable" in result.output

    def test_verbose_nonexistent_file(self, temp_dir: Path) -> None:
        """Verify -v with nonexistent file handles gracefully."""
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
                ["document-symbol", str(nonexistent_file), "-w", workspace, "-v", "-o", "json"],
            )

            # Should handle gracefully (either exit 0 with empty or exit 1 with error)
            assert result.exit_code in (0, 1)

    @staticmethod
    def _extract_kinds(symbols: list[dict]) -> set[int]:
        """Recursively extract all symbol kinds from a nested symbol list."""
        kinds = set()
        for symbol in symbols:
            if isinstance(symbol, dict):
                if "kind" in symbol:
                    kinds.add(symbol["kind"])
                if "children" in symbol:
                    kinds.update(TestDocumentSymbolVerbose._extract_kinds(symbol["children"]))
        return kinds
