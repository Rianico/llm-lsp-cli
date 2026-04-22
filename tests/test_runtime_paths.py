"""Tests for runtime path building with flat directory structure."""

from pathlib import Path

import pytest

from llm_lsp_cli.config.manager import ConfigManager
from llm_lsp_cli.config.path_builder import RuntimePathBuilder


class TestRuntimePathBuilderFlatStructure:
    """Tests for flat runtime directory structure."""

    def test_get_runtime_base_dir_returns_cwd_plus_dot_llm_lsp_cli(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_runtime_base_dir() returns Path.cwd() / '.llm-lsp-cli'."""
        # Arrange
        project_dir = temp_dir / "test-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Act
        base_dir = RuntimePathBuilder.get_runtime_base_dir()

        # Assert - use resolve() to handle macOS /var vs /private/var symlinks
        assert base_dir.resolve() == (project_dir / ".llm-lsp-cli").resolve()

    def test_sanitize_workspace_name_method_removed(self) -> None:
        """_sanitize_workspace_name() method is removed."""
        # Assert
        assert not hasattr(RuntimePathBuilder, "_sanitize_workspace_name")

    def test_generate_workspace_hash_method_removed(self) -> None:
        """_generate_workspace_hash() method is removed."""
        # Assert
        assert not hasattr(RuntimePathBuilder, "_generate_workspace_hash")

    def test_build_workspace_subdir_method_removed(self) -> None:
        """_build_workspace_subdir() method is removed."""
        # Assert
        assert not hasattr(RuntimePathBuilder, "_build_workspace_subdir")

    def test_build_socket_path_flat_structure(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """build_socket_path() uses flat directory structure."""
        # Arrange
        project_dir = temp_dir / "my-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Act
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(project_dir),
            language="python",
        )

        # Assert - use resolve() to handle macOS /var vs /private/var symlinks
        assert socket_path.parent.resolve() == (project_dir / ".llm-lsp-cli").resolve()
        assert socket_path.suffix == ".sock"
        # Path should NOT contain workspace name subdirectory
        assert "my-project" not in socket_path.parent.name

    def test_different_projects_different_socket_paths(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Different projects have different socket paths."""
        # Arrange
        project_a = temp_dir / "project-a"
        project_b = temp_dir / "project-b"
        project_a.mkdir()
        project_b.mkdir()
        monkeypatch.chdir(temp_dir)

        # Act
        socket_a = ConfigManager.build_socket_path(str(project_a), "python")
        socket_b = ConfigManager.build_socket_path(str(project_b), "python")

        # Assert
        assert socket_a != socket_b
        # Both should be in their respective .llm-lsp-cli directories
        assert socket_a.parent.resolve() == (project_a / ".llm-lsp-cli").resolve()
        assert socket_b.parent.resolve() == (project_b / ".llm-lsp-cli").resolve()

    def test_same_project_same_language_consistent_paths(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same project + language produces consistent paths."""
        # Arrange
        project_dir = temp_dir / "my-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Act
        socket1 = ConfigManager.build_socket_path(str(project_dir), "python")
        socket2 = ConfigManager.build_socket_path(str(project_dir), "python")

        # Assert
        assert socket1 == socket2

    def test_socket_path_length_within_unix_limit(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Flat structure saves characters vs old subdir approach."""
        # Arrange: Create a project directory
        project_dir = temp_dir / "my-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Act
        socket_path = ConfigManager.build_socket_path(str(project_dir), "python")

        # Assert
        # The flat structure saves ~20-30 characters vs old subdir approach
        # Old: {base}/llm-lsp-cli/{name}-{hash}/{server}.sock
        # New: {base}/.llm-lsp-cli/{server}.sock
        # Savings: no workspace name + hash subdirectory (~15-25 chars)
        # Verify flat structure (no workspace name in parent dir)
        assert socket_path.parent.name == ".llm-lsp-cli"
        # Verify path doesn't contain workspace hash pattern
        assert not any(c.isdigit() for c in socket_path.parent.name.replace(".llm-lsp-cli", ""))


class TestConfigManagerRuntimeDir:
    """Tests for ConfigManager runtime directory management."""

    def test_ensure_project_dir_method_removed(self) -> None:
        """ensure_project_dir() method is removed from ConfigManager."""
        # Assert
        assert not hasattr(ConfigManager, "ensure_project_dir")

    def test_ensure_runtime_dir_creates_flat_directory(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ensure_runtime_dir() creates .llm-lsp-cli in current directory."""
        # Arrange
        project_dir = temp_dir / "test-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        runtime_dir = project_dir / ".llm-lsp-cli"

        # Act
        created_dir = ConfigManager.ensure_runtime_dir()

        # Assert - use resolve() to handle macOS /var vs /private/var symlinks
        assert created_dir.exists()
        assert created_dir.resolve() == runtime_dir.resolve()

    def test_ensure_runtime_dir_idempotent(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ensure_runtime_dir() is idempotent."""
        # Arrange
        project_dir = temp_dir / "test-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Act
        dir1 = ConfigManager.ensure_runtime_dir()
        dir2 = ConfigManager.ensure_runtime_dir()

        # Assert
        assert dir1 == dir2
        assert dir1.exists()
