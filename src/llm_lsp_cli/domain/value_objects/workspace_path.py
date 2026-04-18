"""WorkspacePath value object for safe path operations within a workspace boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from llm_lsp_cli.domain.exceptions import PathValidationError


@dataclass(frozen=True)
class WorkspacePath:
    """Value object representing a validated workspace root path.

    Ensures all path operations remain within the workspace boundary,
    preventing path traversal attacks and symlink-based escapes.

    Attributes:
        path: The absolute, resolved workspace root path.
    """

    path: Path

    def __init__(self, workspace: Path) -> None:
        """Initialize WorkspacePath with validation.

        Args:
            workspace: Path to the workspace root.

        Raises:
            PathValidationError: If the workspace path does not exist.
        """
        if not workspace.exists():
            raise PathValidationError(f"Workspace path does not exist: {workspace}")

        resolved = workspace.resolve()
        object.__setattr__(self, "path", resolved)

    def resolve_child(self, relative_path: str) -> Path:
        """Resolve a child path within the workspace boundary.

        Args:
            relative_path: Relative path from workspace root.

        Returns:
            Absolute resolved path of the child.

        Raises:
            PathValidationError: If the resolved path escapes the workspace boundary.
        """
        child = self.path / relative_path
        resolved_child = child.resolve()

        try:
            resolved_child.relative_to(self.path)
        except ValueError as err:
            raise PathValidationError(
                f"Path escapes workspace boundary: {relative_path}"
            ) from err

        return resolved_child
