"""Tests for ConfigLoader YAML support."""

import pytest
from pathlib import Path

from llm_lsp_cli.infrastructure.config.exceptions import ConfigParseError


class TestConfigLoaderYamlSupport:
    """Test ConfigLoader handles YAML files."""

    def test_load_yaml_file(self, tmp_path: Path) -> None:
        """Loading .yaml file with yaml.safe_load() succeeds."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        yaml_content = """
languages:
  python:
    command: pyright-langserver
    args:
      - --stdio
trace_lsp: false
timeout_seconds: 30
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        data = ConfigLoader.load(config_file, defaults={})

        assert data["languages"]["python"]["command"] == "pyright-langserver"
        assert data["languages"]["python"]["args"] == ["--stdio"]
        assert data["trace_lsp"] is False
        assert data["timeout_seconds"] == 30

    def test_load_yml_file(self, tmp_path: Path) -> None:
        """Loading .yml file succeeds."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        yml_content = """
languages:
  rust:
    command: rust-analyzer
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(yml_content)

        data = ConfigLoader.load(config_file, defaults={})

        assert data["languages"]["rust"]["command"] == "rust-analyzer"

    def test_load_json_file_backward_compat(self, tmp_path: Path) -> None:
        """Loading .json file still works (backward compat)."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        import json

        json_content = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                    "args": ["--stdio"],
                }
            },
            "trace_lsp": False,
            "timeout_seconds": 30,
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(json_content))

        data = ConfigLoader.load(config_file, defaults={})

        assert data["languages"]["python"]["command"] == "pyright-langserver"

    def test_load_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Invalid YAML raises ConfigParseError."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        invalid_yaml = """
languages:
  python:
    command: pyright-langserver
    args:
      - --stdio
  invalid: [unclosed bracket
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(invalid_yaml)

        with pytest.raises(ConfigParseError):
            ConfigLoader.load(config_file, defaults={})

    def test_load_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Loading non-existent file raises ConfigFileNotFoundError."""
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigFileNotFoundError

        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigFileNotFoundError):
            ConfigLoader.load(config_file, defaults={})
