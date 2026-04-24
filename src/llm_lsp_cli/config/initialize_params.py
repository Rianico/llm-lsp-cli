"""LSP initialize parameters builder.

Builds standard LSP initialize parameters dynamically.
"""

import os
from pathlib import Path
from typing import Any

from llm_lsp_cli import __version__


def build_initialize_params(
    _server_command: str,
    workspace_path: str,
    _custom_conf_path: str | None = None,
) -> dict[str, Any]:
    """Build LSP initialize parameters dynamically.

    Args:
        server_command: The server command (used for logging, not for loading config)
        workspace_path: The workspace directory path
        custom_conf_path: Deprecated, kept for API compatibility

    Returns:
        Dictionary containing initialize parameters for the LSP server.
    """
    workspace_uri = f"file://{Path(workspace_path).resolve()}"

    return {
        "processId": os.getpid(),
        "clientInfo": {
            "name": "llm-lsp-cli",
            "version": __version__,
        },
        "rootUri": workspace_uri,
        "workspaceFolders": [
            {
                "uri": workspace_uri,
                "name": Path(workspace_path).name,
            }
        ],
        "capabilities": _get_standard_capabilities(),
    }


def _get_standard_capabilities() -> dict[str, Any]:
    """Return standard LSP client capabilities.

    These capabilities are standardized across all supported LSP servers:
    - workspaceFolders: True (required for multi-root workspace support)
    - configuration: True (required for server to request settings)
    - diagnostics with refreshSupport: True
    - workDoneProgress: True (for progress notifications)
    - textDocument.diagnostic with dynamicRegistration: True
    - publishDiagnostics with full support
    """
    return {
        "workspace": {
            "workspaceFolders": True,
            "configuration": True,
            "diagnostics": {"refreshSupport": True},
            "workDoneProgress": True,
        },
        "window": {
            "workDoneProgress": True,
        },
        "textDocument": {
            "diagnostic": {"dynamicRegistration": True},
            "publishDiagnostics": {
                "relatedInformation": True,
                "versionSupport": False,
                "tagSupport": {"valueSet": [1, 2]},
                "codeDescriptionSupport": True,
                "dataSupport": True,
            },
            "documentSymbol": {
                "hierarchicalDocumentSymbolSupport": True,
            },
        },
    }


# Backward compatibility alias
InitializeParamsLoader = type(
    "InitializeParamsLoader",
    (),
    {"load": staticmethod(build_initialize_params)},
)
