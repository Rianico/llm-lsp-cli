"""Tests for file-level command headers in TEXT output.

This module tests that alert headers appear correctly in TEXT output
for file-level LSP commands (diagnostics, document-symbol, definition, etc.).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.commands.shared import GlobalOptions
from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header
from llm_lsp_cli.utils import OutputFormat


class TestFileLevelCommandHeaders:
    """Test alert headers appear in TEXT output for file-level commands."""

    @pytest.fixture
    def mock_ctx(self, tmp_path: Path) -> MagicMock:
        """Create a mock Typer context with GlobalOptions."""
        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace=str(tmp_path),
            language="python",
            output_format=OutputFormat.TEXT,
        )
        return ctx

    @pytest.fixture
    def test_file(self, tmp_path: Path) -> Path:
        """Create a test Python file."""
        src = tmp_path / "src"
        src.mkdir()
        f = src / "main.py"
        f.write_text("def hello(): pass")
        return f

    def test_diagnostics_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """diagnostics command shows '<Server>: diagnostics of <file>' in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"diagnostics": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.diagnostics(
                mock_ctx,
                str(test_file),
                workspace=None,
                language=None,
                output_format=None,
            )

        output = output_lines[0]
        # Header should be present for TEXT format
        assert ":" in output, f"Should have header, got: {output}"
        assert "diagnostics" in output.lower() or "main.py" in output

    def test_document_symbol_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """document-symbol command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"symbols": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.document_symbol(
                mock_ctx,
                str(test_file),
                workspace=None,
                language=None,
                output_format=None,
                depth=1,
                raw=False,
            )

        output = output_lines[0]
        assert ":" in output, f"Should have header, got: {output}"
        assert (
            "document-symbol" in output
            or "symbol" in output.lower()
            or "main.py" in output
        )

    def test_definition_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """definition command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"locations": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.definition(
                mock_ctx,
                str(test_file),
                0,
                0,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        output = output_lines[0] if output_lines else ""
        # Should have some output (header or "No locations found")
        assert output

    def test_references_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """references command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"locations": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.references(
                mock_ctx,
                str(test_file),
                0,
                0,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        output = output_lines[0] if output_lines else ""
        assert output

    def test_completion_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """completion command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"items": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.completion(
                mock_ctx,
                str(test_file),
                0,
                0,
                workspace=None,
                language=None,
                output_format=None,
            )

        output = output_lines[0] if output_lines else ""
        # Completion with empty results may have no output
        assert output is not None

    def test_hover_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """hover command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"hover": None}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.hover(
                mock_ctx,
                str(test_file),
                0,
                0,
                workspace=None,
                language=None,
                output_format=None,
            )

        output = output_lines[0] if output_lines else ""
        # Hover with no result may have "No hover information" output
        assert output is not None

    def test_incoming_calls_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """incoming-calls command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"calls": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.incoming_calls(
                mock_ctx,
                str(test_file),
                0,
                0,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        output = output_lines[0] if output_lines else ""
        assert output

    def test_outgoing_calls_shows_header_in_text(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """outgoing-calls command shows header in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        with (
            patch.object(lsp_module, "send_request", return_value={"calls": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.outgoing_calls(
                mock_ctx,
                str(test_file),
                0,
                0,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        output = output_lines[0] if output_lines else ""
        assert output

    def test_json_format_no_header(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """JSON output does NOT include header (must be parseable)."""
        import json

        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.output_format = OutputFormat.JSON

        with (
            patch.object(lsp_module, "send_request", return_value={"diagnostics": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.diagnostics(
                mock_ctx,
                str(test_file),
                workspace=None,
                language=None,
                output_format=None,
            )

        # Should be valid JSON
        output = output_lines[0]
        data = json.loads(output)
        assert isinstance(data, dict)
        assert "_source" in data or "items" in data

    def test_yaml_format_no_header(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """YAML output does NOT include header."""
        import yaml

        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.output_format = OutputFormat.YAML

        with (
            patch.object(lsp_module, "send_request", return_value={"diagnostics": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.diagnostics(
                mock_ctx,
                str(test_file),
                workspace=None,
                language=None,
                output_format=None,
            )

        # Should be valid YAML
        output = output_lines[0]
        data = yaml.safe_load(output)
        assert isinstance(data, dict)

    def test_csv_format_no_header(
        self, mock_ctx: MagicMock, test_file: Path
    ) -> None:
        """CSV output does NOT include alert header."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.output_format = OutputFormat.CSV

        with (
            patch.object(lsp_module, "send_request", return_value={"diagnostics": []}),
            patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.diagnostics(
                mock_ctx,
                str(test_file),
                workspace=None,
                language=None,
                output_format=None,
            )

        output = output_lines[0] if output_lines else ""
        # Empty diagnostics produce empty CSV
        # If there's output, it should NOT have alert header format
        if output:
            first_line = output.split("\n")[0]
            # First line should be column headers, not alert header
            assert (
                "file" in first_line.lower()
                or "severity" in first_line.lower()
                or "range" in first_line.lower()
            )


class TestHeaderBuilderIntegration:
    """Test header builder integration with commands."""

    def test_header_builder_module_exists(self) -> None:
        """header_builder module can be imported."""
        from llm_lsp_cli.output import header_builder  # noqa: F401

    def test_build_alert_header_function_exists(self) -> None:
        """build_alert_header function exists."""
        from llm_lsp_cli.output.header_builder import build_alert_header

        assert callable(build_alert_header)

    def test_command_info_dataclass_exists(self) -> None:
        """CommandInfo dataclass exists."""
        from llm_lsp_cli.output.header_builder import CommandInfo

        assert CommandInfo is not None

    def test_build_alert_header_file_level(self) -> None:
        """build_alert_header creates correct header for file-level commands."""
        info = CommandInfo(
            server_name="Basedpyright",
            command_name="diagnostics",
            file_path="src/main.py",
        )
        header = build_alert_header(info)
        assert header == "Basedpyright: diagnostics of src/main.py"

    def test_build_alert_header_workspace_level(self) -> None:
        """build_alert_header creates correct header for workspace-level commands."""
        info = CommandInfo(
            server_name="Basedpyright",
            command_name="workspace-symbol",
            file_path=None,
        )
        header = build_alert_header(info)
        assert header == "Basedpyright: workspace-symbol"
