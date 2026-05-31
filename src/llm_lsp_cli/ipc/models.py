"""Pydantic models for IPC request parameters and results.

This module defines the data models used for IPC communication between
the CLI and daemon. These models provide runtime validation and type safety
for JSON-RPC requests and responses.

The models are organized into:
- Parameter models: Re-exported from llm_lsp_cli.lsp.types (single source of truth)
- Result models: Used as output from IPC methods (IPC-specific, no LSP equivalent)

For LSP-specific types (Location, Hover, DocumentSymbol, etc.), see
llm_lsp_cli.lsp.types which contains the full LSP 3.17 type definitions.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

# =============================================================================
# Re-exported LSP types (single source of truth: lsp/types.py)
# =============================================================================
from llm_lsp_cli.lsp.types import (
    CompletionContext,
    CompletionParams,
    DefinitionParams,
    DocumentSymbolParams,
    HoverParams,
    Position,
    PrepareRenameParams,
    ReferenceContext,
    ReferenceParams,
    RenameParams,
    TextDocumentIdentifier,
    TextDocumentPositionParams,
    WorkspaceSymbolParams,
)

# =============================================================================
# IPC-specific Parameter Models
# =============================================================================


class EmptyParams(BaseModel):
    """Empty parameters for methods that don't require input.

    Used by daemon control methods like ping, shutdown, and status.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


# =============================================================================
# IPC-specific Result Models
# =============================================================================


class PingResult(BaseModel):
    """Result of ping request.

    Includes daemon and language server health status for health checks.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    status: Literal["ok", "healthy", "unhealthy"]
    daemon: bool = True
    lsp_server: bool = True


class ShutdownResult(BaseModel):
    """Result of shutdown request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    status: Literal["ok"]


class DaemonStatusResult(BaseModel):
    """Result of daemon status request.

    Contains information about the daemon process state.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    running: bool
    workspace: str
    language: str
    pid: int | None = None
    uptime_seconds: float | None = None


__all__ = [
    # Re-exported from lsp.types
    "CompletionContext",
    "CompletionParams",
    "DefinitionParams",
    "DocumentSymbolParams",
    "HoverParams",
    "Position",
    "PrepareRenameParams",
    "ReferenceContext",
    "ReferenceParams",
    "RenameParams",
    "TextDocumentIdentifier",
    "TextDocumentPositionParams",
    "WorkspaceSymbolParams",
    # IPC-specific
    "EmptyParams",
    "PingResult",
    "ShutdownResult",
    "DaemonStatusResult",
]
