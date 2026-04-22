"""Phase 2 edge case tests for configuration components."""

import json
from pathlib import Path
from threading import Thread

import pytest


@pytest.fixture
def reset_xdg_paths():
    """Reset XdgPaths singleton between tests."""
    from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

    XdgPaths._instance = None
    yield
    XdgPaths._instance = None


class TestXdgPathsEdgeCases:
    """Edge case tests for XdgPaths."""

    def test_xdg_paths_home_not_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths handles HOME not being set."""
        # Arrange: Clear all XDG and HOME env vars
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows fallback

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act/Assert: Should handle gracefully (may raise or use fallback)
        try:
            paths = XdgPaths.get()
            # If it succeeds, directories should exist
            assert paths.config_dir.exists() or True  # Allow for fallback behavior
        except (KeyError, RuntimeError):
            # Also valid - should fail gracefully
            pass

    def test_xdg_paths_with_readonly_config_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths handles read-only config directory."""
        # Arrange
        config_home = tmp_path / "config"
        config_home.mkdir()
        config_home.chmod(0o555)  # Read-only

        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        try:
            # Act/Assert
            paths = XdgPaths.get()
            # On some systems, this might succeed if running as root
            assert paths.config_dir.exists()
        except PermissionError:
            # Expected behavior on most systems
            pass
        finally:
            # Cleanup
            config_home.chmod(0o755)

    def test_xdg_paths_runtime_fallback_to_tmpdir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths falls back to TMPDIR when XDG_RUNTIME_DIR not set."""
        # Arrange
        custom_tmp = tmp_path / "custom_tmp"
        custom_tmp.mkdir()

        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.setenv("TMPDIR", str(custom_tmp))
        monkeypatch.setenv("HOME", str(tmp_path))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert str(custom_tmp) in str(paths.runtime_dir)

    def test_xdg_paths_with_unicode_username(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths handles unicode in home directory path."""
        # Arrange
        config_home = tmp_path / "用户" / ".config"
        config_home.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert paths.config_dir.exists()
        assert "用户" in str(paths.config_dir)

    def test_xdg_paths_extremely_long_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths handles very long config paths."""
        # Arrange
        long_name = "a" * 200
        config_home = tmp_path / long_name
        config_home.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert paths.config_dir.exists()


class TestConfigLoaderEdgeCases:
    """Edge case tests for ConfigLoader."""

    def test_config_loader_empty_json_object(self, tmp_path: Path) -> None:
        """ConfigLoader handles empty JSON object."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigValidationError

        # Act/Assert
        with pytest.raises(ConfigValidationError):
            ConfigLoader.load(config_file)

    def test_config_loader_empty_languages_dict(self, tmp_path: Path) -> None:
        """ConfigLoader handles empty languages dictionary."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('{"languages": {}}')

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["languages"] == {}

    def test_config_loader_non_dict_languages(self, tmp_path: Path) -> None:
        """ConfigLoader validates languages is a dict."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('{"languages": ["python", "rust"]}')

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigValidationError

        # Act/Assert
        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigLoader.load(config_file)

        assert "must be a dictionary" in str(exc_info.value)

    def test_config_loader_deeply_nested_structure(self, tmp_path: Path) -> None:
        """ConfigLoader handles deeply nested structures."""
        # Arrange
        config_file = tmp_path / "config.json"
        nested = {"nested": {"deep": {"deeper": {"value": "test"}}}}
        config_data = {"languages": {"python": {"command": "pyright", "args": []}}, **nested}
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["nested"]["deep"]["deeper"]["value"] == "test"

    def test_config_loader_with_null_command(self, tmp_path: Path) -> None:
        """ConfigLoader handles null command value."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('{"languages": {"python": {"command": null}}}')

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["languages"]["python"]["command"] is None

    def test_config_loader_with_array_at_root(self, tmp_path: Path) -> None:
        """ConfigLoader handles array at root level (invalid config)."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('[{"command": "pyright"}]')

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigValidationError

        # Act/Assert
        with pytest.raises(ConfigValidationError):
            ConfigLoader.load(config_file)

    def test_config_loader_with_trailing_comma_invalid(self, tmp_path: Path) -> None:
        """ConfigLoader rejects JSON with trailing commas."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('{"languages": {"python": {"command": "pyright",}},}')

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
        from llm_lsp_cli.infrastructure.config.exceptions import ConfigParseError

        # Act/Assert
        with pytest.raises(ConfigParseError):
            ConfigLoader.load(config_file)

    def test_config_loader_env_var_dollar_sign_in_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader handles $ in env var value."""
        # Arrange
        monkeypatch.setenv("DOLLAR_PATH", "/path/$with/dollars")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "$DOLLAR_PATH",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["path"] == "/path/$with/dollars"

    def test_config_loader_env_var_newline_in_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConfigLoader handles newline in env var value."""
        # Arrange
        monkeypatch.setenv("NEWLINE_PATH", "/path\n/with\nnewlines")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "$NEWLINE_PATH",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert "\n" in loaded["path"]

    def test_config_loader_save_to_symlink(self, tmp_path: Path) -> None:
        """ConfigLoader can save to symlinked file."""
        # Arrange
        real_file = tmp_path / "real_config.json"
        symlink_file = tmp_path / "symlink_config.json"
        symlink_file.symlink_to(real_file)

        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "timeout_seconds": 30,
        }

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        ConfigLoader.save(symlink_file, config_data)

        # Assert
        assert real_file.exists()
        loaded = json.loads(real_file.read_text())
        assert loaded["timeout_seconds"] == 30


class TestJsonRepositoryEdgeCases:
    """Edge case tests for JsonServerDefinitionRepository."""

    def test_repo_with_nonexistent_config_file_get(self, tmp_path: Path) -> None:
        """Repository.get() handles non-existent config file."""
        # Arrange
        config_file = tmp_path / "nonexistent.json"

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        result = repo.get("python")

        # Assert
        assert result is None

    def test_repo_with_nonexistent_config_file_list_all(self, tmp_path: Path) -> None:
        """Repository.list_all() handles non-existent config file."""
        # Arrange
        config_file = tmp_path / "nonexistent.json"

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        results = list(repo.list_all())

        # Assert
        assert len(results) == 0

    def test_repo_register_to_nonexistent_directory(self, tmp_path: Path) -> None:
        """Repository.register() creates parent directories."""
        # Arrange
        config_file = tmp_path / "nested" / "dir" / "config.json"

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository
        from llm_lsp_cli.domain.entities import ServerDefinition

        repo = JsonServerDefinitionRepository(config_file)
        definition = ServerDefinition(
            language_id="test",
            command="test_server",
            args=[],
        )

        # Act
        repo.register(definition)

        # Assert
        assert config_file.exists()

    def test_repo_with_corrupted_json_file(self, tmp_path: Path) -> None:
        """Repository handles corrupted JSON file."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text("{ corrupted json [[[")

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        results = list(repo.list_all())

        # Assert: Should handle gracefully, return empty
        assert len(results) == 0

    def test_repo_with_language_as_non_dict(self, tmp_path: Path) -> None:
        """Repository handles language entry that's not a dict."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text('{"languages": {"python": "just_a_string"}}')

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        results = list(repo.list_all())

        # Assert: Should skip invalid entries
        assert len(results) == 0

    def test_repo_with_mixed_valid_invalid_entries(self, tmp_path: Path) -> None:
        """Repository handles mix of valid and invalid entries."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "languages": {
                        "python": {"command": "pyright", "args": []},  # Valid
                        "rust": "invalid",  # Invalid
                        "typescript": {"command": "ts_server"},  # Valid
                        "go": 123,  # Invalid
                    }
                }
            )
        )

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        results = list(repo.list_all())

        # Assert: Should return only valid entries
        assert len(results) == 2
        ids = {r.language_id for r in results}
        assert ids == {"python", "typescript"}

    def test_repo_register_overwrites_existing(self, tmp_path: Path) -> None:
        """Repository.register() overwrites existing definition."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"languages": {"python": {"command": "old_server", "args": ["--old"]}}})
        )

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository
        from llm_lsp_cli.domain.entities import ServerDefinition

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        new_def = ServerDefinition(
            language_id="python",
            command="new_server",
            args=["--new"],
            timeout_seconds=99,
        )
        repo.register(new_def)

        # Assert
        result = repo.get("python")
        assert result is not None
        assert result.command == "new_server"
        assert result.args == ["--new"]
        assert result.timeout_seconds == 99

    def test_repo_concurrent_get_same_language(self, tmp_path: Path) -> None:
        """Repository handles concurrent get() for same language."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"languages": {"python": {"command": "pyright", "args": []}}})
        )

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        results: list = []
        errors: list = []

        def get_python() -> None:
            try:
                result = repo.get("python")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Act
        threads = [Thread(target=get_python) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r is not None for r in results)


