"""Tests for RuntimePathBuilder diagnostic log path functionality."""

from pathlib import Path

import pytest

from llm_lsp_cli.config.path_builder import RuntimePathBuilder


class TestRuntimePathBuilderDiagnosticLogPath:
    """Test build_diagnostic_log_path() method."""

    def test_build_diagnostic_log_path_basic(self, tmp_path: Path) -> None:
        """Test basic diagnostic log path construction."""
        # Arrange
        workspace = str(tmp_path / "test_project")

        # Act
        path = RuntimePathBuilder.build_diagnostic_log_path(workspace, "python")

        # Assert
        assert path.is_absolute()
        assert path.name == "diagnostics.log"
        assert ".llm-lsp-cli" in str(path)

    def test_build_diagnostic_log_path_with_base_dir(self, tmp_path: Path) -> None:
        """Test diagnostic log path with custom base_dir."""
        # Arrange
        custom_base = tmp_path / "custom_runtime"
        custom_base.mkdir()

        # Act
        path = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path="/project",
            language="python",
            base_dir=custom_base,
        )

        # Assert
        assert str(path).startswith(str(custom_base))
        assert path.name == "diagnostics.log"

    def test_build_diagnostic_log_path_consistent_with_daemon_log(self, tmp_path: Path) -> None:
        """Test diagnostic log path is in same directory as daemon.log."""
        # Arrange
        workspace = str(tmp_path / "test_project")

        # Act
        diag_path = RuntimePathBuilder.build_diagnostic_log_path(workspace, "python")
        daemon_path = RuntimePathBuilder.build_daemon_log_path(workspace, "python")

        # Assert
        assert diag_path.parent == daemon_path.parent


class TestConfigManagerDiagnosticLogPath:
    """Test ConfigManager.build_diagnostic_log_path() facade method."""

    def test_config_manager_build_diagnostic_log_path(self, tmp_path: Path) -> None:
        """Test ConfigManager facade for diagnostic log path."""
        # Arrange
        from llm_lsp_cli.config.manager import ConfigManager

        workspace = str(tmp_path / "test_project")

        # Act
        path = ConfigManager.build_diagnostic_log_path(workspace, "python")

        # Assert
        assert path.is_absolute()
        assert path.name == "diagnostics.log"

    def test_config_manager_diagnostic_log_path_delegates_to_builder(
        self, tmp_path: Path
    ) -> None:
        """Test ConfigManager delegates to RuntimePathBuilder."""
        # Arrange
        from llm_lsp_cli.config.manager import ConfigManager
        from llm_lsp_cli.config.path_builder import RuntimePathBuilder

        workspace = str(tmp_path / "test_project")

        # Act
        config_manager_path = ConfigManager.build_diagnostic_log_path(workspace, "python")
        builder_path = RuntimePathBuilder.build_diagnostic_log_path(workspace, "python")

        # Assert - paths should be identical
        assert config_manager_path == builder_path
