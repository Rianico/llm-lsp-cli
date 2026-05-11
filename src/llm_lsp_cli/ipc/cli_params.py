"""Daemon RPC parameter models for CLI-to-daemon communication.

These flat camelCase models match the daemon's expected wire format,
distinct from the nested LSP-style IPC models in models.py.

Per ADR-0028, these models:
- Use flat camelCase field aliases (workspacePath, filePath, etc.)
- Serialize via model_dump(mode="json", by_alias=True) to the daemon's expected format
- Support both snake_case construction (Python) and camelCase (JSON)
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class DaemonPositionParams(BaseModel):
    """Position-based params for LSP methods (definition, hover, completion, etc.).

    This is the CLI-to-daemon param format, using flat camelCase fields
    that the daemon's _handle_lsp_method expects.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        extra="ignore",
    )

    workspace_path: str = Field(alias="workspacePath")
    file_path: str = Field(alias="filePath")
    line: int = 0
    column: int = 0


class DaemonFileParams(BaseModel):
    """File-based params for LSP methods (documentSymbol, diagnostic).

    Used when only file context is needed, not position.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        extra="ignore",
    )

    workspace_path: str = Field(alias="workspacePath")
    file_path: str = Field(alias="filePath")


class DaemonWorkspaceParams(BaseModel):
    """Workspace-only params for LSP methods (workspaceDiagnostic).

    Used when only workspace context is needed.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        extra="ignore",
    )

    workspace_path: str = Field(alias="workspacePath")


class DaemonRenameParams(DaemonPositionParams):
    """Rename params with new_name in addition to position."""

    new_name: str = Field(alias="newName")


class DaemonSymbolQueryParams(DaemonWorkspaceParams):
    """Workspace symbol params with query string."""

    query: str
