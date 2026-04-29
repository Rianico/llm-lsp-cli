"""Raw formatter for zero-transformation passthrough of LSP responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from llm_lsp_cli.utils import OutputFormat


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

    def format(self, response: dict[str, Any], fmt: OutputFormat) -> str:
        """Format LSP response with zero transformation.

        Args:
            response: Original LSP server response
            fmt: Output format (JSON, YAML, CSV, TEXT)

        Returns:
            Formatted string with structure preserved
        """
        match fmt:
            case OutputFormat.JSON:
                return json.dumps(response, indent=2)
            case OutputFormat.YAML:
                return str(
                    yaml.safe_dump(
                        response, default_flow_style=False, sort_keys=False, allow_unicode=True
                    )
                )
            case OutputFormat.CSV | OutputFormat.TEXT:
                # CSV and TEXT not suitable for raw LSP response structure,
                # so output JSON for consistency
                return json.dumps(response, indent=2)
