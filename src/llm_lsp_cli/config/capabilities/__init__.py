"""LSP server capabilities definitions.

Provides server server capability configurations for different LSP servers.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Module-level cache for capabilities, keyed by server name
_capabilities_cache: dict[str, dict[str, Any]] = {}

# Server name to filename mapping (shared constant)
_SERVERS: dict[str, str] = {
    "pyright": "pyright-langserver.json",
    "basedpyright": "basedpyright-langserver.json",
    "typescript": "typescript-language-server.json",
    "rust-analyzer": "rust-analyzer.json",
    "gopls": "gopls.json",
    "jdtls": "jdtls.json",
}


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
    pattern = rf"(^|-){re.escape(server_name)}(-|$)"
    return bool(re.search(pattern, server_filter.lower()))


def get_capabilities_dir() -> Path:
    """Get the path to the capabilities directory.

    Returns:
        Path to the capabilities directory containing JSON files.
    """
    return Path(__file__).parent


def _extract_server_name_from_path(server_path: str) -> str:
    """Extract the server name (basename) from a server path.

    Args:
        server_path: Full path, relative path, or basename of server executable.

    Returns:
        The basename of the server (e.g., "basedpyright-langserver").
    """
    return Path(server_path).name


def get_capabilities_for_server_path(server_path: str) -> dict[str, Any]:
    """Get capabilities for a specific server path.

    Loads server-specific capabilities JSON file if available,
    otherwise falls back to default.json.

    Args:
        server_path: Path or name of the LSP server executable.

    Returns:
        Dictionary with 'capabilities' and 'initializationOptions' keys.

    Raises:
        FileNotFoundError: If default.json is missing.
        json.JSONDecodeError: If JSON file is invalid.
    """
    capabilities_dir = get_capabilities_dir()
    server_name = _extract_server_name_from_path(server_path)

    # Return cached result if available for this specific server
    if server_name in _capabilities_cache:
        return _capabilities_cache[server_name]

    # Try to match a known server
    capabilities: dict[str, Any] | None = None
    for s_name, server_file in _SERVERS.items():
        if _match_server_filter(server_name, s_name, server_file):
            capabilities = _load_server_capability(capabilities_dir, server_file)
            break

    # Fallback to default.json if no match or load failed
    if capabilities is None:
        logger.warning(
            "No server-specific capabilities found for '%s', falling back to default.json",
            server_name,
        )
        default_path = capabilities_dir / "default.json"
        if not default_path.exists():
            raise FileNotFoundError(
                f"Capabilities file not found for server '{server_name}' "
                "and default.json is missing"
            )
        # Load default.json directly to propagate JSONDecodeError
        content = default_path.read_text()
        loaded = json.loads(content)
        # Type narrow: json.loads returns Any, but we expect dict for valid config
        assert isinstance(loaded, dict)
        capabilities = loaded

    # Cache the result keyed by server name
    _capabilities_cache[server_name] = capabilities
    return capabilities


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

    result: dict[str, dict[str, Any]] = {}

    # If server_filter provided, only load that server
    if server_filter:
        for server_name, server_file in _SERVERS.items():
            if _match_server_filter(server_filter, server_name, server_file):
                capabilities = _load_server_capability(capabilities_dir, server_file)
                if capabilities is not None:
                    result[server_name] = capabilities
                break
        return result

    # Load all servers
    for server_name, filename in _SERVERS.items():
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
