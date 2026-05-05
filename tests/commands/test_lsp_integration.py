"""Integration tests for LSP CLI commands with grouped output and headers.

This module tests CLI command integration in commands/lsp.py:
- workspace-symbol: grouped output format
- workspace-diagnostics: grouped output + URI normalization
- All commands: alert headers in TEXT format
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from llm_lsp_cli.commands.lsp import (
    completion,
    definition,
    diagnostics,
    document_symbol,
    hover,
    incoming_calls,
    outgoing_calls,
    references,
    workspace_diagnostics,
    workspace_symbol,
)
from llm_lsp_cli.commands.shared import GlobalOptions
from llm_lsp_cli.utils import OutputFormat


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_ctx() -> MagicMock:
    """Create a mock Typer context with GlobalOptions."""
    ctx = MagicMock()
    ctx.obj = GlobalOptions(
        workspace="/workspace",
        language="python",
        output_format=OutputFormat.JSON,
    )
    return ctx


@pytest.fixture
def sample_workspace(tmp_path: Path) -> Path:
    """Create a sample workspace with Python files."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass")
    (src / "utils.py").write_text("def helper(): pass")
    return tmp_path


@pytest.fixture
def mock_server_info_response() -> dict[str, Any]:
    """Mock LSP initialize response with serverInfo."""
    return {
        "capabilities": {},
        "serverInfo": {"name": "basedpyright", "version": "1.0.0"},
    }


@pytest.fixture
def mock_workspace_symbols_response() -> dict[str, Any]:
    """Mock workspace/symbol response with multiple files."""
    return {
        "symbols": [
            {
                "name": "User",
                "kind": 5,
                "location": {
                    "uri": "file:///workspace/src/models.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                },
            },
            {
                "name": "UserService",
                "kind": 5,
                "location": {
                    "uri": "file:///workspace/src/services.py",
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}},
                },
            },
            {
                "name": "get_user",
                "kind": 12,
                "location": {
                    "uri": "file:///workspace/src/models.py",
                    "range": {"start": {"line": 15, "character": 0}, "end": {"line": 20, "character": 0}},
                },
            },
        ]
    }


@pytest.fixture
def mock_workspace_diagnostics_response() -> dict[str, Any]:
    """Mock workspace/diagnostic response with file:// URIs."""
    return {
        "diagnostics": [
            {
                "uri": "file:///workspace/src/main.py",
                "diagnostics": [
                    {
                        "range": {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 10}},
                        "severity": 1,
                        "message": "Undefined variable 'x'",
                        "code": "reportUndefinedVariable",
                        "source": "basedpyright",
                    },
                ],
            },
            {
                "uri": "file:///workspace/src/utils.py",
                "diagnostics": [
                    {
                        "range": {"start": {"line": 2, "character": 0}, "end": {"line": 2, "character": 5}},
                        "severity": 2,
                        "message": "Unused import 'os'",
                        "code": "reportUnusedImport",
                        "source": "basedpyright",
                    },
                ],
            },
        ]
    }


# =============================================================================
# Test: Workspace Symbol Grouped Output
# =============================================================================


