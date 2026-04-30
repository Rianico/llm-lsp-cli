"""Unit tests for layered configuration loading in ConfigManager.load()."""

import os
from pathlib import Path

import pytest

from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths


@pytest.fixture(autouse=True)
def reset_xdg_paths() -> None:
    """Reset XdgPaths singleton before each test."""
    XdgPaths.reset_for_testing()


@pytest.fixture
def clean_xdg_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Set up clean XDG environment and return paths."""
    XdgPaths.reset_for_testing()

    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    runtime_dir = tmp_path / "runtime"

    config_dir.mkdir()
    state_dir.mkdir()
    runtime_dir.mkdir()

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_dir))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

    return {
        "config_dir": config_dir,
        "state_dir": state_dir,
        "runtime_dir": runtime_dir,
    }


class TestLoadDefaultsOnly:
    """Tests for loading with no existing configs."""

    def test_load_defaults_only_returns_default_config(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no global or project config exists, returns DEFAULT_CONFIG."""
        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Ensure no project config exists
        monkeypatch.chdir(clean_xdg_env["config_dir"])

        config = ConfigManager.load()

        # Should have default values
        assert config.timeout_seconds == DEFAULT_CONFIG["timeout_seconds"]
        assert config.trace_lsp == DEFAULT_CONFIG["trace_lsp"]
        assert "python" in config.languages


class TestLoadGlobalCreatesFile:
    """Tests for auto-creating global config."""

    def test_load_creates_global_config_when_missing(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When global config doesn't exist, it's auto-created."""
        from llm_lsp_cli.config.manager import ConfigManager

        # Change to directory without project config
        monkeypatch.chdir(clean_xdg_env["config_dir"])

        ConfigManager.load()

        # Global config should be created
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        assert global_config_path.exists()

    def test_load_shows_first_run_notice_when_created(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """First-run notice is displayed when global config is auto-created (in TTY context)."""
        import sys

        from llm_lsp_cli.config.manager import ConfigManager

        # Mock stdout to appear as a TTY so notice is shown
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

        monkeypatch.chdir(clean_xdg_env["config_dir"])

        ConfigManager.load()

        captured = capsys.readouterr()
        # Notice should mention config creation
        assert "Created default config" in captured.out or "Created" in captured.out

    def test_load_no_notice_when_global_exists(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No first-run notice when global config already exists."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Pre-create global config
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_config_path.write_text(yaml.dump(DEFAULT_CONFIG, default_flow_style=False))

        monkeypatch.chdir(clean_xdg_env["config_dir"])

        ConfigManager.load()

        captured = capsys.readouterr()
        # No notice should appear
        assert "Created default config" not in captured.out


class TestLoadProjectOverridesGlobal:
    """Tests for project config overriding global config."""

    def test_load_project_config_overrides_global_values(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Project config values override global config values."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Create global config with custom timeout
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_data = dict(DEFAULT_CONFIG)
        global_data["timeout_seconds"] = 60
        global_config_path.write_text(yaml.dump(global_data, default_flow_style=False))

        # Create project directory with project config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".llm-lsp-cli.yaml"
        project_config.write_text("timeout_seconds: 120\n")

        monkeypatch.chdir(project_dir)

        config = ConfigManager.load()

        # Project value should win
        assert config.timeout_seconds == 120

    def test_load_project_deep_merge_languages(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Project config deep-merges language settings."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Create global config
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_config_path.write_text(yaml.dump(DEFAULT_CONFIG, default_flow_style=False))

        # Create project with language override
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".llm-lsp-cli.yaml"
        project_config.write_text("""
languages:
  python:
    command: basedpyright-langserver
    args: ["--stdio"]
""")

        monkeypatch.chdir(project_dir)

        config = ConfigManager.load()

        # Python command should be overridden
        assert config.languages["python"].command == "basedpyright-langserver"
        # TypeScript should still exist from defaults
        assert "typescript" in config.languages

    def test_load_no_project_config_uses_global(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When no project config exists, global config is used."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Create global config with custom timeout
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_data = dict(DEFAULT_CONFIG)
        global_data["timeout_seconds"] = 45
        global_config_path.write_text(yaml.dump(global_data, default_flow_style=False))

        # Project dir without config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        config = ConfigManager.load()

        # Global value should be used
        assert config.timeout_seconds == 45


class TestEmptyProjectConfig:
    """Tests for empty/whitespace project config handling."""

    def test_empty_project_config_uses_global(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Empty project config file is treated as no override."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Create global config with custom timeout
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_data = dict(DEFAULT_CONFIG)
        global_data["timeout_seconds"] = 90
        global_config_path.write_text(yaml.dump(global_data, default_flow_style=False))

        # Create project with empty config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".llm-lsp-cli.yaml"
        project_config.write_text("")  # Empty file

        monkeypatch.chdir(project_dir)

        config = ConfigManager.load()

        # Global value should be used (empty project config = no override)
        assert config.timeout_seconds == 90

    def test_whitespace_only_project_config_uses_global(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Whitespace-only project config is treated as no override."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager

        # Create global config
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_config_path.write_text(yaml.dump(DEFAULT_CONFIG, default_flow_style=False))

        # Create project with whitespace-only config (valid YAML: just spaces/newlines)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".llm-lsp-cli.yaml"
        project_config.write_text("   \n\n    \n")  # Spaces and newlines only

        monkeypatch.chdir(project_dir)

        config = ConfigManager.load()

        # Defaults should be used
        assert config.timeout_seconds == DEFAULT_CONFIG["timeout_seconds"]


class TestInvalidYamlError:
    """Tests for invalid YAML handling."""

    def test_invalid_global_yaml_raises_config_error(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid YAML in global config raises helpful error."""
        from llm_lsp_cli.config.manager import ConfigManager
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigParseError

        # Create invalid global config
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_config_path.write_text("invalid: [unclosed\n")

        monkeypatch.chdir(clean_xdg_env["config_dir"])

        with pytest.raises(ConfigParseError) as exc_info:
            ConfigManager.load()

        # Error should mention the file path
        assert str(global_config_path) in str(exc_info.value)

    def test_invalid_project_yaml_raises_config_error(
        self, clean_xdg_env: dict[str, Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Invalid YAML in project config raises helpful error."""
        import yaml

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
        from llm_lsp_cli.config.manager import ConfigManager
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigParseError

        # Create valid global config
        global_config_path = clean_xdg_env["config_dir"] / "llm-lsp-cli" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        global_config_path.write_text(yaml.dump(DEFAULT_CONFIG, default_flow_style=False))

        # Create project with invalid config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".llm-lsp-cli.yaml"
        project_config.write_text("invalid: {unclosed\n")

        monkeypatch.chdir(project_dir)

        with pytest.raises(ConfigParseError) as exc_info:
            ConfigManager.load()

        # Error should mention the file path
        assert ".llm-lsp-cli.yaml" in str(exc_info.value)
