from __future__ import annotations

# pyright: reportUnannotatedClassAttribute=false
"""LSP type definitions based on LSP 3.17 specification.

All types are Pydantic BaseModel classes for runtime validation.
CamelCase aliases are used for LSP JSON compatibility.
"""

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Leaf Types (no dependencies on other LSP types)
# =============================================================================


class Position(BaseModel):
    """Position in a text document (0-based)."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    line: int
    character: int


class Range(BaseModel):
    """Range in a text document."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    start: Position
    end: Position


class TextDocumentIdentifier(BaseModel):
    """Identifies a text document."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str


class TextDocumentItem(BaseModel):
    """A text document item."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str
    language_id: str = Field(alias="languageId")
    version: int
    text: str


class VersionedTextDocumentIdentifier(BaseModel):
    """A text document identifier with version."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str
    version: int


class MarkupContent(BaseModel):
    """Markup content for hover, signature help, etc."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    kind: str  # "plaintext" or "markdown"
    value: str


class MarkedString(BaseModel):
    """Marked string for hover."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    language: str | None = None
    value: str | None = None


class TextEdit(BaseModel):
    """A text edit."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    range: Range
    new_text: str = Field(alias="newText")


# =============================================================================
# Composite Types (depend on leaf types)
# =============================================================================


class Location(BaseModel):
    """A location in a text document."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str
    range: Range


class LocationLink(BaseModel):
    """A link between two locations."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    origin_selection_range: Range | None = Field(
        default=None, alias="originSelectionRange"
    )
    target_uri: str = Field(alias="targetUri")
    target_range: Range = Field(alias="targetRange")
    target_selection_range: Range = Field(alias="targetSelectionRange")


class Hover(BaseModel):
    """Hover information."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    contents: MarkupContent | MarkedString | list[MarkedString] | str
    range: Range | None = None


class CompletionContext(BaseModel):
    """Context for completion request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    trigger_kind: int | None = Field(default=None, alias="triggerKind")
    trigger_character: str | None = Field(default=None, alias="triggerCharacter")


class CompletionItem(BaseModel):
    """A completion item."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    label: str
    kind: int | None = None
    detail: str | None = None
    documentation: str | MarkupContent | None = None
    text_edit: TextEdit | None = Field(default=None, alias="textEdit")
    additional_text_edits: list[TextEdit] | None = Field(
        default=None, alias="additionalTextEdits"
    )


class CompletionList(BaseModel):
    """A list of completion items."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    is_incomplete: bool = Field(alias="isIncomplete")
    items: list[CompletionItem]


class SymbolKind(BaseModel):
    """Symbol kind."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    value: int | None = None
    value_set: list[int] | None = Field(default=None, alias="valueSet")


class BaseSymbolInformation(BaseModel):
    """Base symbol information."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    name: str
    kind: int
    tags: list[int] | None = None


class SymbolInformation(BaseSymbolInformation):
    """Symbol information."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    deprecated: bool | None = None
    location: Location | None = None
    container_name: str | None = Field(default=None, alias="containerName")


class DocumentSymbol(BaseModel):
    """Document symbol information."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    name: str
    kind: int
    range: Range
    selection_range: Range = Field(alias="selectionRange")
    detail: str | None = None
    tags: list[int] | None = None
    deprecated: bool | None = None
    children: list["DocumentSymbol"] | None = None


class UnifiedSymbolInformation(BaseModel):
    """Unified symbol information (combines both types)."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    name: str
    kind: int
    range: Range | None = None
    selection_range: Range | None = Field(default=None, alias="selectionRange")
    detail: str | None = None
    tags: list[int] | None = None
    deprecated: bool | None = None
    location: Location | None = None
    container_name: str | None = Field(default=None, alias="containerName")
    children: list["UnifiedSymbolInformation"] | None = None


class WorkspaceSymbolParams(BaseModel):
    """Parameters for workspace/symbol request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    query: str


class HoverParams(BaseModel):
    """Parameters for textDocument/hover request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position


class DefinitionParams(BaseModel):
    """Parameters for textDocument/definition request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position


class ReferenceContext(BaseModel):
    """Context for references request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    include_declaration: bool = Field(alias="includeDeclaration")


class ReferenceParams(BaseModel):
    """Parameters for textDocument/references request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position
    context: ReferenceContext


class CompletionParams(BaseModel):
    """Parameters for textDocument/completion request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position
    context: CompletionContext | None = None


class DocumentSymbolParams(BaseModel):
    """Parameters for textDocument/documentSymbol request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")


class CallHierarchyPrepareParams(BaseModel):
    """Parameters for textDocument/prepareCallHierarchy request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position


class CallHierarchyIncomingCallsParams(BaseModel):
    """Parameters for callHierarchy/incomingCalls request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    item: CallHierarchyItem


