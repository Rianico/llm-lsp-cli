"""LSP type definitions based on LSP 3.17 specification."""

from typing import Any, TypedDict


class Position(TypedDict):
    """Position in a text document."""

    line: int
    character: int


class Range(TypedDict):
    """Range in a text document."""

    start: Position
    end: Position


class TextDocumentIdentifier(TypedDict):
    """Identifies a text document."""

    uri: str


class TextDocumentItem(TypedDict):
    """A text document item."""

    uri: str
    languageId: str
    version: int
    text: str


class VersionedTextDocumentIdentifier(TypedDict):
    """A text document identifier with version."""

    uri: str
    version: int


class Location(TypedDict):
    """A location in a text document."""

    uri: str
    range: Range


class LocationLink(TypedDict, total=False):
    """A link between two locations."""

    originSelectionRange: Range
    targetUri: str
    targetRange: Range
    targetSelectionRange: Range


class MarkupContent(TypedDict):
    """Markup content for hover, signature help, etc."""

    kind: str  # "plaintext" or "markdown"
    value: str


class MarkedString(TypedDict, total=False):
    """Marked string for hover."""

    language: str
    value: str


class Hover(TypedDict):
    """Hover information."""

    contents: MarkupContent | MarkedString | list[MarkedString]
    range: Range | None


class CompletionContext(TypedDict, total=False):
    """Context for completion request."""

    triggerKind: int  # CompletionTriggerKind
    triggerCharacter: str


class CompletionItem(TypedDict, total=False):
    """A completion item."""

    label: str
    kind: int  # CompletionItemKind
    detail: str
    documentation: str | MarkupContent
    textEdit: "TextEdit"
    additionalTextEdits: list["TextEdit"]


class CompletionList(TypedDict):
    """A list of completion items."""

    isIncomplete: bool
    items: list[CompletionItem]


class TextEdit(TypedDict):
    """A text edit."""

    range: Range
    newText: str


class SymbolKind(TypedDict, total=False):
    """Symbol kind."""

    value: int
    valueSet: list[int]


class BaseSymbolInformation(TypedDict):
    """Base symbol information."""

    name: str
    kind: int
    tags: list[int] | None


class SymbolInformation(BaseSymbolInformation, total=False):
    """Symbol information."""

    deprecated: bool
    location: Location
    containerName: str


class DocumentSymbol(TypedDict, total=False):
    """Document symbol information."""

    name: str
    detail: str
    kind: int
    tags: list[int]
    deprecated: bool
    range: Range
    selectionRange: Range
    children: list["DocumentSymbol"]


class UnifiedSymbolInformation(TypedDict, total=False):
    """Unified symbol information (combines both types)."""

    name: str
    detail: str
    kind: int
    tags: list[int]
    deprecated: bool
    range: Range
    selectionRange: Range
    location: Location
    containerName: str
    children: list["UnifiedSymbolInformation"]


class WorkspaceSymbolParams(TypedDict):
    """Parameters for workspace/symbol request."""

    query: str


class InitializeParams(TypedDict, total=False):
    """Parameters for initialize request."""

    processId: int | None
    clientInfo: dict[str, Any]
    locale: str
    rootPath: str | None
    rootUri: str | None
    initializationOptions: Any
    capabilities: "ClientCapabilities"
    trace: str  # "off" | "messages" | "verbose"
    workspaceFolders: list["WorkspaceFolder"] | None


class WorkspaceFolder(TypedDict):
    """A workspace folder."""

    uri: str
    name: str


class ClientCapabilities(TypedDict, total=False):
    """Client capabilities."""

    workspace: dict[str, Any]
    textDocument: "TextDocumentClientCapabilities"
    window: dict[str, Any]
    general: dict[str, Any]
    experimental: Any


class TextDocumentClientCapabilities(TypedDict, total=False):
    """Text document client capabilities."""

    synchronization: dict[str, Any]
    completion: dict[str, Any]
    hover: dict[str, Any]
    signatureHelp: dict[str, Any]
    definition: dict[str, Any]
    references: dict[str, Any]
    documentHighlight: dict[str, Any]
    documentSymbol: dict[str, Any]
    codeAction: dict[str, Any]
    codeLens: dict[str, Any]
    documentLink: dict[str, Any]
    colorProvider: dict[str, Any]
    formatting: dict[str, Any]
    rangeFormatting: dict[str, Any]
    onTypeFormatting: dict[str, Any]
    rename: dict[str, Any]
    foldingRange: dict[str, Any]
    selectionRange: dict[str, Any]
    publishDiagnostics: dict[str, Any]


class ServerCapabilities(TypedDict, total=False):
    """Server capabilities."""

    positionEncoding: str
    textDocumentSync: dict[str, Any] | int
    notebookDocumentSync: dict[str, Any]
    completionProvider: dict[str, Any]
    hoverProvider: bool | dict[str, Any]
    signatureHelpProvider: dict[str, Any]
    declarationProvider: bool | dict[str, Any]
    definitionProvider: bool | dict[str, Any]
    typeDefinitionProvider: bool | dict[str, Any]
    implementationProvider: bool | dict[str, Any]
    referencesProvider: bool | dict[str, Any]
    documentHighlightProvider: bool | dict[str, Any]
    documentSymbolProvider: bool | dict[str, Any]
    codeActionProvider: bool | dict[str, Any]
    codeLensProvider: dict[str, Any]
    documentLinkProvider: dict[str, Any]
    colorProvider: bool | dict[str, Any]
    documentFormattingProvider: bool | dict[str, Any]
    documentRangeFormattingProvider: bool | dict[str, Any]
    documentOnTypeFormattingProvider: dict[str, Any]
    renameProvider: bool | dict[str, Any]
    foldingRangeProvider: bool | dict[str, Any]
    executeCommandProvider: dict[str, Any]
    selectionRangeProvider: bool | dict[str, Any]
    linkedEditingRangeProvider: bool | dict[str, Any]
    callHierarchyProvider: bool | dict[str, Any]
    semanticTokensProvider: dict[str, Any]
    monikerProvider: bool | dict[str, Any]
    typeHierarchyProvider: bool | dict[str, Any]
    inlineValueProvider: bool | dict[str, Any]
    inlayHintProvider: bool | dict[str, Any]
    diagnosticProvider: dict[str, Any]
    workspaceSymbolProvider: bool | dict[str, Any]
    workspace: dict[str, Any]
    experimental: Any


class InitializeResult(TypedDict, total=False):
    """Result of initialize request."""

    capabilities: ServerCapabilities
    serverInfo: dict[str, Any]


class Diagnostic(TypedDict, total=False):
    """A diagnostic message."""

    range: Range
    severity: int
    code: int | str
    codeDescription: dict[str, Any]
    source: str
    message: str
    tags: list[int]
    relatedInformation: list[Any]
    data: Any


class PublishDiagnosticsParams(TypedDict):
    """Parameters for textDocument/publishDiagnostics notification."""

    uri: str
    version: int | None
    diagnostics: list[Diagnostic]
