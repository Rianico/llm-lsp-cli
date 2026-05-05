# pyright: reportExplicitAny=false
"""LSP initialize parameters builder.

Builds standard LSP initialize parameters dynamically.
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

import os
from pathlib import Path
from typing import Any

from llm_lsp_cli import __version__
from llm_lsp_cli.config.capabilities import get_capabilities_for_server_path


def build_initialize_params(
    server_command: str,
    workspace_path: str,
    _custom_conf_path: str | None = None,
) -> dict[str, Any]:
    """Build LSP initialize parameters dynamically.

    Loads server-specific capabilities from JSON files.

    Args:
        server_command: The server command (used to determine which capabilities to load)
        workspace_path: The workspace directory path
        custom_conf_path: Deprecated, kept for API compatibility

    Returns:
        Dictionary containing initialize parameters for the LSP server.
    """
    workspace_uri = f"file://{Path(workspace_path).resolve()}"

    # Load capabilities from JSON file
    caps_data = get_capabilities_for_server_path(server_command)

    # Build params with dynamic overrides
    result: dict[str, Any] = {
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
    }

    # Copy capabilities from loaded JSON
    if "capabilities" in caps_data:
        result["capabilities"] = caps_data["capabilities"]

    # Include initializationOptions if present
    if "initializationOptions" in caps_data:
        result["initializationOptions"] = caps_data["initializationOptions"]

    return result


# Backward compatibility alias
InitializeParamsLoader = type(
    "InitializeParamsLoader",
    (),
    {"load": staticmethod(build_initialize_params)},
)
