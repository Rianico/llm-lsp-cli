"""ServerDefinition entity for LSP server configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class _ServerDefinitionDictRequired(TypedDict):
    """Required fields for ServerDefinitionDict."""

    language_id: str
    command: str


class ServerDefinitionDict(_ServerDefinitionDictRequired, total=False):
    """Dictionary representation of ServerDefinition."""

    args: list[str]
    timeout_seconds: int


@dataclass(frozen=True)
class ServerDefinition:
    """Entity representing an LSP server definition.

    Immutable dataclass that defines how to start and configure
    a language server for a specific language.

    Attributes:
        language_id: Language identifier (e.g., 'python', 'typescript').
        command: Server executable command.
        args: Command-line arguments for the server.
        timeout_seconds: Connection timeout in seconds.
    """

    language_id: str
    command: str
    args: list[str] = field(default_factory=list)
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: ServerDefinitionDict) -> ServerDefinition:
        """Construct a ServerDefinition from a dictionary.

        Args:
            data: Dictionary with server configuration.

        Returns:
            ServerDefinition instance.
        """
        return cls(
            language_id=data["language_id"],
            command=data["command"],
            args=data.get("args", []),
            timeout_seconds=data.get("timeout_seconds", 30),
        )
