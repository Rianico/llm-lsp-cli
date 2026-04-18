"""Configuration management for llm-lsp-cli."""

from .defaults import DEFAULT_CONFIG
from .manager import ConfigManager
from .schema import ClientConfig, LanguageServerConfig
from .types import (
    CapabilityConfig,
    ClientCapabilities,
    InitializeParams,
    LanguageConfig,
    LspMethodConfigDict,
    RuntimePaths,
    ServerConfig,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
)

__all__ = [
    "CapabilityConfig",
    "ClientCapabilities",
    "ClientConfig",
    "ConfigManager",
    "DEFAULT_CONFIG",
    "InitializeParams",
    "LanguageConfig",
    "LanguageServerConfig",
    "LspMethodConfigDict",
    "RuntimePaths",
    "ServerConfig",
    "TextDocumentClientCapabilities",
    "WorkspaceFolder",
]
