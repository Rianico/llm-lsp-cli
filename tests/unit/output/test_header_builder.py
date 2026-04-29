"""Tests for alert header builder for LSP commands.

This module tests the CommandInfo dataclass and build_alert_header function
in output/header_builder.py for generating alert headers in TEXT output.
"""

from __future__ import annotations

import pytest


class TestCommandInfo:
    """Test CommandInfo dataclass."""

    def test_command_info_creation(self) -> None:
        """CommandInfo can be created with all fields."""
        from llm_lsp_cli.output.header_builder import CommandInfo

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="diagnostics",
            file_path="src/main.py"
        )

        assert info.server_name == "Basedpyright"
        assert info.command_name == "diagnostics"
        assert info.file_path == "src/main.py"

    def test_command_info_workspace_level(self) -> None:
        """CommandInfo with file_path=None for workspace commands."""
        from llm_lsp_cli.output.header_builder import CommandInfo

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="workspace-symbol",
            file_path=None
        )

        assert info.server_name == "Basedpyright"
        assert info.command_name == "workspace-symbol"
        assert info.file_path is None

    def test_command_info_is_frozen(self) -> None:
        """CommandInfo is immutable (frozen dataclass)."""
        from llm_lsp_cli.output.header_builder import CommandInfo

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="diagnostics",
            file_path="src/main.py"
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            info.server_name = "Other"  # type: ignore[misc]


class TestBuildAlertHeader:
    """Test header generation for LSP commands."""

    def test_file_level_header_format(self) -> None:
        """File-level command produces '<Server>: <command> of <file>'."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="diagnostics",
            file_path="src/main.py"
        )

        result = build_alert_header(info)
        assert result == "Basedpyright: diagnostics of src/main.py"

    def test_workspace_level_header_format(self) -> None:
        """Workspace-level command produces '<Server>: <command>'."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="workspace-symbol",
            file_path=None
        )

        result = build_alert_header(info)
        assert result == "Basedpyright: workspace-symbol"

    def test_header_with_different_servers(self) -> None:
        """Header works with various server names."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        # Pyright
        info = CommandInfo(
            server_name="Pyright",
            command_name="diagnostics",
            file_path="test.ts"
        )
        assert build_alert_header(info) == "Pyright: diagnostics of test.ts"

        # Rust Analyzer
        info = CommandInfo(
            server_name="Rust Analyzer",
            command_name="diagnostics",
            file_path="src/lib.rs"
        )
        assert build_alert_header(info) == "Rust Analyzer: diagnostics of src/lib.rs"

        # TypeScript
        info = CommandInfo(
            server_name="TypeScript",
            command_name="workspace-diagnostics",
            file_path=None
        )
        assert build_alert_header(info) == "TypeScript: workspace-diagnostics"

    def test_header_with_hyphenated_commands(self) -> None:
        """Hyphenated command names preserved."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="document-symbol",
            file_path="src/main.py"
        )

        result = build_alert_header(info)
        assert result == "Basedpyright: document-symbol of src/main.py"

    def test_header_with_nested_file_path(self) -> None:
        """Nested file paths handled correctly."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="diagnostics",
            file_path="src/deep/nested/module.py"
        )

        result = build_alert_header(info)
        assert "src/deep/nested/module.py" in result
        assert result == "Basedpyright: diagnostics of src/deep/nested/module.py"

    def test_header_with_definition_command(self) -> None:
        """Header for definition command."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="definition",
            file_path="src/main.py"
        )

        result = build_alert_header(info)
        assert result == "Basedpyright: definition of src/main.py"

    def test_header_with_references_command(self) -> None:
        """Header for references command."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Pyright",
            command_name="references",
            file_path="lib/utils.ts"
        )

        result = build_alert_header(info)
        assert result == "Pyright: references of lib/utils.ts"

    def test_header_with_completion_command(self) -> None:
        """Header for completion command."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Basedpyright",
            command_name="completion",
            file_path="src/api/handlers.py"
        )

        result = build_alert_header(info)
        assert result == "Basedpyright: completion of src/api/handlers.py"

    def test_header_with_hover_command(self) -> None:
        """Header for hover command."""
        from llm_lsp_cli.output.header_builder import CommandInfo, build_alert_header

        info = CommandInfo(
            server_name="Rust Analyzer",
            command_name="hover",
            file_path="src/main.rs"
        )

        result = build_alert_header(info)
        assert result == "Rust Analyzer: hover of src/main.rs"
