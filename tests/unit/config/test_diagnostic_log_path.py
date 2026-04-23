"""Tests for build_diagnostic_log_path in path_builder.py.

Verifies that diagnostic log paths are constructed correctly.
"""

from pathlib import Path

from llm_lsp_cli.config.path_builder import RuntimePathBuilder


class TestBuildDiagnosticLogPath:
    """Tests for build_diagnostic_log_path() method."""

    def test_returns_path_in_runtime_dir(self, tmp_path: Path) -> None:
        """Diagnostic log path is in runtime directory."""
        workspace = str(tmp_path / "project")
        result = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
            base_dir=tmp_path / "runtime",
        )

        assert result.parent == tmp_path / "runtime"
        assert result.name == "diagnostics.log"

    def test_returns_correct_filename(self, tmp_path: Path) -> None:
        """Diagnostic log file is named diagnostics.log."""
        workspace = str(tmp_path / "project")
        result = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
        )

        assert result.name == "diagnostics.log"

    def test_same_directory_as_daemon_log(self, tmp_path: Path) -> None:
        """Diagnostic log is in same directory as daemon.log."""
        workspace = str(tmp_path / "project")
        base_dir = tmp_path / "runtime"

        diagnostic_path = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
            base_dir=base_dir,
        )
        daemon_path = RuntimePathBuilder.build_daemon_log_path(
            workspace_path=workspace,
            language="python",
            base_dir=base_dir,
        )

        assert diagnostic_path.parent == daemon_path.parent

    def test_independent_of_language(self, tmp_path: Path) -> None:
        """Diagnostic log path is same regardless of language."""
        workspace = str(tmp_path / "project")
        base_dir = tmp_path / "runtime"

        python_path = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
            base_dir=base_dir,
        )
        typescript_path = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="typescript",
            base_dir=base_dir,
        )

        # Same path regardless of language
        assert python_path == typescript_path

    def test_default_base_dir(self, tmp_path: Path) -> None:
        """Uses workspace-based runtime directory when base_dir not specified."""
        workspace = str(tmp_path / "myproject")
        result = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
        )

        expected_parent = Path(workspace) / ".llm-lsp-cli"
        assert result.parent == expected_parent
        assert result.name == "diagnostics.log"

    def test_base_dir_override(self, tmp_path: Path) -> None:
        """Accepts base_dir override."""
        workspace = str(tmp_path / "project")
        custom_base = tmp_path / "custom" / "runtime"
        result = RuntimePathBuilder.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
            base_dir=custom_base,
        )

        assert result.parent == custom_base


class TestDiagnosticLogPathIntegration:
    """Integration tests for diagnostic log path via ConfigManager."""

    def test_config_manager_delegates_to_path_builder(self, tmp_path: Path) -> None:
        """ConfigManager.build_diagnostic_log_path delegates to RuntimePathBuilder."""
        from llm_lsp_cli.config import ConfigManager

        workspace = str(tmp_path / "project")
        base_dir = tmp_path / "runtime"

        result = ConfigManager.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
            base_dir=base_dir,
        )

        assert result.parent == base_dir
        assert result.name == "diagnostics.log"

    def test_path_consistency(self, tmp_path: Path) -> None:
        """Path is consistent across multiple calls."""
        from llm_lsp_cli.config import ConfigManager

        workspace = str(tmp_path / "project")

        result1 = ConfigManager.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
        )
        result2 = ConfigManager.build_diagnostic_log_path(
            workspace_path=workspace,
            language="python",
        )

        assert result1 == result2
