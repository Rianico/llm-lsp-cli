"""Default configuration values for llm-lsp-cli."""

from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "languages": {
        "python": {
            "command": "pyright-langserver",
            "args": ["--stdio"],
            "initialize_params_file": "initialize_params_pyright.json",
        },
        "typescript": {"command": "typescript-language-server", "args": ["--stdio"]},
        "javascript": {"command": "typescript-language-server", "args": ["--stdio"]},
        "rust": {"command": "rust-analyzer"},
        "go": {"command": "gopls"},
        "java": {"command": "jdtls"},
        "cpp": {"command": "clangd"},
        "csharp": {"command": "OmniSharp"},
    },
    "trace_lsp": False,
    "timeout_seconds": 30,
}
