"""Tests for ServerDefinition entity."""

import dataclasses

import pytest

from llm_lsp_cli.domain.entities.server_definition import ServerDefinition


@pytest.fixture
def server_def() -> ServerDefinition:
    """Create a default ServerDefinition instance."""
    return ServerDefinition(
        language_id="python",
        command="pyright-langserver",
        args=["--stdio"],
    )


class TestServerDefinitionImmutable:
    """ServerDefinition is frozen (immutable)."""

    def test_server_definition_immutable(self, server_def: ServerDefinition) -> None:
        """ServerDefinition is frozen (immutable)."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            server_def.command = "new-command"  # type: ignore[misc]


class TestServerDefinitionFromDict:
    """ServerDefinition.from_dict constructs valid instance."""

    def test_server_definition_from_dict(self) -> None:
        """ServerDefinition.from_dict constructs valid instance."""
        data = {
            "language_id": "typescript",
            "command": "typescript-language-server",
            "args": ["--stdio"],
            "timeout_seconds": 60,
        }
        server_def = ServerDefinition.from_dict(data)
        assert server_def.language_id == "typescript"
        assert server_def.command == "typescript-language-server"
        assert server_def.timeout_seconds == 60


class TestServerDefinitionDefaultTimeout:
    """ServerDefinition uses 30s default timeout."""

    def test_server_definition_default_timeout(self) -> None:
        """ServerDefinition uses 30s default timeout."""
        data = {
            "language_id": "rust",
            "command": "rust-analyzer",
        }
        server_def = ServerDefinition.from_dict(data)
        assert server_def.timeout_seconds == 30
