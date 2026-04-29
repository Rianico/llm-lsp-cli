"""TypedDict configurations for type-safe dictionary structures."""

from __future__ import annotations

from typing import Any, TypedDict

from llm_lsp_cli.lsp.types import (
    ClientCapabilities,
    TextDocumentClientCapabilities,
)

# Re-export types from lsp.types for backward compatibility
__all__ = [
    "ClientCapabilities",
    "TextDocumentClientCapabilities",
    "ServerConfig",
    "InitializeParams",
    "WorkspaceFolder",
    "CapabilityConfig",
    "LspMethodConfigDict",
    "LanguageConfig",
    "RuntimePaths",
]


class ServerConfig(TypedDict, total=False):
    """Server configuration TypedDict.

    Attributes:
        language_id: The language identifier (e.g., 'python', 'typescript').
        command: The server command to execute.
        args: Optional list of command-line arguments.
        enabled: Whether the server is enabled (default True).
    """

    language_id: str
    command: str
    args: list[str]
    enabled: bool


class InitializeParams(TypedDict, total=False):
    """LSP initialize parameters TypedDict.

    Matches the LSP 3.17 specification for initialize request parameters.

    Attributes:
        processId: The process ID of the client.
        clientInfo: Client information (name, version).
        locale: The client locale.
        rootPath: The root path (deprecated, use rootUri).
        rootUri: The root URI.
        initializationOptions: Initialization options.
        capabilities: Client capabilities.
        trace: Trace level ('off', 'messages', 'verbose').
        workspaceFolders: Workspace folders.
    """

    processId: int | None
    clientInfo: dict[str, str]
    locale: str
    rootPath: str | None
    rootUri: str | None
    initializationOptions: Any
    capabilities: ClientCapabilities
    trace: str
    workspaceFolders: list[WorkspaceFolder] | None


class WorkspaceFolder(TypedDict):
    """Workspace folder TypedDict."""

    uri: str
    name: str


# ClientCapabilities and TextDocumentClientCapabilities are imported from lsp.types


class CapabilityConfig(TypedDict, total=False):
    """Capability configuration TypedDict.

    Attributes:
        textDocumentSync: Text document synchronization settings.
        definitionProvider: Whether definition provider is enabled.
        referencesProvider: Whether references provider is enabled.
        completionProvider: Completion provider settings.
        hoverProvider: Whether hover provider is enabled.
        documentSymbolProvider: Whether document symbol provider is enabled.
        workspaceSymbolProvider: Whether workspace symbol provider is enabled.
    """

    textDocumentSync: dict[str, Any] | int
    definitionProvider: bool
    referencesProvider: bool
    completionProvider: dict[str, Any]
    hoverProvider: bool | dict[str, Any]
    documentSymbolProvider: bool
    workspaceSymbolProvider: bool | dict[str, Any]


class LspMethodConfigDict(TypedDict):
    """LSP method configuration TypedDict.

    Attributes:
        registry_method: The registry method name.
        required_params: List of required parameter names.
        param_mapping: Mapping from LSP params to registry params.
    """

    registry_method: str
    required_params: list[str]
    param_mapping: dict[str, str]


class LanguageConfig(TypedDict, total=False):
    """Language configuration TypedDict.

    Attributes:
        command: The server command for this language.
        args: Optional command-line arguments.
        file_patterns: File patterns for language detection.
        priority: Priority for language detection (lower = higher priority).
    """

    command: str
    args: list[str]
    file_patterns: list[str]
    priority: int


class RuntimePaths(TypedDict):
    """Runtime paths TypedDict.

    Attributes:
        socket_path: Path to the UNIX socket file.
        pid_file: Path to the PID lock file.
        log_file: Path to the log file.
        daemon_log_file: Path to the daemon log file.
    """

    socket_path: str
    pid_file: str
    log_file: str
    daemon_log_file: str
