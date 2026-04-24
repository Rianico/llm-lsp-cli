"""Integration tests for workspace_symbol command with --depth option."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import yaml
from typer.testing import CliRunner

from tests.fixtures import (
    SYMBOL_KIND_CLASS,
    SYMBOL_KIND_FIELD,
    SYMBOL_KIND_FUNCTION,
    SYMBOL_KIND_VARIABLE,
    create_workspace_symbol_response_with_variables,
)

runner = CliRunner()


class TestWorkspaceSymbolDepth:
    """Integration tests for workspace-symbol --depth option.

    Note: Workspace symbols are flat by LSP spec (no children), so --depth has no effect.
    These tests verify the option is accepted and symbols are returned correctly.
    """

    def test_default_depth_returns_symbols(self) -> None:
        """Verify default behavior returns all symbols."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # All symbols should be included (workspace symbols are flat, no filtering by kind)
            assert len(parsed) == 4
            kind_names = [item["kind_name"] for item in parsed]
            assert "Class" in kind_names
            assert "Function" in kind_names
            assert "Variable" in kind_names
            assert "Field" in kind_names

    def test_depth_option_accepted(self) -> None:
        """Verify --depth option is accepted (even though workspace symbols are flat)."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "--depth", "-1", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert len(parsed) == 4

    def test_depth_with_include_tests(self) -> None:
        """Verify --depth works together with --include-tests."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                    "workspace-symbol",
                    "MyClass",
                    "-w",
                    "/tmp/test_workspace",
                    "--depth",
                    "1",
                    "--include-tests",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert len(parsed) == 4

    def test_depth_json_format(self) -> None:
        """Verify --depth with JSON output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "--depth", "1", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)
            assert len(parsed) == 4

    def test_depth_yaml_format(self) -> None:
        """Verify --depth with YAML output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "--depth", "1", "-o", "yaml"],
            )

            assert result.exit_code == 0
            parsed = yaml.safe_load(result.output)
            assert isinstance(parsed, list)
            assert len(parsed) == 4

    def test_depth_csv_format(self) -> None:
        """Verify --depth with CSV output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "--depth", "1", "-o", "csv"],
            )

            assert result.exit_code == 0
            lines = result.output.strip().split("\n")
            # Header + 4 data rows
            assert len(lines) == 5

    def test_depth_text_format(self) -> None:
        """Verify --depth with text output works."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "--depth", "1", "-o", "text"],
            )

            assert result.exit_code == 0
            # Should mention all symbol names
            assert "MyClass" in result.output
            assert "my_variable" in result.output
            assert "instance_field" in result.output
            assert "helper_function" in result.output

    def test_depth_empty_results(self) -> None:
        """Verify --depth with empty results handles gracefully."""
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
                [
                    "workspace-symbol",
                    "nonexistent",
                    "-w",
                    "/tmp/test_workspace",
                    "--depth",
                    "1",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert parsed == []