class CallHierarchyOutgoingCallsParams(BaseModel):
    """Parameters for callHierarchy/outgoingCalls request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    item: CallHierarchyItem


class WorkspaceDiagnosticParams(BaseModel):
    """Parameters for workspace/diagnostic request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    identifier: str | None = None
    previous_result_ids: list[object] = Field(default_factory=list, alias="previousResultIds")
    partial_result_token: str | None = Field(default=None, alias="partialResultToken")
    work_done_token: str | None = Field(default=None, alias="workDoneToken")


class PrepareRenameParams(BaseModel):
    """Parameters for textDocument/prepareRename request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position


class RenameParams(BaseModel):
    """Parameters for textDocument/rename request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    position: Position
    new_name: str = Field(alias="newName")


class WorkspaceFolder(BaseModel):
    """A workspace folder."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str
    name: str


# =============================================================================
# Complex Types (multiple dependencies)
# =============================================================================


class TextDocumentClientCapabilities(BaseModel):
    """Text document client capabilities."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    synchronization: dict[str, object] | None = None
    completion: dict[str, object] | None = None
    hover: dict[str, object] | None = None
    signature_help: dict[str, object] | None = Field(default=None, alias="signatureHelp")
    definition: dict[str, object] | None = None
    references: dict[str, object] | None = None
    document_highlight: dict[str, object] | None = Field(
        default=None, alias="documentHighlight"
    )
    document_symbol: dict[str, object] | None = Field(
        default=None, alias="documentSymbol"
    )
    code_action: dict[str, object] | None = Field(default=None, alias="codeAction")
    code_lens: dict[str, object] | None = Field(default=None, alias="codeLens")
    document_link: dict[str, object] | None = Field(default=None, alias="documentLink")
    color_provider: dict[str, object] | None = Field(
        default=None, alias="colorProvider"
    )
    formatting: dict[str, object] | None = None
    range_formatting: dict[str, object] | None = Field(
        default=None, alias="rangeFormatting"
    )
    on_type_formatting: dict[str, object] | None = Field(
        default=None, alias="onTypeFormatting"
    )
    rename: dict[str, object] | None = None
    folding_range: dict[str, object] | None = Field(default=None, alias="foldingRange")
    selection_range: dict[str, object] | None = Field(
        default=None, alias="selectionRange"
    )
    publish_diagnostics: dict[str, object] | None = Field(
        default=None, alias="publishDiagnostics"
    )


class ClientCapabilities(BaseModel):
    """Client capabilities."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    workspace: dict[str, object] | None = None
    text_document: TextDocumentClientCapabilities | None = Field(
        default=None, alias="textDocument"
    )
    window: dict[str, object] | None = None
    general: dict[str, object] | None = None
    experimental: object | None = None


class ServerCapabilities(BaseModel):
    """Server capabilities."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    position_encoding: str | None = Field(default=None, alias="positionEncoding")
    text_document_sync: dict[str, object] | int | None = Field(
        default=None, alias="textDocumentSync"
    )
    notebook_document_sync: dict[str, object] | None = Field(
        default=None, alias="notebookDocumentSync"
    )
    completion_provider: dict[str, object] | None = Field(
        default=None, alias="completionProvider"
    )
    hover_provider: bool | dict[str, object] | None = Field(
        default=None, alias="hoverProvider"
    )
    signature_help_provider: dict[str, object] | None = Field(
        default=None, alias="signatureHelpProvider"
    )
    declaration_provider: bool | dict[str, object] | None = Field(
        default=None, alias="declarationProvider"
    )
    definition_provider: bool | dict[str, object] | None = Field(
        default=None, alias="definitionProvider"
    )
    type_definition_provider: bool | dict[str, object] | None = Field(
        default=None, alias="typeDefinitionProvider"
    )
    implementation_provider: bool | dict[str, object] | None = Field(
        default=None, alias="implementationProvider"
    )
    references_provider: bool | dict[str, object] | None = Field(
        default=None, alias="referencesProvider"
    )
    document_highlight_provider: bool | dict[str, object] | None = Field(
        default=None, alias="documentHighlightProvider"
    )
    document_symbol_provider: bool | dict[str, object] | None = Field(
        default=None, alias="documentSymbolProvider"
    )
    code_action_provider: bool | dict[str, object] | None = Field(
        default=None, alias="codeActionProvider"
    )
    code_lens_provider: dict[str, object] | None = Field(
        default=None, alias="codeLensProvider"
    )
    document_link_provider: dict[str, object] | None = Field(
        default=None, alias="documentLinkProvider"
    )
    color_provider: bool | dict[str, object] | None = Field(
        default=None, alias="colorProvider"
    )
    document_formatting_provider: bool | dict[str, object] | None = Field(
        default=None, alias="documentFormattingProvider"
    )
    document_range_formatting_provider: bool | dict[str, object] | None = Field(
        default=None, alias="documentRangeFormattingProvider"
    )
    document_on_type_formatting_provider: dict[str, object] | None = Field(
        default=None, alias="documentOnTypeFormattingProvider"
    )
    rename_provider: bool | dict[str, object] | None = Field(
        default=None, alias="renameProvider"
    )
    folding_range_provider: bool | dict[str, object] | None = Field(
        default=None, alias="foldingRangeProvider"
    )
    execute_command_provider: dict[str, object] | None = Field(
        default=None, alias="executeCommandProvider"
    )
    selection_range_provider: bool | dict[str, object] | None = Field(
        default=None, alias="selectionRangeProvider"
    )
    linked_editing_range_provider: bool | dict[str, object] | None = Field(
        default=None, alias="linkedEditingRangeProvider"
    )
    call_hierarchy_provider: bool | dict[str, object] | None = Field(
        default=None, alias="callHierarchyProvider"
    )
    semantic_tokens_provider: dict[str, object] | None = Field(
        default=None, alias="semanticTokensProvider"
    )
    moniker_provider: bool | dict[str, object] | None = Field(
        default=None, alias="monikerProvider"
    )
    type_hierarchy_provider: bool | dict[str, object] | None = Field(
        default=None, alias="typeHierarchyProvider"
    )
    inline_value_provider: bool | dict[str, object] | None = Field(
        default=None, alias="inlineValueProvider"
    )
    inlay_hint_provider: bool | dict[str, object] | None = Field(
        default=None, alias="inlayHintProvider"
    )
    diagnostic_provider: dict[str, object] | None = Field(
        default=None, alias="diagnosticProvider"
    )
    workspace_symbol_provider: bool | dict[str, object] | None = Field(
        default=None, alias="workspaceSymbolProvider"
    )
    workspace: dict[str, object] | None = None
    experimental: object | None = None


