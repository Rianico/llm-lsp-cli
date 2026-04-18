"""Path validation service for preventing path traversal attacks."""

from __future__ import annotations

from pathlib import Path

from ..exceptions import PathValidationError


class PathValidator:
    """Validates paths to prevent CWE-22 path traversal attacks.

    This service ensures that all paths remain within workspace boundaries
    and handles symlink-based escape attempts.

    Design: Pure functions with no side effects (immutability).
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize the validator with a workspace root boundary.

        Args:
            workspace_root: The root directory that serves as the boundary.

        Raises:
            PathValidationError: If the workspace root does not exist.
        """
        self._workspace_root = workspace_root.resolve()

        if not self._workspace_root.exists():
            raise PathValidationError(
                f"Workspace root does not exist: {self._workspace_root}"
            )

    def validate_within_boundary(self, path: str | Path) -> Path:
        """Validate that a path is within the workspace boundary.

        Args:
            path: The path to validate (can be relative or absolute).

        Returns:
            The resolved Path object if validation succeeds.

        Raises:
            PathValidationError: If the path is outside the boundary,
                contains null bytes, or attempts traversal.
        """
        # Check for null bytes first
        path_str = str(path)
        if "\x00" in path_str:
            raise PathValidationError(
                f"Path contains null byte: {repr(path_str)}"
            )

        # Convert to Path if string
        path_obj = Path(path) if isinstance(path, str) else path

        # Handle absolute paths
        if path_obj.is_absolute():
            resolved = path_obj.resolve()
        else:
            # Resolve relative to workspace root
            resolved = (self._workspace_root / path_obj).resolve()

        # Verify the resolved path is within the workspace boundary
        try:
            resolved.relative_to(self._workspace_root)
        except ValueError as err:
            raise PathValidationError(
                f"Path is outside workspace boundary: {path_str}"
            ) from err

        return resolved
