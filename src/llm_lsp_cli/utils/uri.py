"""URI utility functions for path conversion."""

from __future__ import annotations

import contextlib
from pathlib import Path
from urllib.parse import unquote, urlparse

__all__ = ["uri_to_absolute_path"]


def uri_to_absolute_path(uri: str, workspace_root: Path) -> str:
    """Convert a file URI to an absolute path.

    Args:
        uri: File URI (e.g., "file:///workspace/src/module/file.py")
        workspace_root: The root directory of the workspace (used for path resolution)

    Returns:
        Absolute file path (e.g., "/workspace/src/module/file.py"),
        or the original URI if it's not a file URI.
    """
    if not uri:
        return ""

    parsed = urlparse(uri)
    if parsed.scheme != "file":
        # Non-file URI, return as-is
        return uri

    # Decode URL-encoded characters (e.g., %20 -> space)
    decoded_path = unquote(parsed.path)
    file_path = Path(decoded_path)

    # Resolve to absolute path
    with contextlib.suppress(OSError, ValueError):
        file_path = file_path.resolve()

    return str(file_path)
