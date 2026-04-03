"""Configuration management for llm-lsp-cli."""

from .defaults import DEFAULT_CONFIG
from .manager import ConfigManager
from .schema import ClientConfig, LanguageServerConfig

__all__ = [
    "ClientConfig",
    "LanguageServerConfig",
    "ConfigManager",
    "DEFAULT_CONFIG",
]
