"""Unit tests for config init --force flag."""

import re
from pathlib import Path

import pytest
import yaml


class TestForceFlagContract:
    """CLI interface/shape tests for --force flag."""

    def test_config_init_accepts_force_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force flag is accepted by config init command."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init", "--help"])

        assert result.exit_code == 0
        assert "--force" in result.output or "-f" in result.output

    def test_config_init_accepts_project_and_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--project and --force flags can be combined."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init", "--project", "--force", "--help"])

        assert result.exit_code == 0


class TestForceFlagBehavior:
    """Functional behavior tests for --force flag."""

    def test_force_creates_config_when_not_exists(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force creates config without prompting when none exists."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        result = runner.invoke(app, ["config", "init", "--force"])

        assert result.exit_code == 0
        # Should not prompt when config doesn't exist
        assert "?" not in result.output or "Created" in result.output
        # Config should exist
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        assert config_path.exists()

    def test_force_prompts_before_overwrite(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force prompts before overwriting existing config."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("timeout_seconds: 999\n")

        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        # Provide "y" as input to confirm overwrite
        result = runner.invoke(app, ["config", "init", "--force"], input="y\n")

        assert result.exit_code == 0
        # Should have prompted
        assert "Overwrite" in result.output or "?" in result.output
        # Config should be overwritten with default content
        content = config_path.read_text()
        # Should not contain custom value anymore
        assert "999" not in content

    def test_force_aborts_on_no_response(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force aborts without overwriting when user answers 'N'."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("# EXISTING_MARKER_12345\ntimeout_seconds: 999\n")

        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        # Provide "N" as input to decline overwrite
        result = runner.invoke(app, ["config", "init", "--force"], input="N\n")

        # Should exit gracefully
        assert result.exit_code in (0, 1)
        # Original content should be preserved
        content = config_path.read_text()
        assert "EXISTING_MARKER_12345" in content
        assert "999" in content

    def test_force_works_with_project_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force works with --project flag."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        # Create existing project config
        project_config = tmp_path / ".llm-lsp-cli.yaml"
        project_config.write_text("timeout_seconds: 888\n")

        # Provide "y" to confirm overwrite
        result = runner.invoke(app, ["config", "init", "--project", "--force"], input="y\n")

        assert result.exit_code == 0
        # Config should be overwritten
        content = project_config.read_text()
        # Should have default languages now
        assert "languages:" in content

    def test_force_creates_project_config_when_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force --project creates project config when none exists."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "init", "--project", "--force"])

        assert result.exit_code == 0
        project_config = tmp_path / ".llm-lsp-cli.yaml"
        assert project_config.exists()


class TestForceFlagNegative:
    """Forbidden behavior tests for --force flag."""

    def test_no_silent_overwrite_without_force(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """config init without --force should not silently overwrite."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("# UNIQUE_MARKER_XYZ\ntimeout_seconds: 777\n")

        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        # Run without --force (no input provided since it shouldn't prompt)
        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        assert "already exists" in result.output.lower()
        # Original content should be preserved
        content = config_path.read_text()
        assert "UNIQUE_MARKER_XYZ" in content
        assert "777" in content

    def test_no_overwrite_without_confirmation(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--force should not overwrite if user doesn't confirm."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("timeout_seconds: 555\n")

        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        # Run with --force but provide empty input (default should be No)
        runner.invoke(app, ["config", "init", "--force"], input="\n")

        # Original content should be preserved (default is No)
        content = config_path.read_text()
        assert "555" in content


class TestDefaultConfigValues:
    """Tests for default config content."""

    def test_default_config_values_unchanged(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default config values match expected defaults."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        content = config_path.read_text()
        config = yaml.safe_load(content)

        assert config["trace_lsp"] is False
        assert config["timeout_seconds"] == 30
        assert "python" in config["languages"]

    def test_config_uses_flow_style_for_lists(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config output uses flow style for list fields."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        content = config_path.read_text()

        # Lists should use flow style (inline with brackets)
        # e.g., args: ["--stdio"] or args: [--stdio]
        # NOT block-style:
        #   args:
        #     - --stdio

        # Check for flow style args (brackets present after args:)
        assert re.search(r"args:\s*\[", content) is not None, \
            f"Expected flow-style args, got:\n{content}"

        # Check for flow style root_markers
        assert re.search(r"root_markers:\s*\[", content) is not None, \
            f"Expected flow-style root_markers, got:\n{content}"

    def test_config_uses_block_style_for_mappings(
        self, xdg_test_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config output uses block style for mappings (not inline)."""
        from typer.testing import CliRunner

        from llm_lsp_cli.cli import app

        config_dir = xdg_test_env
        runner = CliRunner()
        monkeypatch.chdir(config_dir.parent)

        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        config_path = config_dir / "llm-lsp-cli" / "config.yaml"
        content = config_path.read_text()

        # Mappings should use block style (not inline with {})
        assert "languages:" in content
        assert "languages: {" not in content
        # Python language config should be block style
        assert "python:" in content
        assert "python: {" not in content
