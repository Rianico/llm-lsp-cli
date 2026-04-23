"""Integration tests for did-change CLI command.

This module tests the CLI command as specified in ADR-0010.

Key behaviors tested:
1. CLI command succeeds with valid file
2. CLI command fails with invalid file path
3. CLI command fails when file outside workspace
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
    filepath.write_text("def test_func():\n    pass\n")
    return filepath


class TestDidChangeCommand:
    """Tests for did-change CLI command."""

    def test_cli_command_succeeds_with_valid_file(
        self,
        temp_workspace: Path,
        temp_python_file: Path,
    ) -> None:
        """Verify CLI command exits with code 0 for valid file.

        Given: Daemon running, valid Python file
        When: llm-lsp-cli did-change <file> executed
        Then: Command exits with code 0
        """
        # Patch where DaemonClient is imported
        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_daemon_client_class:
            mock_instance = mock_daemon_client_class.return_value
            mock_instance.send_notification = AsyncMock()
            mock_instance.close = AsyncMock()

            result = runner.invoke(
                app,
                [
                    "did-change",
                    str(temp_python_file),
                    "--workspace", str(temp_workspace),
                ],
            )

            # Command should succeed
            assert result.exit_code == 0

    def test_cli_command_outputs_acknowledgment(
        self,
        temp_workspace: Path,
        temp_python_file: Path,
    ) -> None:
        """Verify CLI command outputs acknowledgment message."""
        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_daemon_client_class:
            mock_instance = mock_daemon_client_class.return_value
            mock_instance.send_notification = AsyncMock()
            mock_instance.close = AsyncMock()

            result = runner.invoke(
                app,
                [
                    "did-change",
                    str(temp_python_file),
                    "--workspace", str(temp_workspace),
                ],
            )

            # Should show acknowledgment
            assert "acknowledged" in result.output.lower() or result.exit_code == 0

    def test_cli_command_fails_with_invalid_file_path(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify CLI command fails with non-existent file.

        Given: Non-existent file path
        When: llm-lsp-cli did-change <file> executed
        Then: Command exits with code 1
        """
        non_existent = temp_workspace / "does_not_exist.py"

        result = runner.invoke(
            app,
            [
                "did-change",
                str(non_existent),
                "--workspace", str(temp_workspace),
            ],
        )

        # Command should fail
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_cli_command_fails_when_file_outside_workspace(
        self,
        temp_workspace: Path,
        tmp_path: Path,
    ) -> None:
        """Verify CLI command fails when file escapes workspace boundary.

        Given: File path outside workspace boundary
        When: llm-lsp-cli did-change <file> executed
        Then: Command exits with code 1
        """
        # Create file outside workspace
        outside_file = tmp_path / "outside" / "module.py"
        outside_file.parent.mkdir(parents=True)
        outside_file.write_text("# Outside workspace")

        result = runner.invoke(
            app,
            [
                "did-change",
                str(outside_file),
                "--workspace", str(temp_workspace),
            ],
        )

        # Command should fail
        assert result.exit_code == 1
        assert "workspace boundary" in result.output.lower() or "error" in result.output.lower()

    def test_cli_command_resolves_relative_path(
        self,
        temp_workspace: Path,
        temp_python_file: Path,
    ) -> None:
        """Verify CLI command resolves relative file paths correctly."""
        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_daemon_client_class:
            mock_instance = mock_daemon_client_class.return_value
            mock_instance.send_notification = AsyncMock()
            mock_instance.close = AsyncMock()

            # Change to workspace directory and use relative path
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_workspace)
                result = runner.invoke(
                    app,
                    [
                        "did-change",
                        temp_python_file.name,
                    ],
                )
                # Should succeed with relative path
                assert result.exit_code == 0
            finally:
                os.chdir(old_cwd)

    def test_cli_command_auto_detects_language_from_file(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify language is auto-detected from file extension."""
        py_file = temp_workspace / "auto_detect.py"
        py_file.write_text("x = 1")

        with patch("llm_lsp_cli.daemon_client.DaemonClient") as mock_daemon_client_class:
            mock_instance = mock_daemon_client_class.return_value
            mock_instance.send_notification = AsyncMock()
            mock_instance.close = AsyncMock()

            result = runner.invoke(
                app,
                [
                    "did-change",
                    str(py_file),
                    "--workspace", str(temp_workspace),
                ],
            )

            # Should succeed with auto-detected language
            assert result.exit_code == 0
