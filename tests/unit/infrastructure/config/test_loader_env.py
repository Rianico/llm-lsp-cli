"""Tests for ConfigLoader environment variable expansion in YAML."""

import pytest
from pathlib import Path


class TestConfigLoaderEnvExpansion:
    """Test environment variable expansion in YAML."""

    def test_env_var_dollar_pattern(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """$VAR pattern expands correctly."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        monkeypatch.setenv("MY_VAR", "/my/path")

        yaml_content = """
languages:
  python:
    command: pyright-langserver
    env:
      CUSTOM_PATH: $MY_VAR
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        data = ConfigLoader.load(config_file, defaults={})

        assert data["languages"]["python"]["env"]["CUSTOM_PATH"] == "/my/path"

    def test_env_var_braces_pattern(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """${VAR} pattern expands correctly."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        monkeypatch.setenv("MY_VAR", "/my/path")

        yaml_content = """
languages:
  python:
    command: pyright-langserver
    env:
      CUSTOM_PATH: ${MY_VAR}
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        data = ConfigLoader.load(config_file, defaults={})

        assert data["languages"]["python"]["env"]["CUSTOM_PATH"] == "/my/path"

    def test_env_var_missing_remains_literal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing env vars remain as literal string."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Ensure this var doesn't exist
        monkeypatch.delenv("NONEXISTENT_VAR_12345", raising=False)

        yaml_content = """
languages:
  python:
    command: pyright-langserver
    env:
      CUSTOM_PATH: $NONEXISTENT_VAR_12345
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        data = ConfigLoader.load(config_file, defaults={})

        # Should remain as literal string
        assert data["languages"]["python"]["env"]["CUSTOM_PATH"] == "$NONEXISTENT_VAR_12345"

    def test_env_expansion_in_nested_values(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env expansion works in nested values."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        monkeypatch.setenv("WORKSPACE", "/workspace")

        yaml_content = """
languages:
  python:
    command: pyright-langserver
    args:
      - --root-path
      - $WORKSPACE/project
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        data = ConfigLoader.load(config_file, defaults={})

        assert data["languages"]["python"]["args"][1] == "/workspace/project"
