"""LSP server capabilities definitions.

Provides server server capability configurations for different LSP servers.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

import yaml


def _load_server_capability(
    capabilities_dir: Path,
    filename: str,
) -> dict[str, Any] | None:
    """Load a single server capability from JSON file.

    Args:
        capabilities_dir: Path to capabilities directory
        filename: JSON filename to load

    Returns:
        Parsed capabilities dict, or None if file doesn't exist or is invalid JSON
    """
    file_path = capabilities_dir / filename
    if not file_path.exists():
        return None
    content = file_path.read_text()
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(content)
    return None


def _match_server_filter(
    server_filter: str,
    server_name: str,
    server_file: str,
) -> bool:
    """Check if server_filter matches a server.

    Matching strategy (in priority order):
    1. Exact match: server_filter equals server_file, server_name, or server_file_base
    2. Server name prefix: server_filter starts with server_name (e.g., "basedpyright" in "basedpyright-langserver")
    3. Suffix match with separator: server_filter ends with "-{server_file_base}" to avoid false positives
    4. Substring match: server_name is in server_filter (for custom paths like "custom-pyright" containing "pyright")

    Args:
        server_filter: Filter string to match
        server_name: Server name (e.g., "pyright")
        server_file: Server filename (e.g., "pyright-langserver.json")

    Returns:
        True if server_filter matches the server
    """
    server_file_base = server_file.replace(".json", "")

    # Exact match (highest priority)
    if server_filter in (server_name, server_file, server_file_base):
        return True

    # Server name prefix (e.g., "basedpyright" in "basedpyright-langserver")
    if server_filter.startswith(server_name):
        return True

    # Suffix match with separator (e.g., "custom-pyright" ends with "-pyright")
    if server_filter.endswith(f"-{server_file_base}") or server_filter.endswith(f"-{server_name}"):
        return True

    # Substring match for custom paths (e.g., "custom-pyright" contains "pyright")
    # Use regex to match word boundaries - server_name must be preceded by hyphen or at start
    import re
    pattern = rf"(^|-){re.escape(server_name)}(-|$)"
    return bool(re.search(pattern, server_filter.lower()))


def get_server_capabilities(
    server_filter: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Get LSP server capabilities for all supported servers.

    Args:
        server_filter: Optional server name to filter results
                       (e.g., "pyright-langserver", "rust-analyzer").
                       If provided, returns only that server's capabilities.

    Returns:
        dict: Server name -> capabilities mapping.
              If server_filter provided, contains only that server.
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

    # If server_filter provided, only load that server
    if server_filter:
        for server_name, server_file in servers.items():
            if _match_server_filter(server_filter, server_name, server_file):
                capabilities = _load_server_capability(capabilities_dir, server_file)
                if capabilities is not None:
                    result[server_name] = capabilities
                break
        return result

    # Load all servers
    for server_name, filename in servers.items():
        capabilities = _load_server_capability(capabilities_dir, filename)
        if capabilities is not None:
            result[server_name] = capabilities

    return result


def format_capabilities(
    format: str = "json",
    server_filter: str | None = None,
) -> str:
    """Format server capabilities for display.

    Args:
        format: Output format - "json", "yaml", or "text"
        server_filter: Optional server name to filter before formatting

    Returns:
        Formatted capabilities string

    Raises:
        ValueError: If format is not supported
    """
    capabilities = get_server_capabilities(server_filter)

    # If server_filter was provided but no capabilities found, fall back to all servers
    if server_filter is not None and not capabilities:
        import typer
        typer.echo(
            f"Warning: Capabilities not found for '{server_filter}', showing all servers.",
            err=True,
        )
        capabilities = get_server_capabilities()

    if format == "json":
        return json.dumps(capabilities, indent=2)
    elif format == "yaml":
        return yaml.safe_dump(capabilities, default_flow_style=False, sort_keys=False)
    elif format == "text":
        lines = []
        for server_name, server_caps in capabilities.items():
            # If single server, don't print server name prefix
            if len(capabilities) == 1:
                lines.append(f"Capabilities for {server_name}:")
            else:
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
