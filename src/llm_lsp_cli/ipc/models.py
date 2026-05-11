"""Pydantic models for IPC request parameters and results.

This module defines the data models used for IPC communication between
the CLI and daemon. These models provide runtime validation and type safety
for JSON-RPC requests and responses.

The models are organized into:
- Parameter models: Used as input to IPC methods
- Result models: Used as output from IPC methods

For LSP-specific types (Location, Hover, DocumentSymbol, etc.), see
llm_lsp_cli.lsp.types which contains the full LSP 3.17 type definitions.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Parameter Models
# =============================================================================


class EmptyParams(BaseModel):
    """Empty parameters for methods that don't require input.

    Used by daemon control methods like ping, shutdown, and status.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


class Position(BaseModel):
    """Position in a text document (0-based line and character).

    This is an IPC-specific Position model. For LSP Position, see
    llm_lsp_cli.lsp.types.Position which uses camelCase aliases.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    line: int
    character: int

    @field_validator("line", "character")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Ensure line and character are non-negative."""
        if v < 0:
            raise ValueError("Position values must be non-negative")
        return v


class TextDocumentIdentifier(BaseModel):
    """Identifies a text document by URI.

    This is an IPC-specific identifier. For LSP TextDocumentIdentifier,
    see llm_lsp_cli.lsp.types which uses camelCase aliases.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    uri: str


class TextDocumentPositionParams(BaseModel):
    """Base parameters for methods that operate on a position in a document.

    Used by definition, hover, prepareRename, etc.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position


class WorkspaceSymbolParams(BaseModel):
    """Parameters for workspace/symbol request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    query: str


class RenameParams(BaseModel):
    """Parameters for textDocument/rename request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position
    new_name: str = Field(alias="newName")


class DefinitionParams(TextDocumentPositionParams):
    """Parameters for textDocument/definition request.

    Inherits from TextDocumentPositionParams.
    """

    pass


class HoverParams(TextDocumentPositionParams):
    """Parameters for textDocument/hover request.

    Inherits from TextDocumentPositionParams.
    """

    pass


class DocumentSymbolParams(BaseModel):
    """Parameters for textDocument/documentSymbol request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")


class CompletionContext(BaseModel):
    """Context for completion request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    trigger_kind: int | None = Field(default=None, alias="triggerKind")
    trigger_character: str | None = Field(default=None, alias="triggerCharacter")


class CompletionParams(BaseModel):
    """Parameters for textDocument/completion request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position
    context: CompletionContext | None = None


class ReferenceContext(BaseModel):
    """Context for references request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    include_declaration: bool = Field(alias="includeDeclaration")


class ReferenceParams(BaseModel):
    """Parameters for textDocument/references request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position
    context: ReferenceContext


class PrepareRenameParams(TextDocumentPositionParams):
    """Parameters for textDocument/prepareRename request.

    Inherits from TextDocumentPositionParams.
    """

    pass


# =============================================================================
# Result Models
# =============================================================================


class PingResult(BaseModel):
    """Result of ping request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    status: Literal["ok"]


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
