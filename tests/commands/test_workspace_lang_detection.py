"""Integration tests for workspace-level language detection in CLI commands.

Tests verify that workspace_symbol and workspace_diagnostics commands
use correct LSP server based on detected language.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pytest import MonkeyPatch

runner = CliRunner()


class TestWorkspaceDiagnosticsLanguageDetection:
    """Tests I1, I3, I4, I5: workspace-diagnostics command behavior."""

    def test_workspace_diagnostics_rust_project(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """I1: Rust project with Cargo.toml sends language='rust' to daemon."""
        workspace = tmp_path / "rust_project"
        workspace.mkdir()
        (workspace / "Cargo.toml").touch()

        # Mock the daemon client to capture the language parameter
        with patch("llm_lsp_cli.commands.lsp.send_request") as mock_send:
            mock_send.return_value = {"diagnostics": []}

            from llm_lsp_cli.cli import app

            result = runner.invoke(app, ["lsp", "workspace-diagnostics", "-w", str(workspace)])

            # Verify send_request was called with language='rust'
            assert mock_send.called
            call_kwargs = mock_send.call_args
            assert call_kwargs[1].get("language") == "rust"

    def test_workspace_diagnostics_python_project(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """I3: Python project with pyproject.toml sends language='python' to daemon."""
        workspace = tmp_path / "python_project"
        workspace.mkdir()
        (workspace / "pyproject.toml").touch()

        with patch("llm_lsp_cli.commands.lsp.send_request") as mock_send:
            mock_send.return_value = {"diagnostics": []}

            from llm_lsp_cli.cli import app

            result = runner.invoke(app, ["lsp", "workspace-diagnostics", "-w", str(workspace)])

            # Verify send_request was called with language='python'
            assert mock_send.called
            call_kwargs = mock_send.call_args
            assert call_kwargs[1].get("language") == "python"

    def test_explicit_language_flag_override(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """I4: Explicit --language overrides detected language."""
        workspace = tmp_path / "rust_project"
        workspace.mkdir()
        (workspace / "Cargo.toml").touch()

        with patch("llm_lsp_cli.commands.lsp.send_request") as mock_send:
            mock_send.return_value = {"diagnostics": []}

            from llm_lsp_cli.cli import app

            result = runner.invoke(
                app, ["lsp", "workspace-diagnostics", "-w", str(workspace), "-l", "python"]
            )

            # Verify send_request was called with language='python' (explicit), not 'rust' (detected)
            assert mock_send.called
            call_kwargs = mock_send.call_args
            assert call_kwargs[1].get("language") == "python"

    def test_no_marker_shows_error_message(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """I5: Empty dir without --language shows error with supported languages."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        from llm_lsp_cli.cli import app

        result = runner.invoke(app, ["lsp", "workspace-diagnostics", "-w", str(workspace)])

        # Should exit with error
        assert result.exit_code == 1
        # Should mention supported languages in error message
        assert "Supported languages" in result.output or "language" in result.output.lower()


class TestWorkspaceSymbolLanguageDetection:
    """Test I2: workspace-symbol command behavior."""

    def test_workspace_symbol_go_project(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """I2: Go project with go.mod sends language='go' to daemon."""
        workspace = tmp_path / "go_project"
        workspace.mkdir()
        (workspace / "go.mod").touch()

        with patch("llm_lsp_cli.commands.lsp.send_request") as mock_send:
            mock_send.return_value = {"symbols": []}

            from llm_lsp_cli.cli import app

            result = runner.invoke(app, ["lsp", "workspace-symbol", "test", "-w", str(workspace)])

            # Verify send_request was called with language='go'
            assert mock_send.called
            call_kwargs = mock_send.call_args
            assert call_kwargs[1].get("language") == "go"


class TestNegativeConstraints:
    """Tests N1-N2: Anti-regression tests for silent Python fallback removal."""

    def test_no_silent_python_fallback_in_empty_dir(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """N1: Empty dir WITHOUT --language does NOT use Python LSP; errors instead."""
        workspace = tmp_path / "empty_workspace"
        workspace.mkdir()

        from llm_lsp_cli.cli import app

        result = runner.invoke(app, ["lsp", "workspace-diagnostics", "-w", str(workspace)])

        # Should fail, not silently use Python
        assert result.exit_code == 1
        # Should NOT have called with language='python'
        assert "python" not in result.output.lower() or "error" in result.output.lower()

    def test_no_crash_on_unknown_workspace(self, tmp_path: Path, xdg_test_env: Path, monkeypatch: MonkeyPatch) -> None:
        """N2: Graceful error, not unhandled exception."""
        workspace = tmp_path / "unknown_project"
        workspace.mkdir()

        from llm_lsp_cli.cli import app

        result = runner.invoke(app, ["lsp", "workspace-diagnostics", "-w", str(workspace)])

        # Should exit cleanly with error code 1, not crash
        assert result.exit_code == 1
        # Should have a meaningful error message
        assert len(result.output) > 0
        # Should not be a Python traceback
        assert "Traceback" not in result.output
