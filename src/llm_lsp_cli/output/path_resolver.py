"""Path resolution utilities for compact output formatting."""

from __future__ import annotations

from pathlib import Path


def normalize_uri_to_relative(uri: str, workspace_root: Path) -> str:
    """Normalize a file URI to a workspace-relative path.

    Args:
        uri: The file URI (e.g., "file:///project/src/utils.py")
        workspace_root: The workspace root path

    Returns:
        Workspace-relative path if inside workspace, absolute path otherwise,
        or the original URI if not a file:// URI
    """
    if not uri:
        return ""

    # Handle non-file URIs
    if not uri.startswith("file://"):
        return uri

    # Parse the file URI
    try:
        file_path = Path(uri[7:])  # Remove "file://" prefix
    except (ValueError, IndexError):
        return uri

    # Resolve workspace root
    workspace_resolved = workspace_root.resolve()

    # Try to make the path relative to workspace
    try:
        relative_path = file_path.resolve().relative_to(workspace_resolved)
        return str(relative_path)
    except ValueError:
        # Path is outside workspace, return absolute path
        return str(file_path.resolve())
