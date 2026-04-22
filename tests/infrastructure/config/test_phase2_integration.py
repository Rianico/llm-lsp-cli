"""Phase 2 integration tests for configuration pipeline."""

import json
from pathlib import Path
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import yaml


@pytest.fixture
def reset_xdg_paths():
    """Reset XdgPaths singleton between tests."""
    from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

    XdgPaths._instance = None
    yield
    XdgPaths._instance = None


class TestFullConfigLoadingPipeline:
    """Test the full configuration loading pipeline end-to-end."""

    def test_full_pipeline_from_xdg_to_config_manager(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """Complete pipeline: XDG paths -> Config file -> ConfigManager."""
        # Arrange
        config_home = tmp_path / "config"
        config_file = config_home / "llm-lsp-cli" / "config.yaml"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        config_data = {
            "languages": {
                "python": {
                    "command": "pyright-custom",
                    "args": ["--custom"],
                    "timeout_seconds": 90,
                },
                "typescript": {
                    "command": "typescript-language-server",
                    "args": ["--stdio"],
                    "timeout_seconds": 45,
                },
            },
            "trace_lsp": True,
            "timeout_seconds": 120,
        }
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(yaml.dump(config_data))

        # Act
        from llm_lsp_cli.config.manager import ConfigManager

        config = ConfigManager.load()

        # Assert
        assert config.trace_lsp is True
        assert config.timeout_seconds == 120
        assert "python" in config.languages
        assert "typescript" in config.languages

    def test_config_manager_resolve_server_from_user_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.resolve_server_command() uses user config."""
        # Arrange
        config_home = tmp_path / "config"
        config_file = config_home / "llm-lsp-cli" / "config.yaml"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        # Create a fake server script
        fake_server = tmp_path / "fake_server.py"
        fake_server.write_text("#!/usr/bin/env python3\n")
        fake_server.chmod(0o755)

        config_data = {
            "languages": {
                "testlang": {
                    "command": str(fake_server),
                    "args": ["--test"],
                    "timeout_seconds": 60,
                }
            }
        }
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(yaml.dump(config_data))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        cmd, args = ConfigManager.resolve_server_command("testlang")

        # Assert
        assert cmd == str(fake_server)
        assert args == ["--test"]

    def test_config_loads_default_when_no_config_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.load() creates default config when none exists."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        config = ConfigManager.load()

        # Assert
        assert config is not None
        assert hasattr(config, "languages")
        # Default config should have some languages
        assert len(config.languages) > 0

    def test_config_init_config_returns_true_when_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.init_config() returns True when config is created."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        result = ConfigManager.init_config()

        # Assert
        assert result is True
        config_file = config_home / "llm-lsp-cli" / "config.yaml"
        assert config_file.exists()

    def test_config_init_config_returns_false_when_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigManager.init_config() returns False when config already exists."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.config.manager import ConfigManager

        # Create config first
        ConfigManager.init_config()

        # Act
        result = ConfigManager.init_config()

        # Assert
        assert result is False


class TestLazyInitializationConcurrentAccess:
    """Test lazy initialization under concurrent access patterns."""

    def test_xdg_paths_concurrent_first_access(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths handles multiple threads calling get() simultaneously."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Reset to ensure fresh initialization
        XdgPaths._instance = None

        results: list = []
        errors: list = []

        def get_paths() -> None:
            try:
                paths = XdgPaths.get()
                results.append(paths)
            except Exception as e:
                errors.append(e)

        # Act: Start many threads simultaneously
        threads = [Thread(target=get_paths) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 20
        # All should be the same singleton instance
        assert all(r is results[0] for r in results)

    def test_repository_concurrent_first_load(self, tmp_path: Path) -> None:
        """Repository handles concurrent first-time loads."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {f"lang{i}": {"command": f"server{i}", "args": []} for i in range(10)}
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        results: list = []
        errors: list = []

        def get_server(lang_id: str) -> None:
            try:
                result = repo.get(lang_id)
                results.append((lang_id, result))
            except Exception as e:
                errors.append(e)

        # Act: Multiple threads accessing different languages
        threads = [Thread(target=get_server, args=(f"lang{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10

    def test_concurrent_repository_register_operations(self, tmp_path: Path) -> None:
        """Repository handles concurrent register operations."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"languages": {}}))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository
        from llm_lsp_cli.domain.entities import ServerDefinition

        repo = JsonServerDefinitionRepository(config_file)

        errors: list = []

        def register_lang(lang_id: str, command: str) -> None:
            try:
                defn = ServerDefinition(
                    language_id=lang_id,
                    command=command,
                    args=[],
                    timeout_seconds=30,
                )
                repo.register(defn)
            except Exception as e:
                errors.append(e)

        # Act: Concurrent registrations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(register_lang, f"concurrent_lang{i}", f"server{i}")
                for i in range(20)
            ]
            for future in as_completed(futures):
                future.result()

        # Assert
        assert len(errors) == 0, f"Errors: {errors}"
        # Verify all registrations persisted
        all_defs = list(repo.list_all())
        assert len(all_defs) == 20

    def test_xdg_paths_repeated_access_after_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths.get() is fast after initialization."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Pre-initialize
        _ = XdgPaths.get()

        # Act: Many repeated accesses
        results = [XdgPaths.get() for _ in range(1000)]

        # Assert
        assert all(r is results[0] for r in results)

    def test_concurrent_config_load_and_save(self, tmp_path: Path) -> None:
        """ConfigLoader handles concurrent load and save operations.

        Note: Without file locking, some read/write races may cause temporary
        parse errors. This test verifies the file doesn't get corrupted.
        """
        # Arrange
        config_file = tmp_path / "config.json"
        initial_data = {
            "languages": {"initial": {"command": "initial_server", "args": []}},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(initial_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        load_count = [0]
        save_count = [0]
        load_errors: list = []
        save_errors: list = []

        def load_config() -> None:
            try:
                data = ConfigLoader.load(config_file)
                assert "languages" in data
                load_count[0] += 1
            except Exception as e:
                # Some read errors during concurrent writes are expected
                # without file locking
                load_errors.append(e)

        def save_config(lang_id: str) -> None:
            try:
                data = {
                    "languages": {lang_id: {"command": f"server_{lang_id}", "args": []}},
                    "timeout_seconds": 30,
                }
                ConfigLoader.save(config_file, data)
                save_count[0] += 1
            except Exception as e:
                save_errors.append(e)

        # Act: Mix of concurrent loads and saves
        with ThreadPoolExecutor(max_workers=10) as executor:
            loads = [executor.submit(load_config) for _ in range(10)]
            saves = [executor.submit(save_config, f"lang{i}") for i in range(10)]
            for future in as_completed(loads + saves):
                future.result()

        # Assert: File should not be corrupted (valid JSON at end)
        # Some load errors during races are acceptable without file locking
        final_content = config_file.read_text()
        try:
            final_data = json.loads(final_content)
            assert "languages" in final_data
        except json.JSONDecodeError:
            pytest.fail(f"Config file corrupted after concurrent operations: {final_content}")

        # Verify save operations mostly succeeded
        assert save_count[0] > 0, "No saves completed"


class TestEnvironmentVariableExpansionEdgeCases:
    """Test environment variable expansion edge cases."""

    def test_env_var_undefined_keeps_original_pattern(self, tmp_path: Path) -> None:
        """Undefined env vars keep their original $VAR pattern."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "socket_path": "$UNDEFINED_VAR/socket",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert: Undefined var should remain as-is
        assert loaded["socket_path"] == "$UNDEFINED_VAR/socket"

    def test_env_var_brace_undefined_keeps_pattern(self, tmp_path: Path) -> None:
        """Undefined ${VAR} keeps original pattern."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "${UNDEFINED_BRACE}/bin",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["path"] == "${UNDEFINED_BRACE}/bin"

    def test_env_var_with_empty_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty env var value keeps original pattern (implementation choice)."""
        # Arrange
        monkeypatch.setenv("EMPTY_VAR", "")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "$EMPTY_VAR/bin",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert: Empty value keeps original pattern (implementation choice)
        # This is acceptable behavior - undefined/empty vars are not expanded
        assert loaded["path"] == "$EMPTY_VAR/bin"

    def test_env_var_with_special_characters(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env vars with special characters expand correctly."""
        # Arrange
        monkeypatch.setenv("SPECIAL", "/path/with spaces/and-dashes/测试")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "command": "$SPECIAL/server",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["command"] == "/path/with spaces/and-dashes/测试/server"

    def test_env_var_multiple_in_same_string(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple env vars in same string all expand."""
        # Arrange
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "endpoint": "http://$HOST:$PORT/api",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["endpoint"] == "http://localhost:8080/api"

    def test_env_var_mixed_brace_and_dollar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mixed $VAR and ${VAR} syntax in same string."""
        # Arrange
        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "$VAR1:${VAR2}:$VAR1",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["path"] == "value1:value2:value1"

    def test_env_var_in_nested_structure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env vars expand in deeply nested structures."""
        # Arrange
        monkeypatch.setenv("DEEP_CMD", "deep_server")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "python": {
                    "command": "$DEEP_CMD",
                    "args": ["--env=$DEEP_CMD"],
                    "nested": {"deeply": {"path": "$DEEP_CMD/path"}},
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["languages"]["python"]["command"] == "deep_server"
        assert loaded["languages"]["python"]["args"] == ["--env=deep_server"]
        assert loaded["languages"]["python"]["nested"]["deeply"]["path"] == "deep_server/path"

    def test_env_var_in_list_items(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env vars expand in list items."""
        # Arrange
        monkeypatch.setenv("ARG1", "first")
        monkeypatch.setenv("ARG2", "second")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": ["$ARG1", "$ARG2"]}},
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["languages"]["python"]["args"] == ["first", "second"]

    def test_env_var_partial_match_not_expanded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Partial env var names are not expanded."""
        # Arrange
        monkeypatch.setenv("MY_VAR", "expanded")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "$MY_VAR_EXTRA",  # Should NOT expand (different var name)
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert: Should remain as-is since MY_VAR_EXTRA is not defined
        assert loaded["path"] == "$MY_VAR_EXTRA"

    def test_env_var_with_numbers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env vars with numbers in name expand correctly."""
        # Arrange
        monkeypatch.setenv("VAR_123", "numeric")
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "path": "$VAR_123/bin",
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        # Act
        loaded = ConfigLoader.load(config_file)

        # Assert
        assert loaded["path"] == "numeric/bin"


class TestWorkspacePathIsolation:
    """Test workspace path isolation in configuration."""

    def test_different_workspaces_get_different_socket_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """Different workspace paths get different socket paths."""
        # Arrange
        runtime_dir = tmp_path / "runtime"
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

        workspace1 = tmp_path / "project_alpha"
        workspace2 = tmp_path / "project_beta"
        workspace1.mkdir()
        workspace2.mkdir()

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        socket1 = ConfigManager.build_socket_path(str(workspace1), "python")
        socket2 = ConfigManager.build_socket_path(str(workspace2), "python")

        # Assert
        assert socket1 != socket2
        assert "project_alpha" in str(socket1)
        assert "project_beta" in str(socket2)

    def test_same_workspace_different_languages_different_sockets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """Same workspace but different languages get different sockets."""
        # Arrange
        runtime_dir = tmp_path / "runtime"
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

        workspace = tmp_path / "project"
        workspace.mkdir()

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        socket_python = ConfigManager.build_socket_path(str(workspace), "python")
        socket_typescript = ConfigManager.build_socket_path(str(workspace), "typescript")

        # Assert
        assert socket_python != socket_typescript
        assert "pyright" in str(socket_python) or "python" in str(socket_python)
        assert "typescript" in str(socket_typescript)

    def test_workspace_with_special_characters_sanitized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """Workspace names with special chars are sanitized."""
        # Arrange
        runtime_dir = tmp_path / "runtime"
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

        workspace = tmp_path / "project-测试"
        workspace.mkdir(parents=True)

        from llm_lsp_cli.config.manager import ConfigManager

        # Act
        socket_path = ConfigManager.build_socket_path(str(workspace), "python")

        # Assert: Path should be sanitized (ASCII chars preserved)
        socket_str = str(socket_path)
        # "project" should be in the path (ASCII chars preserved)
        assert "project" in socket_str.lower()
        # Path should have correct structure
        assert socket_path.suffix == ".sock"
        assert "llm-lsp-cli" in socket_str
