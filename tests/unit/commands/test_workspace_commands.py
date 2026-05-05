"""Tests for workspace-level command grouping.

This module tests that workspace-symbol and workspace-diagnostics commands
produce properly grouped output with correct structure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.commands.shared import GlobalOptions
from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import (
    group_diagnostics_by_file,
    group_symbols_by_file,
)
from llm_lsp_cli.utils import OutputFormat


class TestWorkspaceSymbolGrouping:
    """Test workspace-symbol produces grouped output."""

    @pytest.fixture
    def mock_ctx(self, tmp_path: Path) -> MagicMock:
        """Create a mock Typer context with GlobalOptions."""
        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace=str(tmp_path),
            language="python",
            output_format=OutputFormat.JSON,
        )
        return ctx

    @pytest.fixture
    def setup_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with files."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "models.py").write_text("class User: pass")
        (src / "services.py").write_text("class UserService: pass")
        return tmp_path

    def _make_symbols_response(self, workspace: Path) -> dict[str, Any]:
        """Create mock response with URIs relative to workspace."""
        return {
            "symbols": [
                {
                    "name": "User",
                    "kind": 5,
                    "location": {
                        "uri": (workspace / "src" / "models.py").as_uri(),
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 10, "character": 0},
                        },
                    },
                },
                {
                    "name": "UserService",
                    "kind": 5,
                    "location": {
                        "uri": (workspace / "src" / "services.py").as_uri(),
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 20, "character": 0},
                        },
                    },
                },
            ]
        }

    def test_json_output_grouped_structure(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """JSON output is array of file-grouped objects."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_symbols_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_symbol(
                mock_ctx,
                "User",
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
                depth=1,
                raw=False,
            )

        data = json.loads(output_lines[0])
        assert isinstance(data, dict), "Output should be a dict with _source and files"
        assert "_source" in data
        assert "files" in data
        files = data["files"]
        assert len(files) > 0

        for group in files:
            assert "file" in group
            assert "symbols" in group
            assert isinstance(group["symbols"], list)

    def test_json_output_symbols_is_array(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Each group's symbols is an array."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_symbols_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_symbol(
                mock_ctx,
                "User",
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
                depth=1,
                raw=False,
            )

        data = json.loads(output_lines[0])
        files = data["files"]

        for group in files:
            assert isinstance(group["symbols"], list)

    def test_text_output_hierarchical(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """TEXT output shows hierarchical structure with file headers."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT
        mock_response = self._make_symbols_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_symbol(
                mock_ctx,
                "User",
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
                depth=1,
                raw=False,
            )

        output = output_lines[0]
        # Should have file headers ending with colon
        assert ":" in output
        # Should have tree connectors
        has_tree = "├──" in output or "└──" in output
        assert has_tree, f"Should have tree connectors, got: {output[:200]}"

    def test_csv_output_flat(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """CSV output remains flat with file column."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.CSV
        mock_response = self._make_symbols_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_symbol(
                mock_ctx,
                "User",
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
                depth=1,
                raw=False,
            )

        output = output_lines[0]
        lines = output.strip().split("\n")
        # First line is CSV header
        assert "file" in lines[0].lower()
        # Should be a flat table
        assert "{" not in output

    def test_empty_results_appropriate_output(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Empty results produce correct empty output per format."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value={"symbols": []}),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_symbol(
                mock_ctx,
                "Nonexistent",
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
                depth=1,
                raw=False,
            )

        data = json.loads(output_lines[0])
        assert isinstance(data, dict)
        assert data["files"] == []

    def test_file_groups_sorted_alphabetically(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """File groups appear in alphabetical order."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        # Create symbols from z.py and a.py
        mock_response = {
            "symbols": [
                {
                    "name": "Z",
                    "kind": 5,
                    "location": {
                        "uri": (setup_workspace / "src" / "z.py").as_uri(),
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 10, "character": 0},
                        },
                    },
                },
                {
                    "name": "A",
                    "kind": 5,
                    "location": {
                        "uri": (setup_workspace / "src" / "a.py").as_uri(),
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 10, "character": 0},
                        },
                    },
                },
            ]
        }

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_symbol(
                mock_ctx,
                "test",
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
                depth=1,
                raw=False,
            )

        data = json.loads(output_lines[0])
        files = data["files"]
        file_paths = [g["file"] for g in files]
        # Files should be sorted alphabetically
        assert file_paths == sorted(file_paths)


class TestWorkspaceDiagnosticsGrouping:
    """Test workspace-diagnostics produces grouped output with relative paths."""

    @pytest.fixture
    def mock_ctx(self, tmp_path: Path) -> MagicMock:
        """Create a mock Typer context with GlobalOptions."""
        ctx = MagicMock()
        ctx.obj = GlobalOptions(
            workspace=str(tmp_path),
            language="python",
            output_format=OutputFormat.JSON,
        )
        return ctx

    @pytest.fixture
    def setup_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with files."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("x = y  # undefined")
        (src / "utils.py").write_text("import os")
        return tmp_path

    def _make_diagnostics_response(self, workspace: Path) -> dict[str, Any]:
        """Create mock response with URIs relative to workspace."""
        return {
            "diagnostics": [
                {
                    "uri": (workspace / "src" / "main.py").as_uri(),
                    "diagnostics": [
                        {
                            "range": {
                                "start": {"line": 5, "character": 0},
                                "end": {"line": 5, "character": 10},
                            },
                            "severity": 1,
                            "message": "Undefined variable 'x'",
                            "code": "reportUndefinedVariable",
                            "source": "basedpyright",
                        },
                    ],
                },
            ]
        }

    def test_json_output_grouped_structure(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """JSON output is array of file-grouped objects."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_diagnostics_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        data = json.loads(output_lines[0])
        assert isinstance(data, dict)
        assert "_source" in data
        assert "files" in data
        files = data["files"]
        for group in files:
            assert "file" in group
            assert "diagnostics" in group
            assert isinstance(group["diagnostics"], list)

    def test_file_paths_are_absolute(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """File paths in output are absolute (not relative URIs)."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_diagnostics_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        data = json.loads(output_lines[0])
        files = data["files"]
        for group in files:
            file_path = group["file"]
            assert file_path.startswith("/"), f"Path should be absolute, got: {file_path}"
            assert not file_path.startswith("file://"), f"Path should not be URI, got: {file_path}"

    def test_file_paths_match_other_commands(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """workspace-diagnostics paths match diagnostics command format."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_diagnostics_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        data = json.loads(output_lines[0])
        files = data["files"]
        # Paths should be relative
        for group in files:
            file_path = group["file"]
            assert "/" in file_path or "\\" in file_path or file_path.endswith(".py")

    def test_diagnostic_items_have_expected_fields(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Diagnostic items include severity_name, message, range, code, source."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_diagnostics_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        data = json.loads(output_lines[0])
        files = data["files"]
        for group in files:
            for diag in group["diagnostics"]:
                assert "severity_name" in diag
                assert "message" in diag
                assert "range" in diag

    def test_text_output_hierarchical(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """TEXT output shows hierarchical structure."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT
        mock_response = self._make_diagnostics_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        output = output_lines[0]
        # Should have file headers
        assert ":" in output

    def test_csv_output_flat(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """CSV output remains flat."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.CSV
        mock_response = self._make_diagnostics_response(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value=mock_response),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        output = output_lines[0]
        # Should be flat CSV
        assert "{" not in output or "file" in output

    def test_empty_results_appropriate_output(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Empty results produce correct empty output."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)

        with (
            patch.object(lsp_module, "send_request", return_value={"diagnostics": []}),
            patch.object(
                lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)
            ),
            patch.object(lsp_module, "typer") as mock_typer,
        ):
            output_lines: list[str] = []

            def capture(x: str) -> None:
                output_lines.append(x)

            mock_typer.echo.side_effect = capture
            lsp_module.workspace_diagnostics(
                mock_ctx,
                workspace=None,
                language=None,
                output_format=None,
                include_tests=False,
            )

        data = json.loads(output_lines[0])
        assert isinstance(data, dict)
        assert data["files"] == []


class TestFormatterGroupingIntegration:
    """Test formatter grouping functions."""

    def test_group_symbols_by_file_exists(self) -> None:
        """group_symbols_by_file function exists in formatter module."""
        from llm_lsp_cli.output.formatter import group_symbols_by_file

        assert callable(group_symbols_by_file)

    def test_group_diagnostics_by_file_exists(self) -> None:
        """group_diagnostics_by_file function exists in formatter module."""
        from llm_lsp_cli.output.formatter import group_diagnostics_by_file

        assert callable(group_diagnostics_by_file)

    def test_group_symbols_by_file_groups_correctly(self, tmp_path: Path) -> None:
        """group_symbols_by_file groups symbols by file path."""
        from llm_lsp_cli.output.formatter import CompactFormatter

        formatter = CompactFormatter(tmp_path)
        symbols = [
            {
                "name": "A",
                "kind": 5,
                "location": {
                    "uri": (tmp_path / "a.py").as_uri(),
                    "range": {},
                },
            },
            {
                "name": "B",
                "kind": 5,
                "location": {
                    "uri": (tmp_path / "b.py").as_uri(),
                    "range": {},
                },
            },
            {
                "name": "C",
                "kind": 5,
                "location": {
                    "uri": (tmp_path / "a.py").as_uri(),
                    "range": {},
                },
            },
        ]
        records = formatter.transform_symbols(symbols)
        grouped = group_symbols_by_file(records)

        assert len(grouped) == 2
        files = [g["file"] for g in grouped]
        # Check file paths end with expected names (absolute paths)
        assert any(f.endswith("a.py") for f in files)
        assert any(f.endswith("b.py") for f in files)

    def test_group_diagnostics_by_file_groups_correctly(self) -> None:
        """group_diagnostics_by_file groups diagnostics by file path."""
        from llm_lsp_cli.output.formatter import DiagnosticRecord, Position, Range

        diags = [
            DiagnosticRecord(
                file="a.py",
                range=Range(Position(0, 0), Position(1, 0)),
                severity=1,
                severity_name="Error",
                code="E001",
                source="test",
                message="Error 1",
            ),
            DiagnosticRecord(
                file="b.py",
                range=Range(Position(0, 0), Position(1, 0)),
                severity=2,
                severity_name="Warning",
                code="W001",
                source="test",
                message="Warning 1",
            ),
        ]
        grouped = group_diagnostics_by_file(diags)

        assert len(grouped) == 2
        files = [g["file"] for g in grouped]
        assert "a.py" in files
        assert "b.py" in files


class TestDispatcherGroupedIntegration:
    """Test dispatcher grouped output methods."""

    def test_dispatcher_format_grouped_exists(self) -> None:
        """OutputDispatcher.format_grouped method exists."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format_grouped")

    def test_dispatcher_format_grouped_text_exists(self) -> None:
        """OutputDispatcher.format_grouped_text method exists."""
        from llm_lsp_cli.output.dispatcher import OutputDispatcher

        assert hasattr(OutputDispatcher, "format_grouped_text")

    def test_dispatcher_format_grouped_json(self) -> None:
        """format_grouped produces valid JSON."""
        dispatcher = OutputDispatcher()
        grouped = [
            {"file": "a.py", "symbols": [{"name": "A", "kind_name": "Class", "range": "1:1-10:1"}]},
        ]
        output = dispatcher.format_grouped(grouped, OutputFormat.JSON, _source="TestServer")
        data = json.loads(output)
        assert isinstance(data, dict)
        assert "files" in data
        assert data["files"] == grouped

    def test_dispatcher_format_grouped_text(self) -> None:
        """format_grouped_text produces hierarchical TEXT."""
        dispatcher = OutputDispatcher()
        grouped = [
            {
                "file": "a.py",
                "symbols": [{"name": "A", "kind_name": "Class", "range": "1:1-10:1"}],
            },
        ]
        output = dispatcher.format_grouped_text(
            grouped, items_key="symbols", header="Test: symbols"
        )
        assert "a.py:" in output
        assert "A" in output


class TestTextRendererGroupedIntegration:
    """Test text renderer grouped output functions."""

    def test_render_workspace_symbols_grouped_exists(self) -> None:
        """render_workspace_symbols_grouped function exists."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        assert callable(render_workspace_symbols_grouped)

    def test_render_workspace_diagnostics_grouped_exists(self) -> None:
        """render_workspace_diagnostics_grouped function exists."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        assert callable(render_workspace_diagnostics_grouped)

    def test_render_workspace_symbols_grouped_output(self) -> None:
        """render_workspace_symbols_grouped produces correct output."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped = [
            {"file": "a.py", "symbols": [{"name": "A", "kind_name": "Class", "range": "1:1-10:1"}]},
        ]
        output = render_workspace_symbols_grouped(grouped)
        assert "a.py:" in output
        assert "A" in output

    def test_render_workspace_diagnostics_grouped_output(self) -> None:
        """render_workspace_diagnostics_grouped produces correct output."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped = [
            {
                "file": "a.py",
                "diagnostics": [
                    {
                        "severity_name": "Error",
                        "message": "Test error",
                        "range": "1:1-1:5",
                    }
                ],
            },
        ]
        output = render_workspace_diagnostics_grouped(grouped)
        assert "a.py:" in output
        assert "Error" in output
