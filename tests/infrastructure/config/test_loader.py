"""Tests for ConfigLoader."""

import json
from pathlib import Path

import pytest


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    def test_config_loader_loads_valid_json(self, tmp_path: Path) -> None:
        """ConfigLoader loads valid JSON configuration."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright-langserver", "args": ["--stdio"]}},
            "trace_lsp": False,
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["languages"]["python"]["command"] == "pyright-langserver"
        assert loaded["trace_lsp"] is False
        assert loaded["timeout_seconds"] == 30

    def test_config_loader_validates_schema(self, tmp_path: Path) -> None:
        """ConfigLoader validates configuration schema."""
        # Arrange
        config_file = tmp_path / "config.json"
        # Missing required 'languages' key
        config_data = {"trace_lsp": False}
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigValidationError

        # Act/Assert
        with pytest.raises(ConfigValidationError):
            ConfigLoader.load(config_file)

    def test_config_loader_expands_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader expands environment variables."""
        # Arrange
        monkeypatch.setenv("TEST_SOCKET_PATH", "/tmp/test-socket")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright-langserver", "args": ["--stdio"]}},
            "socket_path": "$TEST_SOCKET_PATH",
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["socket_path"] == "/tmp/test-socket"

    def test_config_loader_handles_missing_file(self, tmp_path: Path) -> None:
        """ConfigLoader raises error for missing file."""
        # Arrange
        config_file = tmp_path / "nonexistent.json"

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigFileNotFoundError

        # Act/Assert
        with pytest.raises(ConfigFileNotFoundError):
            ConfigLoader.load(config_file)

    def test_config_loader_handles_invalid_json(self, tmp_path: Path) -> None:
        """ConfigLoader raises error for invalid JSON."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigParseError

        # Act/Assert
        with pytest.raises(ConfigParseError):
            ConfigLoader.load(config_file)

    def test_config_loader_saves_config(self, tmp_path: Path) -> None:
        """ConfigLoader saves configuration to file."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright-langserver", "args": ["--stdio"]}},
            "trace_lsp": True,
            "timeout_seconds": 60,
        }

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        ConfigLoader.save(config_file, config_data)

        # Assert
        assert config_file.exists()
        loaded = json.loads(config_file.read_text())
        assert loaded["trace_lsp"] is True
        assert loaded["timeout_seconds"] == 60

    def test_config_loader_creates_parent_directories(self, tmp_path: Path) -> None:
        """ConfigLoader creates parent directories when saving."""
        # Arrange
        config_file = tmp_path / "nested" / "dir" / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright-langserver", "args": ["--stdio"]}},
            "timeout_seconds": 30,
        }

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        ConfigLoader.save(config_file, config_data)

        # Assert
        assert config_file.exists()
        assert config_file.parent.exists()

    def test_config_loader_load_with_defaults(self, tmp_path: Path) -> None:
        """ConfigLoader.load() can provide defaults for missing keys."""
        # Arrange
        config_file = tmp_path / "config.json"
        # Minimal config
        config_data = {"languages": {"python": {"command": "pyright-langserver"}}}
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        defaults = {
            "trace_lsp": False,
            "timeout_seconds": 30,
        }

        # Act
        loaded = ConfigLoader.load(config_file, defaults=defaults)

        # Assert
        assert loaded["trace_lsp"] is False
        assert loaded["timeout_seconds"] == 30

    def test_config_loader_expands_nested_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader expands env vars in nested structures."""
        # Arrange
        monkeypatch.setenv("PYRIGHT_CMD", "pyright-langserver")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "$PYRIGHT_CMD", "args": ["--stdio"]}},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["languages"]["python"]["command"] == "pyright-langserver"

    def test_config_loader_brace_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader expands ${VAR} style env vars."""
        # Arrange
        monkeypatch.setenv("TEST_PATH", "/bracket-test")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": ["--stdio"]}},
            "socket_path": "${TEST_PATH}/socket",
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["socket_path"] == "/bracket-test/socket"
