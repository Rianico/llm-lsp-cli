"""URI utility functions for path conversion."""

from __future__ import annotations

import contextlib
from pathlib import Path
from urllib.parse import unquote, urlparse

__all__ = ["uri_to_relative_path"]


def uri_to_relative_path(uri: str, workspace_root: Path) -> str:
    """Convert a file URI to a project-relative path.

    Args:
        uri: File URI (e.g., "file:///workspace/src/module/file.py")
        workspace_root: The root directory of the workspace for relative path resolution

    Returns:
        Relative path within workspace (e.g., "src/module/file.py"),
        or absolute path if file is outside workspace (fallback),
        or the original URI if it's not a file URI.
    """
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        # Non-file URI, return as-is
        return uri

    # Decode URL-encoded characters (e.g., %20 -> space)
    decoded_path = unquote(parsed.path)
    file_path = Path(decoded_path)

    # Handle Windows paths (if applicable)
    if file_path.exists():
        file_path = file_path.resolve()
    else:
        # For non-existent files, try to resolve anyway
        with contextlib.suppress(OSError, ValueError):
            file_path = file_path.resolve()

    # Try to make relative to workspace root
    try:
        relative = file_path.relative_to(workspace_root)
        return str(relative)
    except ValueError:
        # File is outside workspace, return absolute path as fallback
        return str(file_path)
