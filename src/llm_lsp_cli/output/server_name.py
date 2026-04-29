"""Server name resolution with fallback chain.

This module provides the get_server_display_name function that determines
the display name of an LSP server using a priority-based fallback chain.

Priority:
1. serverInfo.name from LSP initialize response (capitalized)
2. Command basename matched against known mapping
3. Language-to-server mapping (when language provided)
4. Command basename with first letter capitalized (fallback)
"""

from __future__ import annotations

from pathlib import Path

# Known server basename to display name mappings
_SERVER_NAME_MAP: dict[str, str] = {
    "pyright-langserver": "Pyright",
    "pyright": "Pyright",
    "basedpyright-langserver": "Basedpyright",
    "basedpyright": "Basedpyright",
    "typescript-language-server": "TypeScript",
    "tsserver": "TypeScript",
    "rust-analyzer": "Rust Analyzer",
    "gopls": "Go",
    "golangci-lint-langserver": "Golangci-lint",
    "clangd": "Clangd",
    "lua-language-server": "Lua",
    "lua-lsp": "Lua",
    "sumneko-lua-language-server": "Lua",
}

# Language to server display name mapping (fallback when no command_path)
_LANGUAGE_TO_SERVER: dict[str, str] = {
    "python": "Basedpyright",
    "typescript": "TypeScript",
    "typescriptreact": "TypeScript",
    "javascript": "TypeScript",
    "javascriptreact": "TypeScript",
    "rust": "Rust Analyzer",
    "go": "Go",
}


def _capitalize_first(s: str) -> str:
    """Capitalize only the first letter, preserving the rest."""
    if not s:
        return s
    return s[0].upper() + s[1:]


def get_server_display_name(
    server_info_name: str | None,
    command_path: str,
    language: str | None = None,
) -> str:
    """Get the display name for an LSP server.

    Uses a priority fallback chain:
    1. serverInfo.name (capitalized)
    2. Command basename matched against known mapping
    3. Language-to-server mapping (when language provided)
    4. Command basename with first letter capitalized

    Args:
        server_info_name: The serverInfo.name from LSP initialize response
        command_path: The command path used to start the LSP server
        language: The language for fallback server name lookup

    Returns:
        The display name for the server
    """
    # Priority 1: Use serverInfo.name if provided and non-empty
    if server_info_name:
        return _capitalize_first(server_info_name)

    # Priority 2: Use command basename if provided
    if command_path:
        basename = Path(command_path).name
        # Check known mappings
        if basename in _SERVER_NAME_MAP:
            return _SERVER_NAME_MAP[basename]
        # Capitalize first letter of basename
        return _capitalize_first(basename)

    # Priority 3: Use language-to-server mapping
    if language and language in _LANGUAGE_TO_SERVER:
        return _LANGUAGE_TO_SERVER[language]

    # Fallback: return empty string
    return ""
