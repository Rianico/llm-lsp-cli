"""Integration tests for workspace_symbol command with -v/--verbose flag."""

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


class TestWorkspaceSymbolVerbose:
    """Integration tests for workspace-symbol -v flag."""

    def test_default_excludes_variables(self) -> None:
        """Verify default behavior excludes variable and field symbols."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Should exclude VARIABLE (13) and FIELD (8)
            kinds = [item["kind"] for item in parsed]
            assert SYMBOL_KIND_VARIABLE not in kinds
            assert SYMBOL_KIND_FIELD not in kinds
            # Should include CLASS (5) and FUNCTION (12)
            assert SYMBOL_KIND_CLASS in kinds
            assert SYMBOL_KIND_FUNCTION in kinds

    def test_verbose_includes_variables(self) -> None:
        """Verify -v flag includes variable and field symbols."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-v", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Should include all kinds
            kinds = [item["kind"] for item in parsed]
            assert SYMBOL_KIND_VARIABLE in kinds
            assert SYMBOL_KIND_FIELD in kinds
            assert SYMBOL_KIND_CLASS in kinds
            assert SYMBOL_KIND_FUNCTION in kinds

    def test_double_verbose_includes_all(self) -> None:
        """Verify -vv flag (DEBUG level) includes all symbols."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-vv", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            kinds = [item["kind"] for item in parsed]
            assert SYMBOL_KIND_VARIABLE in kinds
            assert SYMBOL_KIND_FIELD in kinds

    def test_verbose_with_include_tests(self) -> None:
        """Verify -v works together with --include-tests."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                [
                    "workspace-symbol",
                    "MyClass",
                    "-w",
                    "/tmp/test_workspace",
                    "-v",
                    "--include-tests",
                    "-o",
                    "json",
                ],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            # Both filters should work - variables included with -v
            kinds = [item["kind"] for item in parsed]
            assert SYMBOL_KIND_VARIABLE in kinds or SYMBOL_KIND_FIELD in kinds

    def test_verbose_json_format(self) -> None:
        """Verify -v with JSON output includes variables."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-v", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert isinstance(parsed, list)
            # Should have all 4 symbols
            assert len(parsed) == 4

    def test_verbose_yaml_format(self) -> None:
        """Verify -v with YAML output includes variables."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-v", "-o", "yaml"],
            )

            assert result.exit_code == 0
            parsed = yaml.safe_load(result.output)
            assert isinstance(parsed, list)
            assert len(parsed) == 4

    def test_verbose_csv_format(self) -> None:
        """Verify -v with CSV output includes variables."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-v", "-o", "csv"],
            )

            assert result.exit_code == 0
            lines = result.output.strip().split("\n")
            # Header + 4 data rows
            assert len(lines) == 5

    def test_verbose_text_format(self) -> None:
        """Verify -v with text output includes variables."""
        from llm_lsp_cli.cli import app

        mock_response = create_workspace_symbol_response_with_variables()

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
                ["workspace-symbol", "MyClass", "-w", "/tmp/test_workspace", "-v", "-o", "text"],
            )

            assert result.exit_code == 0
            # Should mention all symbol names
            assert "MyClass" in result.output
            assert "my_variable" in result.output
            assert "instance_field" in result.output
            assert "helper_function" in result.output

    def test_verbose_empty_results(self) -> None:
        """Verify -v with empty results handles gracefully."""
        from llm_lsp_cli.cli import app

        mock_response = {"symbols": []}

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
                ["workspace-symbol", "nonexistent", "-w", "/tmp/test_workspace", "-v", "-o", "json"],
            )

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert parsed == []
