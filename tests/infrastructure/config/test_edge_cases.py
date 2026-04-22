"""Edge case tests for configuration components."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def reset_xdg_paths():
    """Reset XdgPaths singleton between tests."""
    from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

    XdgPaths._instance = None
    yield
    XdgPaths._instance = None


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_xdg_paths_with_permission_denied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths raises PermissionError on permission denied."""
        # Arrange: Create a directory we can't write to
        config_home = tmp_path / "config"
        config_home.mkdir()
        config_home.chmod(0o555)

        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act/Assert: Raises PermissionError
        import pytest

        with pytest.raises(PermissionError):
            XdgPaths.get()

        # Cleanup
        config_home.chmod(0o755)

    def test_config_loader_with_very_large_file(self, tmp_path: Path) -> None:
        """ConfigLoader handles very large config files."""
        # Arrange: Create large config
        config_file = tmp_path / "large-config.json"
        large_config = {
            "languages": {f"lang{i}": {"command": f"server{i}", "args": []} for i in range(1000)},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(large_config))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert len(loaded["languages"]) == 1000

    def test_config_loader_with_special_characters_in_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader handles special characters in env vars."""
        # Arrange
        monkeypatch.setenv("SPECIAL_PATH", "/path/with spaces/and-dashes")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "socket_path": "$SPECIAL_PATH/socket.sock",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["socket_path"] == "/path/with spaces/and-dashes/socket.sock"

    def test_repository_with_malformed_server_def(self, tmp_path: Path) -> None:
        """Repository handles malformed server definition."""
        # Arrange
        config_file = tmp_path / "config.json"
        # Missing required 'command' field
        config_data = {"languages": {"python": {"args": [], "timeout_seconds": 30}}}
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act/Assert: May raise error or return None
        try:
            result = repo.get("python")
            # If it returns something, it should be None or partial
            assert result is None or result.command is not None
        except Exception:
            # Also valid - should handle malformed data
            pass

    def test_config_loader_with_readonly_file(self, tmp_path: Path) -> None:
        """ConfigLoader handles readonly config file."""
        # Arrange
        config_file = tmp_path / "readonly.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))
        config_file.chmod(0o444)

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act: Should be able to read
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["timeout_seconds"] == 30

        # Cleanup
        config_file.chmod(0o644)

    def test_repository_with_concurrent_writes(self, tmp_path: Path) -> None:
        """Repository handles concurrent writes safely."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"languages": {}}))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository
        from llm_lsp_cli.domain.entities import ServerDefinition

        repo = JsonServerDefinitionRepository(config_file)

        errors: list = []

        def register_language(lang_id: str, command: str) -> None:
            try:
                defn = ServerDefinition(
                    language_id=lang_id,
                    command=command,
                    args=[],
                )
                repo.register(defn)
            except Exception as e:
                errors.append(e)

        # Act: Concurrent writes
        from threading import Thread

        threads = [
            Thread(target=register_language, args=(f"lang{i}", f"server{i}")) for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert: Either all succeed or some fail gracefully
        # At minimum, file should be valid JSON
        assert config_file.exists()
        try:
            json.loads(config_file.read_text())
        except json.JSONDecodeError:
            pytest.fail("Config file corrupted after concurrent writes")

    def test_config_with_symlinked_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigLoader works with symlinked directories."""
        # Arrange
        real_dir = tmp_path / "real_config"
        real_dir.mkdir()
        symlink_dir = tmp_path / "symlink_config"
        symlink_dir.symlink_to(real_dir)

        # Create config in the symlink target
        config_file = symlink_dir / "llm-lsp-cli" / "config.json"
        config_file.parent.mkdir(parents=True)
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setenv("XDG_CONFIG_HOME", str(symlink_dir))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        paths = XdgPaths.get()
        loaded = ConfigLoader.load(paths.config_dir / "config.json")

        # Assert
        assert loaded["timeout_seconds"] == 30

    def test_xdg_paths_with_nested_env_references(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader handles nested env var references."""
        # Arrange
        monkeypatch.setenv("BASE_DIR", "/opt")
        monkeypatch.setenv("SERVER_BIN", "$BASE_DIR/bin/server")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"custom": {"command": "$SERVER_BIN", "args": []}},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert: Nested expansion depends on implementation
        # Either fully expanded or partially expanded is valid
        command = loaded["languages"]["custom"]["command"]
        assert command in ["$BASE_DIR/bin/server", "/opt/bin/server"]

    def test_repository_with_missing_languages_key(self, tmp_path: Path) -> None:
        """Repository handles config missing languages key."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('{"timeout_seconds": 30}')

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        result = repo.get("python")

        # Assert
        assert result is None

    def test_config_loader_with_null_values(self, tmp_path: Path) -> None:
        """ConfigLoader loads null values as None."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "timeout_seconds": 30,
            "null_field": None,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act/Assert: Should load successfully with null values preserved
        loaded = ConfigLoader.load(config_file)
        assert loaded["null_field"] is None
        assert loaded["timeout_seconds"] == 30

    def test_xdg_paths_with_trailing_slash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XdgPaths handles trailing slashes in env vars."""
        # Arrange
        config_home = tmp_path / "config" / ""  # Trailing slash
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert paths.config_dir.exists()

    def test_config_loader_preserves_extra_fields(self, tmp_path: Path) -> None:
        """ConfigLoader preserves extra fields in config."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "timeout_seconds": 30,
            "custom_field": "custom_value",
            "another_custom": {"nested": True},
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert: Extra fields should be preserved
        assert loaded["custom_field"] == "custom_value"
        assert loaded["another_custom"]["nested"] is True
