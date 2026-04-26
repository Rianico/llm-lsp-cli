"""Tests for rename CLI command registration.

This module tests the CLI command registration as specified in design.md.

Key behaviors tested:
1. CLI command `rename` is registered and accessible
2. CLI command accepts required arguments: file, line, column, new_name
3. CLI command supports options: --workspace, --language, --format, --apply, --dry-run, --rollback
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from llm_lsp_cli.cli import app

runner = CliRunner()


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory with a Python file."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    return workspace


@pytest.fixture
def temp_python_file(temp_workspace: Path) -> Path:
    """Create a temporary Python file inside the workspace."""
    filepath = temp_workspace / "test_module.py"
    filepath.write_text("def old_name():\n    pass\n")
    return filepath


class TestRenameCommandRegistration:
    """Tests for rename CLI command registration."""

    def test_rename_command_is_registered(self) -> None:
        """Verify rename command is registered and accessible."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "rename" in result.output.lower()

    def test_rename_command_accepts_required_arguments(
        self,
        temp_workspace: Path,
        temp_python_file: Path,
    ) -> None:
        """Verify rename command accepts file, line, column, new_name arguments."""
        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_daemon_client_class:
            mock_instance = mock_daemon_client_class.return_value
            mock_instance.request = AsyncMock(return_value={"edits": []})
            mock_instance.close = AsyncMock()

            result = runner.invoke(
                app,
                [
                    "lsp",
                    "rename",
                    str(temp_python_file),
                    "1",
                    "4",
                    "new_name",
                    "--workspace", str(temp_workspace),
                ],
            )

            # Command should succeed (or fail with business logic, not missing command)
            assert "no such command" not in result.output.lower()

    def test_rename_command_supports_workspace_option(
        self,
        temp_workspace: Path,
        temp_python_file: Path,
    ) -> None:
        """Verify rename command supports --workspace / -w option."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "--workspace" in result.output or "-w" in result.output

    def test_rename_command_supports_language_option(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify rename command supports --language / -l option."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "--language" in result.output or "-l" in result.output

    def test_rename_command_supports_format_option(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify rename command supports --format / -o option."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output or "-o" in result.output

    def test_rename_command_supports_apply_flag(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify rename command supports --apply flag."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "--apply" in result.output

    def test_rename_command_supports_dry_run_flag(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify rename command supports --dry-run flag."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output

    def test_rename_command_supports_rollback_option(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify rename command supports --rollback option."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "--rollback" in result.output


class TestRenameCommandHelp:
    """Tests for rename CLI command help output."""

    def test_rename_help_shows_file_argument(self) -> None:
        """Verify help shows file argument."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "file" in result.output.lower()

    def test_rename_help_shows_line_argument(self) -> None:
        """Verify help shows line argument."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "line" in result.output.lower()

    def test_rename_help_shows_column_argument(self) -> None:
        """Verify help shows column argument."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "column" in result.output.lower()

    def test_rename_help_shows_new_name_argument(self) -> None:
        """Verify help shows new_name argument."""
        result = runner.invoke(app, ["lsp", "rename", "--help"])
        assert result.exit_code == 0
        assert "new_name" in result.output.lower() or "new-name" in result.output.lower()
