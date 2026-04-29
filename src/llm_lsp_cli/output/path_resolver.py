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


def resolve_path_for_header(
    file_path: str | Path,
    workspace_path: str | Path,
) -> str:
    """Resolve file path to relative for header display.

    Handles both:
    - file:// URIs (from LSP responses)
    - Absolute paths (from CLI file arguments)

    Returns workspace-relative path if inside workspace, else basename.

    Args:
        file_path: The file path or URI to resolve
        workspace_path: The workspace root path

    Returns:
        Workspace-relative path if inside workspace, else basename
    """
    # Defensive: handle empty/None inputs gracefully
    if not file_path:
        return ""

    # Convert to Path, handling file:// URIs
    if isinstance(file_path, str):
        file_path = Path(file_path[7:]) if file_path.startswith("file://") else Path(file_path)

    workspace_resolved = Path(workspace_path).resolve()

    try:
        return str(file_path.resolve().relative_to(workspace_resolved))
    except ValueError:
        # Path is outside workspace, return basename
        return file_path.name
