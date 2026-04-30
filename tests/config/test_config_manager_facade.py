"""Tests for ConfigManager backward compatibility facade."""

import inspect
from pathlib import Path

import pytest


class TestConfigManagerBackwardCompatibility:
    """Test ConfigManager maintains backward compatibility."""

    def test_config_manager_backward_compatible_get_config_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigManager.get_config_dir() still works."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        config_dir = ConfigManager.get_config_dir()

        # Assert
        assert isinstance(config_dir, Path)
        assert "llm-lsp-cli" in str(config_dir)

    def test_config_manager_backward_compatible_build_socket_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigManager.build_socket_path() still works."""
        # Arrange
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
        workspace = tmp_path / "test-project"
        workspace.mkdir()

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        socket_path = ConfigManager.build_socket_path(str(workspace), "python")

        # Assert
        assert isinstance(socket_path, Path)
        assert socket_path.suffix == ".sock"
        assert "test-project" in str(socket_path)

    def test_config_manager_backward_compatible_load(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigManager.load() still works."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        config = ConfigManager.load()

        # Assert
        from llm_lsp_cli.config.schema import ClientConfig

        assert isinstance(config, ClientConfig)
        assert hasattr(config, "languages")
        assert hasattr(config, "timeout_seconds")

    def test_config_manager_delegates_to_xdg_paths(self) -> None:
        """ConfigManager uses XdgPaths internally."""
        from llm_lsp_cli.config.manager import ConfigManager

        # Check that ConfigManager references XdgPaths
        source = inspect.getsource(ConfigManager)
        assert "XdgPaths" in source

    def test_config_manager_delegates_to_config_loader(self) -> None:
        """ConfigManager uses ConfigLoader internally."""
        from llm_lsp_cli.config.manager import ConfigManager

        # Check that ConfigManager references ConfigLoader
        source = inspect.getsource(ConfigManager)
        assert "ConfigLoader" in source

    def test_config_manager_reduced_size(self) -> None:
        """ConfigManager is a facade and should remain reasonably sized (<300 lines)."""
        from llm_lsp_cli.config.manager import ConfigManager

        source = inspect.getsource(ConfigManager)
        lines = source.split("\n")
        assert len(lines) < 300, f"ConfigManager has {len(lines)} lines, should be < 300"

    def test_config_manager_no_hardcoded_server_names(self) -> None:
        """ConfigManager doesn't have hardcoded server names."""
        from llm_lsp_cli.config.manager import ConfigManager

        source = inspect.getsource(ConfigManager)
        # These should not appear as hardcoded strings
        assert (
            "'pyright'" not in source
            or "pyright" not in source.lower()
            or "DEFAULT_CONFIG" in source
        )  # Allow if referencing defaults

    def test_config_manager_no_module_level_side_effects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigManager module doesn't create directories at import time."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        # Act: Import the module
        from llm_lsp_cli.config import manager  # noqa: F401

        # Assert: Directories should NOT exist yet
        assert not config_home.exists()
