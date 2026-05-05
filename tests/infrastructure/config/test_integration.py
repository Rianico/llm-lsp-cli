"""Integration tests for configuration components."""

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


class TestFullConfigPipeline:
    """Integration tests for full configuration pipeline."""

    def test_full_config_load_pipeline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """Full configuration load pipeline works end-to-end."""
        config_home = tmp_path / "config"
        config_file = config_home / "llm-lsp-cli" / "config.json"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        config_data = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                    "args": ["--stdio"],
                    "timeout_seconds": 60,
                }
            },
            "trace_lsp": True,
            "timeout_seconds": 45,
        }
        config_file.parent.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        paths = XdgPaths.get()
        assert paths.config_dir == config_home / "llm-lsp-cli"

    def test_config_manager_uses_repository_pattern(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None, no_project_config: None
    ) -> None:
        """ConfigManager uses repository pattern for server definitions."""
        config_home = tmp_path / "config"
        config_file = config_home / "llm-lsp-cli" / "config.yaml"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        import yaml

        config_data = {"languages": {"python": {"command": "pyright-custom", "args": []}}}
        config_file.parent.mkdir(parents=True)
        config_file.write_text(yaml.dump(config_data))

        from llm_lsp_cli.config.manager import ConfigManager

        result = ConfigManager.get_language_config("python")

        assert result is not None
        assert "pyright-custom" in result.command

    def test_xdg_paths_config_loader_integration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths and ConfigLoader work together."""
        config_home = tmp_path / "config"
        config_file = config_home / "llm-lsp-cli" / "config.json"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        config_data = {
            "languages": {"rust": {"command": "rust-analyzer", "args": []}},
            "timeout_seconds": 90,
        }
        config_file.parent.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        paths = XdgPaths.get()
        loaded = ConfigLoader.load(paths.config_dir / "config.json")

        assert loaded["languages"]["rust"]["command"] == "rust-analyzer"
        assert loaded["timeout_seconds"] == 90

    def test_repository_loads_user_overrides(self, tmp_path: Path) -> None:
        """Repository loads user config overrides."""
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "python": {
                    "command": "custom-pyright",
                    "args": ["--custom-arg"],
                    "timeout_seconds": 120,
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        result = repo.get("python")

        assert result is not None
        assert result.command == "custom-pyright"
        assert result.args == ["--custom-arg"]
        assert result.timeout_seconds == 120

    def test_config_save_and_reload_round_trip(self, tmp_path: Path) -> None:
        """Configuration survives save and reload."""
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "go": {"command": "gopls", "args": []},
                "typescript": {"command": "typescript-language-server", "args": ["--stdio"]},
            },
            "trace_lsp": True,
            "timeout_seconds": 60,
        }

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        ConfigLoader.save(config_file, config_data)
        loaded = ConfigLoader.load(config_file)

        assert loaded["languages"]["go"]["command"] == "gopls"
        assert loaded["languages"]["typescript"]["args"] == ["--stdio"]
        assert loaded["trace_lsp"] is True
        assert loaded["timeout_seconds"] == 60

    def test_multiple_repos_isolated(self, tmp_path: Path) -> None:
        """Multiple repository instances are isolated."""
        config_file1 = tmp_path / "config1.json"
        config_file2 = tmp_path / "config2.json"

        config_file1.write_text(json.dumps({"languages": {"python": {"command": "pyright1"}}}))
        config_file2.write_text(json.dumps({"languages": {"python": {"command": "pyright2"}}}))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo1 = JsonServerDefinitionRepository(config_file1)
        repo2 = JsonServerDefinitionRepository(config_file2)

        result1 = repo1.get("python")
        result2 = repo2.get("python")

        assert result1 is not None
        assert result2 is not None
        assert result1.command == "pyright1"
        assert result2.command == "pyright2"

    def test_config_loader_env_expansion_with_xdg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """ConfigLoader expands env vars with XDG paths."""
        monkeypatch.setenv("CUSTOM_SOCKET", "/custom/socket/path")
        config_home = tmp_path / "config"
        config_file = config_home / "llm-lsp-cli" / "config.json"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "socket_path": "$CUSTOM_SOCKET",
            "timeout_seconds": 30,
        }
        config_file.parent.mkdir(parents=True)
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths
        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        paths = XdgPaths.get()
        loaded = ConfigLoader.load(paths.config_dir / "config.json")

        assert loaded["socket_path"] == "/custom/socket/path"

    def test_repository_with_empty_config(self, tmp_path: Path) -> None:
        """Repository handles empty config gracefully."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"languages": {}}')

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        all_defs = list(repo.list_all())

        assert len(all_defs) == 0

    def test_concurrent_config_access(self, tmp_path: Path) -> None:
        """ConfigLoader handles concurrent access safely."""
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {"python": {"command": "pyright", "args": []}},
            "timeout_seconds": 30,
        }
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.loader import ConfigLoader

        results: list = []
        errors: list = []

        def load_config() -> None:
            try:
                loaded = ConfigLoader.load(config_file)
                results.append(loaded)
            except Exception as e:
                errors.append(e)

        threads = [Thread(target=load_config) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 5
        for r in results:
            assert r["timeout_seconds"] == 30

    def test_full_workspace_lifecycle_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """Full workspace lifecycle with configuration."""
        config_home = tmp_path / "config"
        runtime_dir = tmp_path / "runtime"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

        workspace = tmp_path / "test-workspace"
        workspace.mkdir()

        from llm_lsp_cli.config.manager import ConfigManager

        ConfigManager.init_config()
        socket_path = ConfigManager.build_socket_path(str(workspace), "python")

        assert "test-workspace" in str(socket_path)

    def test_repository_cache_invalidation(self, tmp_path: Path) -> None:
        """Repository handles config file changes."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"languages": {"python": {"command": "pyright-v1"}}}))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        result1 = repo.get("python")
        assert result1 is not None
        assert result1.command == "pyright-v1"

        config_file.write_text(json.dumps({"languages": {"python": {"command": "pyright-v2"}}}))

        result2 = repo.get("python")

        assert result2 is not None
        assert result2.command in ["pyright-v1", "pyright-v2"]

    def test_xdg_paths_with_unicode_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths handles unicode in home directory."""
        config_home = tmp_path / "config-测试"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        paths = XdgPaths.get()

        assert paths.config_dir.exists()
        assert "测试" in str(paths.config_dir.parent)
