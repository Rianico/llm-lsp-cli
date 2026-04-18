"""ServerDefinitionRepository protocol for server definition storage."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from llm_lsp_cli.domain.entities.server_definition import ServerDefinition


class ServerDefinitionRepository(Protocol):
    """Protocol for server definition repositories.

    Defines the interface for storing and retrieving LSP server
    definitions. Implementations may use JSON files, databases,
    or in-memory storage.
    """

    def get(self, language_id: str) -> ServerDefinition | None:
        """Retrieve a server definition by language ID.

        Args:
            language_id: Language identifier (e.g., 'python').

        Returns:
            ServerDefinition if found, None otherwise.
        """
        ...

    def list_all(self) -> Iterable[ServerDefinition]:
        """List all registered server definitions.

        Returns:
            Iterable of all ServerDefinition instances.
        """
        ...

    def register(self, definition: ServerDefinition) -> None:
        """Register a new server definition.

        Args:
            definition: ServerDefinition to register.
        """
        ...