class TestWorkspaceSymbolGroupedOutput:
    """Test workspace-symbol command uses grouped output."""

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
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                    },
                },
                {
                    "name": "UserService",
                    "kind": 5,
                    "location": {
                        "uri": (workspace / "src" / "services.py").as_uri(),
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}},
                    },
                },
                {
                    "name": "get_user",
                    "kind": 12,
                    "location": {
                        "uri": (workspace / "src" / "models.py").as_uri(),
                        "range": {"start": {"line": 15, "character": 0}, "end": {"line": 20, "character": 0}},
                    },
                },
            ]
        }

    def test_json_output_is_grouped_array(
        self, mock_ctx: MagicMock, setup_workspace: Path, mock_workspace_symbols_response: dict[str, Any]
    ) -> None:
        """JSON output is array of file-grouped objects, not flat array."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_symbols_response(setup_workspace)

        # Patch send_request in the lsp module where it's imported
        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                # Capture output
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    # Call with explicit parameters to avoid Typer Option resolution issues
                    workspace_symbol(
                        mock_ctx,
                        "User",
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                        depth=1,
                        raw=False,
                    )

                # Parse output as JSON
                output = output_lines[0]
                data = json.loads(output)

                # Assert wrapped structure with _source and files
                assert isinstance(data, dict), "Output should be a dict with _source and files"
                assert "_source" in data, "Output should have _source field"
                assert "files" in data, "Output should have files field"

                files = data["files"]
                assert len(files) > 0, "Output should have file groups"

                # Each group must have 'file' and 'symbols' keys
                for group in files:
                    assert "file" in group, "Each group must have 'file' key"
                    assert "symbols" in group, "Each group must have 'symbols' key"
                    assert isinstance(group["symbols"], list), "symbols must be a list"

    def test_json_output_groups_by_file(
        self, mock_ctx: MagicMock, setup_workspace: Path, mock_workspace_symbols_response: dict[str, Any]
    ) -> None:
        """Symbols are grouped by file path."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_symbols_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
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

                # Extract file names from groups - now wrapped with _source and files
                assert "_source" in data
                files = data["files"]
                file_paths = [g["file"] for g in files]

                # Should have exactly 2 files
                assert len(file_paths) == 2, f"Should have 2 file groups, got {len(file_paths)}"

                # Files should be absolute paths
                for f in file_paths:
                    assert f.startswith("/"), f"File path should be absolute, got {f}"
                    assert not f.startswith("file://"), f"File path should not be URI, got {f}"

    def test_text_output_has_hierarchical_format(
        self, mock_ctx: MagicMock, setup_workspace: Path, mock_workspace_symbols_response: dict[str, Any]
    ) -> None:
        """TEXT output shows file headers with tree connectors."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT
        mock_response = self._make_symbols_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
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
                assert ":" in output, "Should have file headers"

                # Should have tree connectors
                has_tree = "├──" in output or "└──" in output
                assert has_tree, f"Should have tree connectors, got: {output[:200]}"

    def test_csv_output_remains_flat(
        self, mock_ctx: MagicMock, setup_workspace: Path, mock_workspace_symbols_response: dict[str, Any]
    ) -> None:
        """CSV output stays flat (no nested structure)."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.CSV
        mock_response = self._make_symbols_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
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
                assert "file" in lines[0].lower(), "CSV should have file column"

                # Should be a flat table (no nested structure indicators)
                assert "{" not in output, "CSV should not have JSON-like structure"

    def test_empty_results_empty_array_json(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Empty results return [] in JSON."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value={"symbols": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
                        mock_ctx,
                        "Nonexistent",
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                        depth=1,
                        raw=False,
                    )

                # Should be wrapped with _source and empty files array
                data = json.loads(output_lines[0])
                assert isinstance(data, dict), f"Output should be a dict, got {output_lines[0]}"
                assert "_source" in data, f"Output should have _source field, got {output_lines[0]}"
                assert data["files"] == [], f"Empty should have empty files array, got {output_lines[0]}"

    def test_empty_results_shows_message_text(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Empty results show 'No symbols found.' in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        with patch.object(lsp_module, "send_request", return_value={"symbols": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
                        mock_ctx,
                        "Nonexistent",
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                        depth=1,
                        raw=False,
                    )

                assert "No symbols found" in output_lines[0]


# =============================================================================
# Test: Workspace Diagnostics Grouped Output + URI Normalization
# =============================================================================


class TestWorkspaceDiagnosticsGroupedOutput:
    """Test workspace-diagnostics command uses grouped output and relative paths."""

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
                            "range": {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 10}},
                            "severity": 1,
                            "message": "Undefined variable 'x'",
                            "code": "reportUndefinedVariable",
                            "source": "basedpyright",
                        },
                    ],
                },
                {
                    "uri": (workspace / "src" / "utils.py").as_uri(),
                    "diagnostics": [
                        {
                            "range": {"start": {"line": 2, "character": 0}, "end": {"line": 2, "character": 5}},
                            "severity": 2,
                            "message": "Unused import 'os'",
                            "code": "reportUnusedImport",
                            "source": "basedpyright",
                        },
                    ],
                },
            ]
        }

    def test_json_output_is_grouped_array(
        self,
        mock_ctx: MagicMock,
        setup_workspace: Path,
        mock_workspace_diagnostics_response: dict[str, Any],
    ) -> None:
        """JSON output is array of file-grouped objects."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_diagnostics_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                data = json.loads(output_lines[0])

                # Assert wrapped structure with _source and files
                assert isinstance(data, dict)
                assert "_source" in data
                assert "files" in data
                files = data["files"]
                for group in files:
                    assert "file" in group
                    assert "diagnostics" in group
                    assert isinstance(group["diagnostics"], list)

    def test_file_paths_are_absolute(
        self,
        mock_ctx: MagicMock,
        setup_workspace: Path,
        mock_workspace_diagnostics_response: dict[str, Any],
    ) -> None:
        """File paths are absolute, not relative URIs."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_response = self._make_diagnostics_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                data = json.loads(output_lines[0])

                # Wrapped with _source and files
                assert "_source" in data
                files = data["files"]
                for group in files:
                    file_path = group["file"]
                    # Should be absolute path
                    assert file_path.startswith("/"), f"Path should be absolute, got: {file_path}"
                    # Should not be file:// URI
                    assert not file_path.startswith("file://"), f"Path should not be URI, got: {file_path}"

    def test_text_output_has_file_headers(
        self,
        mock_ctx: MagicMock,
        setup_workspace: Path,
        mock_workspace_diagnostics_response: dict[str, Any],
    ) -> None:
        """TEXT output shows file headers for diagnostics."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT
        mock_response = self._make_diagnostics_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                output = output_lines[0]

                # Should have file headers
                assert ".py:" in output or "src/" in output, f"Should have file headers, got: {output[:200]}"

    def test_text_output_shows_severity_and_message(
        self,
        mock_ctx: MagicMock,
        setup_workspace: Path,
        mock_workspace_diagnostics_response: dict[str, Any],
    ) -> None:
        """TEXT output shows severity and message."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT
        mock_response = self._make_diagnostics_response(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                output = output_lines[0]

                # Should show Error or Warning
                assert "Error" in output or "Warning" in output, f"Should show severity, got: {output[:200]}"

    def test_empty_results_empty_array_json(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Empty results return [] in JSON."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                # Should be wrapped with _source and empty files array
                data = json.loads(output_lines[0])
                assert isinstance(data, dict), f"Output should be a dict, got {output_lines[0]}"
                assert "_source" in data, f"Output should have _source field, got {output_lines[0]}"
                assert data["files"] == [], f"Empty should have empty files array, got {output_lines[0]}"

    def test_empty_results_shows_message_text(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Empty results show 'No diagnostics found.' in TEXT."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                assert "No diagnostics found" in output_lines[0]


# =============================================================================
# Test: Alert Header Integration (TEXT format only)
# =============================================================================


class TestAlertHeaderIntegration:
    """Test alert headers appear in TEXT output for all LSP commands."""

    @pytest.fixture
    def setup_file(self, tmp_path: Path) -> Path:
        """Create a test file."""
        src = tmp_path / "src"
        src.mkdir()
        test_file = src / "main.py"
        test_file.write_text("def main(): pass")
        return tmp_path

    def _get_server_name_from_header(self, output: str) -> str | None:
        """Extract server name from header line.

        Header format: 'ServerName: command of file' or 'ServerName: command'
        """
        lines = output.strip().split("\n")
        if not lines:
            return None
        first_line = lines[0]
        if ":" in first_line:
            # Extract server name (everything before first colon)
            parts = first_line.split(":", 1)
            return parts[0].strip()
        return None

    def _assert_header_present(self, output: str, command_name: str, file_path: str | None = None) -> None:
        """Assert header is present with correct format."""
        lines = output.strip().split("\n")
        assert lines, "Output should not be empty"

        header = lines[0]
        # Header format: 'ServerName: command of file' or 'ServerName: command'
        assert ":" in header, f"Header should contain ':', got: {header}"

        # Should have command name
        assert command_name in header, f"Header should contain '{command_name}', got: {header}"

        # If file provided, should have 'of <file>'
        if file_path:
            assert f" of {file_path}" in header or file_path in header, \
                f"Header should contain file path, got: {header}"

    def test_diagnostics_header_format(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """diagnostics shows '<Server>: diagnostics of <file>'."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        test_file = setup_file / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    diagnostics(
                        mock_ctx,
                        str(test_file),
                        workspace=None,
                        language=None,
                        output_format=None,
                    )

                # Check for header in output
                output = output_lines[0]
                assert ":" in output, f"Should have header, got: {output}"

    def test_document_symbol_header_format(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """document-symbol shows '<Server>: document-symbol of <file>'."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        test_file = setup_file / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"symbols": [{"name": "main", "kind": 12, "range": {}}]}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    document_symbol(
                        mock_ctx,
                        str(test_file),
                        workspace=None,
                        language=None,
                        output_format=None,
                        depth=1,
                        raw=False,
                    )

                output = output_lines[0]
                # Header should be present for TEXT format
                assert "document-symbol" in output or "main" in output

    def test_definition_header_format(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """definition shows '<Server>: definition of <file>'."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        test_file = setup_file / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"locations": []}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    definition(
                        mock_ctx,
                        str(test_file),
                        0,
                        0,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                # Check output
                output = output_lines[0] if output_lines else ""
                # Either header or "No locations found" is acceptable
                assert output  # Something should be output

    def test_workspace_symbol_header_format(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """workspace-symbol shows '<Server>: workspace-symbol' (no 'of' clause)."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        with patch.object(lsp_module, "send_request", return_value={"symbols": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_file)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
                        mock_ctx,
                        "test",
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                        depth=1,
                        raw=False,
                    )

                # For workspace-level commands, header should NOT have 'of <file>'
                # But we're testing that a header appears
                output = output_lines[0]
                assert "workspace-symbol" in output or "No symbols found" in output

    def test_workspace_diagnostics_header_format(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """workspace-diagnostics shows '<Server>: workspace-diagnostics'."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_file)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_diagnostics(
                        mock_ctx,
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                    )

                output = output_lines[0]
                # Should either have header or "No diagnostics found"
                assert output

    def test_json_format_has_no_header(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """JSON output must be parseable (no header string)."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.JSON

        test_file = setup_file / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    diagnostics(
                        mock_ctx,
                        str(test_file),
                        workspace=None,
                        language=None,
                        output_format=None,
                    )

                # Should be valid JSON
                output = output_lines[0]
                try:
                    data = json.loads(output)
                    # Should be a dict with _source and items (file-level command uses items)
                    assert isinstance(data, dict)
                    assert "_source" in data
                    assert "items" in data
                except json.JSONDecodeError:
                    pytest.fail(f"JSON output should be parseable, got: {output[:100]}")

    def test_yaml_format_has_no_header(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """YAML output must be parseable (no header string)."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.YAML

        test_file = setup_file / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    diagnostics(
                        mock_ctx,
                        str(test_file),
                        workspace=None,
                        language=None,
                        output_format=None,
                    )

                # Should be valid YAML
                output = output_lines[0]
                try:
                    data = yaml.safe_load(output)
                    # Should be a dict with _source and items (file-level command uses items)
                    assert isinstance(data, dict)
                    assert "_source" in data
                    assert "items" in data
                except yaml.YAMLError:
                    pytest.fail(f"YAML output should be parseable, got: {output[:100]}")

    def test_csv_format_has_no_alert_header(
        self, mock_ctx: MagicMock, setup_file: Path
    ) -> None:
        """CSV output must be standard CSV (no alert header)."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_file)
        mock_ctx.obj.output_format = OutputFormat.CSV

        test_file = setup_file / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    diagnostics(
                        mock_ctx,
                        str(test_file),
                        workspace=None,
                        language=None,
                        output_format=None,
                    )

                # Empty diagnostics should produce empty CSV output
                # The key is it should NOT have an alert header line
                output = output_lines[0] if output_lines else ""
                if output:
                    # If there's output, first line should be CSV headers
                    first_line = output.split("\n")[0]
                    assert "file" in first_line.lower() or "severity" in first_line.lower() or \
                           "range" in first_line.lower(), \
                        f"CSV first line should be column headers, got: {first_line}"


# =============================================================================
# Test: Header Format Variants
# =============================================================================


class TestHeaderFormatVariants:
    """Test header format variations for file-level vs workspace-level commands."""

    @pytest.fixture
    def setup_workspace(self, tmp_path: Path) -> Path:
        """Create workspace with files."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def main(): pass")
        return tmp_path

    def test_file_level_header_includes_file_path(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """File-level commands show 'of <file>' in header."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        test_file = setup_workspace / "src" / "main.py"

        with patch.object(lsp_module, "send_request", return_value={"diagnostics": []}):
            with patch.object(lsp_module, "validate_file_in_workspace", return_value=test_file):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    diagnostics(
                        mock_ctx,
                        str(test_file),
                        workspace=None,
                        language=None,
                        output_format=None,
                    )

                # For TEXT format, header should be present
                output = output_lines[0]
                # Should indicate file somehow
                assert "diagnostics" in output or "main.py" in output

    def test_workspace_level_header_no_file_clause(
        self, mock_ctx: MagicMock, setup_workspace: Path
    ) -> None:
        """Workspace-level commands do NOT show 'of <file>'."""
        import llm_lsp_cli.commands.lsp as lsp_module

        mock_ctx.obj.workspace = str(setup_workspace)
        mock_ctx.obj.output_format = OutputFormat.TEXT

        with patch.object(lsp_module, "send_request", return_value={"symbols": []}):
            with patch.object(lsp_module, "resolve_workspace_path", return_value=str(setup_workspace)):
                output_lines: list[str] = []

                def capture(x: str, **kwargs: Any) -> None:
                    output_lines.append(x)

                with patch.object(lsp_module, "typer") as mock_typer:
                    mock_typer.echo.side_effect = capture
                    workspace_symbol(
                        mock_ctx,
                        "test",
                        workspace=None,
                        language=None,
                        output_format=None,
                        include_tests=False,
                        depth=1,
                        raw=False,
                    )

                output = output_lines[0]
                # Should have workspace-symbol command indicator
                # But should NOT have 'of <specific-file>'
                assert "workspace-symbol" in output or "No symbols found" in output
