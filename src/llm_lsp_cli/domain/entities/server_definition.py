"""ServerDefinition entity for LSP server configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    def from_dict(cls, data: dict[str, Any]) -> ServerDefinition:
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