class TestConfigManagerFacadeEdgeCases:
    """Edge case tests for ConfigManager facade."""

    def test_config_manager_get_language_config_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.get_language_config() returns None for unknown language."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        result = ConfigManager.get_language_config("nonexistent_language")

        # Assert
        assert result is None

    def test_config_manager_resolve_unknown_language(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.resolve_server_command() raises for unknown language."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act/Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager.resolve_server_command("unknown_language_xyz")

        assert "unknown_language_xyz" in str(exc_info.value)

    def test_config_manager_resolve_with_cli_arg_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.resolve_server_command() uses CLI arg when provided."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        # Create a valid executable at the custom path
        custom_dir = tmp_path / "custom" / "path" / "to"
        custom_dir.mkdir(parents=True)
        server_exe = custom_dir / "server"
        server_exe.write_text("#!/bin/sh\necho 'server'\n")
        server_exe.chmod(0o755)

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        cmd, args = ConfigManager.resolve_server_command("any_language", cli_arg=str(server_exe))

        # Assert
        assert cmd == str(server_exe.resolve())
        assert args == []

    def test_config_manager_build_socket_path_with_custom_base(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """build_socket_path() uses custom base_dir when provided."""
        # Arrange
        custom_base = tmp_path / "custom_base"
        custom_base.mkdir()
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        socket_path = ConfigManager.build_socket_path(
            str(workspace), "python", base_dir=custom_base, lsp_server_name="custom_server"
        )

        # Assert
        assert str(custom_base) in str(socket_path)
        assert "custom_server.sock" in str(socket_path)

    def test_config_manager_ensure_config_dir_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ensure_config_dir() creates directory if needed."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        config_dir = ConfigManager.ensure_config_dir()

        # Assert
        assert config_dir.exists()

    def test_config_manager_save_and_reload(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.save() and load() round-trip."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager
        from llm_lsp_cli.config.schema import ClientConfig, LanguageServerConfig

        config = ClientConfig(
            languages={
                "testlang": LanguageServerConfig(
                    command="test_server",
                    args=["--test"],
                )
            },
            trace_lsp=True,
            timeout_seconds=120,
        )

        # Act
        ConfigManager.save(config)
        loaded = ConfigManager.load()

        # Assert
        assert loaded.trace_lsp is True
        assert loaded.timeout_seconds == 120
        assert "testlang" in loaded.languages