class InitializeParams(BaseModel):
    """Parameters for initialize request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    process_id: int | None = Field(default=None, alias="processId")
    client_info: dict[str, str] | None = Field(default=None, alias="clientInfo")
    locale: str | None = None
    root_path: str | None = Field(default=None, alias="rootPath")
    root_uri: str | None = Field(default=None, alias="rootUri")
    initialization_options: object | None = Field(default=None, alias="initializationOptions")
    capabilities: ClientCapabilities | None = None
    trace: str | None = None
    workspace_folders: list[WorkspaceFolder] | None = Field(
        default=None, alias="workspaceFolders"
    )


class InitializeResult(BaseModel):
    """Result of initialize request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    capabilities: ServerCapabilities
    server_info: dict[str, str] | None = Field(default=None, alias="serverInfo")


class DiagnosticRelatedInformation(BaseModel):
    """Related information for a diagnostic."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    location: Location
    message: str


class Diagnostic(BaseModel):
    """A diagnostic message."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    range: Range
    message: str
    severity: int | None = None
    code: int | str | None = None
    code_description: dict[str, str] | None = Field(default=None, alias="codeDescription")
    source: str | None = None
    tags: list[int] | None = None
    related_information: list[DiagnosticRelatedInformation] | None = Field(
        default=None, alias="relatedInformation"
    )
    data: object | None = None


class PublishDiagnosticsParams(BaseModel):
    """Parameters for textDocument/publishDiagnostics notification."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str
    version: int | None = None
    diagnostics: list[Diagnostic]


class DocumentDiagnosticParams(BaseModel):
    """Parameters for textDocument/diagnostic request."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    text_document: TextDocumentIdentifier = Field(alias="textDocument")
    previous_result_id: str | None = Field(default=None, alias="previousResultId")


class DocumentDiagnosticReport(BaseModel):
    """Diagnostic report for a single document."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    kind: str  # "full" or "unchanged"
    result_id: str | None = Field(default=None, alias="resultId")
    items: list[Diagnostic] | None = None


class WorkspaceDiagnosticItem(BaseModel):
    """A single diagnostic item in workspace report."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    uri: str
    version: int | None = None
    diagnostics: list[Diagnostic]


class WorkspaceDiagnosticReport(BaseModel):
    """Workspace-wide diagnostic report."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    items: list[WorkspaceDiagnosticItem]


# =============================================================================
# Call Hierarchy Types (LSP 3.17)
# =============================================================================


class CallHierarchyItem(BaseModel):
    """Call hierarchy item returned by prepareCallHierarchy.

    Required fields: name, kind, uri, range, selectionRange
    Optional fields: tags, detail, data
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    name: str
    kind: int
    uri: str
    range: Range
    selection_range: Range = Field(alias="selectionRange")
    tags: list[int] | None = None
    detail: str | None = None
    data: object | None = None


class CallHierarchyIncomingCall(BaseModel):
    """Incoming call representation for callHierarchy/incomingCalls.

    Note: Uses 'from_' instead of 'from' to avoid Python keyword conflict.
    The 'from_' field maps to the LSP 'from' field in JSON via alias.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    from_: CallHierarchyItem = Field(alias="from")
    from_ranges: list[Range] = Field(alias="fromRanges")


class CallHierarchyOutgoingCall(BaseModel):
    """Outgoing call representation for callHierarchy/outgoingCalls."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )

    to: CallHierarchyItem
    from_ranges: list[Range] = Field(alias="fromRanges")
