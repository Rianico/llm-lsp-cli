"""Unit tests for config init --project flag."""

from pathlib import Path

import pytest


class TestConfigInitProjectFlag:
    """Tests for config init --project flag."""

    def test_init_project_creates_llm_lsp_cli_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--project flag creates .llm-lsp-cli.yaml in current directory."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init", "--project"])

        assert result.exit_code == 0
        project_config = tmp_path / ".llm-lsp-cli.yaml"
        assert project_config.exists()

    def test_init_project_output_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--project flag outputs correct message."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()

        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init", "--project"])

        assert "Created project config" in result.output
        assert ".llm-lsp-cli.yaml" in result.output

    def test_init_project_already_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--project flag is idempotent when config already exists."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()

        monkeypatch.chdir(tmp_path)

        # Create existing config
        project_config = tmp_path / ".llm-lsp-cli.yaml"
        project_config.write_text("timeout_seconds: 999\n")

        result = runner.invoke(app, ["config", "init", "--project"])

        # Should not error
        assert result.exit_code == 0
        # Should indicate it already exists
        assert "already exists" in result.output.lower()
        # Should not modify existing content
        assert "999" in project_config.read_text()

    def test_init_global_creates_in_xdg_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """config init (without --project) creates global config."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app
        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Set up clean XDG environment
        XdgPaths.reset_for_testing()
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        global_config = config_dir / "llm-lsp-cli" / "config.yaml"
        assert global_config.exists()

    def test_init_global_already_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """config init is idempotent when global config exists."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app
        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        XdgPaths.reset_for_testing()
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))

        # Pre-create global config
        global_config = config_dir / "llm-lsp-cli" / "config.yaml"
        global_config.parent.mkdir(parents=True, exist_ok=True)
        global_config.write_text("timeout_seconds: 888\n")

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        assert "already exists" in result.output.lower()
        # Content should not be modified
        assert "888" in global_config.read_text()
