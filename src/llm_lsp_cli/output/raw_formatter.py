"""Raw formatter for zero-transformation passthrough of LSP responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class RawFormatter:
    """Formatter that outputs LSP responses with zero transformation.

    This formatter provides passthrough semantics: what the LSP server sends
    is what the user receives. No filtering, no path normalization, no field
    omission.

    Used with the --raw CLI flag for debugging or when the original LSP
    response structure is needed.
    """

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the formatter with a workspace root.

        Args:
            workspace: Workspace root path (stored but not used for transformation)
        """
        self._workspace = Path(workspace).resolve()

    @property
    def workspace(self) -> Path:
        """Return the workspace root path."""
        return self._workspace

    def format_json(self, response: dict[str, Any]) -> str:
        """Format LSP response as JSON with zero transformation.

        Args:
            response: Original LSP server response

        Returns:
            JSON string with indent=2, identical to input structure
        """
        return json.dumps(response, indent=2)

    def format_yaml(self, response: dict[str, Any]) -> str:
        """Format LSP response as YAML with zero transformation.

        Args:
            response: Original LSP server response

        Returns:
            YAML string with full structure preserved
        """
        return yaml.safe_dump(
            response, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

    def format_text(self, response: dict[str, Any]) -> str:
        """Format LSP response as text (JSON passthrough).

        LSP has no standard text format, so this outputs JSON for consistency.

        Args:
            response: Original LSP server response

        Returns:
            JSON string (same as format_json)
        """
        return json.dumps(response, indent=2)

    def format_csv(self, response: dict[str, Any]) -> str:
        """Format LSP response as CSV (JSON passthrough).

        CSV is not suitable for raw LSP response structure,
        so this outputs JSON for consistency.

        Args:
            response: Original LSP server response

        Returns:
            JSON string (same as format_json)
        """
        return json.dumps(response, indent=2)
