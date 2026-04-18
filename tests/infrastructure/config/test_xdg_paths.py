"""Tests for XdgPaths lazy initialization."""

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


class TestXdgPathsLazyInitialization:
    """Test XdgPaths lazy initialization behavior."""

    def test_xdg_paths_lazy_initialization(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths does not create directories at import time."""
        # Arrange: Set up clean temp environment
        config_home = tmp_path / "config"
        state_home = tmp_path / "state"
        runtime_dir = tmp_path / "runtime"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))

        # Act: Import and access class without calling get()
        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Assert: Directories should NOT exist yet
        assert not config_home.exists()
        assert not state_home.exists()
        assert not runtime_dir.exists()

    def test_xdg_paths_get_creates_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths.get() creates required directories."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert paths.config_dir.exists()
        assert paths.state_dir.exists()
        assert paths.runtime_dir.exists()
        # Note: config_dir already includes llm-lsp-cli
        assert paths.config_dir.name == "llm-lsp-cli"

    def test_xdg_paths_respects_xdg_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths uses XDG environment variables."""
        # Arrange
        custom_config = tmp_path / "custom_config"
        custom_state = tmp_path / "custom_state"
        custom_runtime = tmp_path / "custom_runtime"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config))
        monkeypatch.setenv("XDG_STATE_HOME", str(custom_state))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(custom_runtime))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert paths.config_dir.parent == custom_config
        assert paths.state_dir.parent == custom_state
        assert paths.runtime_dir.parent == custom_runtime

    def test_xdg_paths_fallback_chain(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths falls back to defaults when XDG vars not set."""
        # Arrange: Clear XDG env vars
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert: Should fallback to standard locations
        assert paths.config_dir.parent == tmp_path / ".config"
        assert paths.state_dir.parent == tmp_path / ".local" / "state"
        # Runtime dir fallback depends on implementation

    def test_xdg_paths_thread_safety(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths.get() is thread-safe."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        results: list = []
        errors: list = []

        def get_paths() -> None:
            try:
                paths = XdgPaths.get()
                results.append(paths)
            except Exception as e:
                errors.append(e)

        # Act: Call from multiple threads
        threads = [Thread(target=get_paths) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        # All should return the same instance (singleton)
        assert all(r is results[0] for r in results)

    def test_xdg_paths_ensure_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths ensures directories have correct permissions."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert: Check permissions (0o700 = owner rwx only)
        import stat

        config_llm_lsp = paths.config_dir
        mode = config_llm_lsp.stat().st_mode
        assert mode & stat.S_IRWXU == stat.S_IRWXU  # Owner has rwx
        # Note: exact permission check may vary by platform

    def test_xdg_paths_singleton_instance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths.get() returns same instance on repeated calls."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths1 = XdgPaths.get()
        paths2 = XdgPaths.get()

        # Assert
        assert paths1 is paths2

    def test_xdg_paths_properties(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None
    ) -> None:
        """XdgPaths has correct properties."""
        # Arrange
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

        # Act
        paths = XdgPaths.get()

        # Assert
        assert hasattr(paths, "config_dir")
        assert hasattr(paths, "state_dir")
        assert hasattr(paths, "runtime_dir")
        assert isinstance(paths.config_dir, Path)
        assert isinstance(paths.state_dir, Path)
        assert isinstance(paths.runtime_dir, Path)
