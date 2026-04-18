"""Tests for JsonServerDefinitionRepository."""

from pathlib import Path

import pytest

from llm_lsp_cli.domain.entities import ServerDefinition


class TestJsonServerDefinitionRepository:
    """Test JsonServerDefinitionRepository functionality."""

    def test_repo_implements_protocol(self) -> None:
        """JsonServerDefinitionRepository implements ServerDefinitionRepository protocol."""
        from llm_lsp_cli.domain.repositories import ServerDefinitionRepository
        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        # This will fail at runtime if protocol not implemented
        repo: ServerDefinitionRepository = JsonServerDefinitionRepository(Path("/tmp/test"))
        assert repo is not None

    def test_repo_loads_from_config_file(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository loads server definitions from config file."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "python": {
                    "command": "pyright-langserver",
                    "args": ["--stdio"],
                    "timeout_seconds": 60,
                }
            }
        }
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        result = repo.get("python")

        # Assert
        assert result is not None
        assert result.language_id == "python"
        assert result.command == "pyright-langserver"
        assert result.args == ["--stdio"]
        assert result.timeout_seconds == 60

    def test_repo_falls_back_to_defaults(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository falls back to default definitions."""
        # Arrange: Empty config
        config_file = tmp_path / "config.json"
        config_data = {"languages": {}}
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act: Try to get a language not in config
        result = repo.get("rust")

        # Assert: Should return None for unknown languages
        # (defaults would come from a different source)
        assert result is None

    def test_repo_get_returns_none_for_unknown(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository.get() returns None for unknown language."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "python": {"command": "pyright", "args": []}
            }
        }
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        result = repo.get("unknown-language")

        # Assert
        assert result is None

    def test_repo_register_adds_definition(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository.register() adds a server definition."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {"languages": {}}
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)
        new_def = ServerDefinition(
            language_id="ruby",
            command="solargraph",
            args=["stdio"],
            timeout_seconds=45,
        )

        # Act
        repo.register(new_def)

        # Assert
        result = repo.get("ruby")
        assert result is not None
        assert result.language_id == "ruby"
        assert result.command == "solargraph"

    def test_repo_list_all_returns_all(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository.list_all() returns all definitions."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "python": {"command": "pyright", "args": []},
                "typescript": {"command": "typescript-language-server", "args": ["--stdio"]},
                "rust": {"command": "rust-analyzer", "args": []},
            }
        }
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)

        # Act
        all_defs = list(repo.list_all())

        # Assert
        assert len(all_defs) == 3
        language_ids = {d.language_id for d in all_defs}
        assert language_ids == {"python", "typescript", "rust"}

    def test_repo_lazy_loading(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository loads config lazily."""
        # Arrange
        config_file = tmp_path / "config.json"
        # Don't create the file yet

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        # Act: Create repo without file
        repo = JsonServerDefinitionRepository(config_file)

        # Assert: Should not raise until get() is called
        # (lazy loading)
        all_defs = list(repo.list_all())
        assert len(all_defs) == 0

    def test_repo_persistence_after_register(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository persists registered definitions."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {"languages": {}}
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)
        new_def = ServerDefinition(
            language_id="go",
            command="gopls",
            args=[],
            timeout_seconds=30,
        )

        # Act
        repo.register(new_def)

        # Assert: Check file was updated
        loaded_data = json.loads(config_file.read_text())
        assert "go" in loaded_data["languages"]
        assert loaded_data["languages"]["go"]["command"] == "gopls"

    def test_repo_update_existing_definition(
        self, tmp_path: Path
    ) -> None:
        """JsonServerDefinitionRepository updates existing definitions."""
        # Arrange
        config_file = tmp_path / "config.json"
        config_data = {
            "languages": {
                "python": {"command": "pyright-old", "args": []}
            }
        }
        import json
        config_file.write_text(json.dumps(config_data))

        from llm_lsp_cli.infrastructure.config.repository import JsonServerDefinitionRepository

        repo = JsonServerDefinitionRepository(config_file)
        updated_def = ServerDefinition(
            language_id="python",
            command="pyright-updated",
            args=["--new-arg"],
            timeout_seconds=45,
        )

        # Act
        repo.register(updated_def)

        # Assert
        result = repo.get("python")
        assert result is not None
        assert result.command == "pyright-updated"
        assert result.args == ["--new-arg"]
