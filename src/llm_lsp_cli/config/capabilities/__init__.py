"""LSP server capabilities definitions.

Provides server capability configurations for different LSP servers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def get_server_capabilities() -> dict[str, dict[str, Any]]:
    """Get LSP server capabilities for all supported servers.

    Returns:
        dict: Server name -> capabilities mapping
    """
    capabilities_dir = Path(__file__).parent

    servers = {
        "pyright": "pyright-langserver.json",
        "basedpyright": "basedpyright-langserver.json",
        "typescript": "typescript-language-server.json",
        "rust-analyzer": "rust-analyzer.json",
        "gopls": "gopls.json",
        "jdtls": "jdtls.json",
    }

    result: dict[str, dict[str, Any]] = {}

    for server_name, filename in servers.items():
        file_path = capabilities_dir / filename
        if file_path.exists():
            content = file_path.read_text()
            try:
                result[server_name] = json.loads(content)
            except json.JSONDecodeError:
                # Skip invalid JSON files
                continue

    return result


def format_capabilities(format: str = "json") -> str:
    """Format server capabilities for display.

    Args:
        format: Output format - "json", "yaml", or "text"

    Returns:
        Formatted capabilities string

    Raises:
        ValueError: If format is not supported
    """
    capabilities = get_server_capabilities()

    if format == "json":
        return json.dumps(capabilities, indent=2)
    elif format == "yaml":
        return yaml.safe_dump(capabilities, default_flow_style=False, sort_keys=False)
    elif format == "text":
        lines = []
        for server_name, server_caps in capabilities.items():
            lines.append(f"{server_name}:")
            # Show top-level keys as summary
            for key in sorted(server_caps.keys()):
                value = server_caps[key]
                if isinstance(value, dict):
                    lines.append(f"  {key}:")
                    for subkey in sorted(value.keys())[:5]:  # Limit subkeys
                        lines.append(f"    {subkey}: ...")
                else:
                    lines.append(f"  {key}: {value}")
            lines.append("")
        return "\n".join(lines)
    else:
        raise ValueError(f"Unsupported format: {format}")
