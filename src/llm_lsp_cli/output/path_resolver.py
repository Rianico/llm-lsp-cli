"""Path resolution utilities for compact output formatting.

This module provides path resolution utilities that delegate to the canonical
uri_to_absolute_path implementation in utils/uri.py for consistent behavior.
"""

from __future__ import annotations

from pathlib import Path

from llm_lsp_cli.utils.uri import uri_to_absolute_path


def normalize_uri_to_absolute(uri: str, workspace_root: Path) -> str:
    """Normalize a file URI to an absolute path.

    Delegates to the canonical uri_to_absolute_path implementation for
    consistent URI parsing and URL decoding behavior.

    Args:
        uri: The file URI (e.g., "file:///project/src/utils.py")
        workspace_root: The workspace root path (passed through to
            uri_to_absolute_path; used for URI resolution but does not
            affect absoluteness of output)

    Returns:
        Absolute file path, or the original URI if not a file:// URI
    """
    return uri_to_absolute_path(uri, workspace_root)


def resolve_path_for_header_absolute(
    file_path: str | Path,
    workspace_path: str | Path,
) -> str:
    """Resolve file path to absolute path for header display.

    Handles both:
    - file:// URIs (from LSP responses) - delegates to uri_to_absolute_path
    - Absolute/relative paths (from CLI file arguments)

    Returns absolute path in all cases.

    Args:
        file_path: The file path or URI to resolve
        workspace_path: The workspace root path (used for URI resolution)

    Returns:
        Absolute file path
    """
    # Defensive: handle empty/None inputs gracefully
    if not file_path:
        return ""

    # Handle file:// URIs via canonical implementation
    if isinstance(file_path, str) and file_path.startswith("file://"):
        return uri_to_absolute_path(file_path, Path(workspace_path))

    # Convert to Path and resolve to absolute
    return str(Path(file_path).resolve())
