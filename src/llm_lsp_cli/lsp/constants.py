"""LSP constants based on LSP 3.17 specification."""


class LSPConstants:
    """LSP protocol constants."""

    # JSON-RPC version
    JSONRPC_VERSION: str = "2.0"

    # Content type header
    CONTENT_TYPE: str = "application/vscode-jsonrpc; charset=utf-8"

    # Request methods (client -> server)
    INITIALIZE: str = "initialize"
    INITIALIZED: str = "initialized"
    SHUTDOWN: str = "shutdown"
    EXIT: str = "exit"

    # Text document synchronization
    TEXT_DOCUMENT_DID_OPEN: str = "textDocument/didOpen"
    TEXT_DOCUMENT_DID_CHANGE: str = "textDocument/didChange"
    TEXT_DOCUMENT_DID_CLOSE: str = "textDocument/didClose"
    TEXT_DOCUMENT_DID_SAVE: str = "textDocument/didSave"
    TEXT_DOCUMENT_WILL_SAVE: str = "textDocument/willSave"
    TEXT_DOCUMENT_WILL_SAVE_WAIT_UNTIL: str = "textDocument/willSaveWaitUntil"

    # Language features
    COMPLETION: str = "textDocument/completion"
    HOVER: str = "textDocument/hover"
    SIGNATURE_HELP: str = "textDocument/signatureHelp"
    DEFINITION: str = "textDocument/definition"
    TYPE_DEFINITION: str = "textDocument/typeDefinition"
    IMPLEMENTATION: str = "textDocument/implementation"
    REFERENCES: str = "textDocument/references"
    DOCUMENT_HIGHLIGHT: str = "textDocument/documentHighlight"
    DOCUMENT_SYMBOL: str = "textDocument/documentSymbol"
    CODE_ACTION: str = "textDocument/codeAction"
    CODE_LENS: str = "textDocument/codeLens"
    DOCUMENT_LINK: str = "textDocument/documentLink"
    DOCUMENT_COLOR: str = "textDocument/documentColor"
    COLOR_PRESENTATION: str = "textDocument/colorPresentation"
    FORMATTING: str = "textDocument/formatting"
    RANGE_FORMATTING: str = "textDocument/rangeFormatting"
    ON_TYPE_FORMATTING: str = "textDocument/onTypeFormatting"
    RENAME: str = "textDocument/rename"
    PREPARE_RENAME: str = "textDocument/prepareRename"
    FOLDING_RANGE: str = "textDocument/foldingRange"
    SELECTION_RANGE: str = "textDocument/selectionRange"
    PREPARE_CALL_HIERARCHY: str = "textDocument/prepareCallHierarchy"
    CALL_HIERARCHY_INCOMING_CALLS: str = "callHierarchy/incomingCalls"
    CALL_HIERARCHY_OUTGOING_CALLS: str = "callHierarchy/outgoingCalls"
    SEMANTIC_TOKENS_FULL: str = "textDocument/semanticTokens/full"
    PREPARE_TYPE_HIERARCHY: str = "textDocument/prepareTypeHierarchy"
    INLINE_VALUE: str = "textDocument/inlineValue"
    INLAY_HINT: str = "textDocument/inlayHint"
    DIAGNOSTIC: str = "textDocument/diagnostic"

    # Workspace features
    WORKSPACE_SYMBOL: str = "workspace/symbol"
    WORKSPACE_DIAGNOSTIC: str = "workspace/diagnostic"
    WORKSPACE_EXECUTE_COMMAND: str = "workspace/executeCommand"
    WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS: str = "workspace/didChangeWorkspaceFolders"
    WORKSPACE_DID_CREATE_FILES: str = "workspace/didCreateFiles"
    WORKSPACE_WILL_CREATE_FILES: str = "workspace/willCreateFiles"
    WORKSPACE_DID_RENAME_FILES: str = "workspace/didRenameFiles"
    WORKSPACE_WILL_RENAME_FILES: str = "workspace/willRenameFiles"
    WORKSPACE_DID_DELETE_FILES: str = "workspace/didDeleteFiles"
    WORKSPACE_WILL_DELETE_FILES: str = "workspace/willDeleteFiles"

    # Window features
    WINDOW_SHOW_MESSAGE: str = "window/showMessage"
    WINDOW_SHOW_MESSAGE_REQUEST: str = "window/showMessageRequest"
    WINDOW_LOG_MESSAGE: str = "window/logMessage"
    WINDOW_WORK_DONE_PROGRESS_CREATE: str = "window/workDoneProgress/create"

    # Client features
    CLIENT_REGISTER_CAPABILITY: str = "client/registerCapability"
    CLIENT_UNREGISTER_CAPABILITY: str = "client/unregisterCapability"

    # Workspace configuration
    WORKSPACE_CONFIGURATION: str = "workspace/configuration"

    # Progress notifications
    PROGRESS: str = "$/progress"
    SET_TRACE: str = "$/setTrace"
    LOG_TRACE: str = "$/logTrace"

    # Cancel request
    CANCEL_REQUEST: str = "$/cancelRequest"

    # Common field names
    TEXT_DOCUMENT: str = "textDocument"
    POSITION: str = "position"
    RANGE: str = "range"
    URI: str = "uri"
    VERSION: str = "version"
    LANGUAGE_ID: str = "languageId"
    CONTENT_CHANGES: str = "contentChanges"
    CONTEXT: str = "context"

    # Completion trigger kinds
    COMPLETION_TRIGGER_INVOKED: int = 1
    COMPLETION_TRIGGER_TRIGGER_CHARACTER: int = 2
    COMPLETION_TRIGGER_TRIGGER_FOR_INCOMPLETE_COMPLETIONS: int = 3

    # Completion item kinds
    ITEM_KIND_TEXT: int = 1
    ITEM_KIND_METHOD: int = 2
    ITEM_KIND_FUNCTION: int = 3
    ITEM_KIND_CONSTRUCTOR: int = 4
    ITEM_KIND_FIELD: int = 5
    ITEM_KIND_VARIABLE: int = 6
    ITEM_KIND_CLASS: int = 7
    ITEM_KIND_INTERFACE: int = 8
    ITEM_KIND_MODULE: int = 9
    ITEM_KIND_PROPERTY: int = 10
    ITEM_KIND_UNIT: int = 11
    ITEM_KIND_VALUE: int = 12
    ITEM_KIND_ENUM: int = 13
    ITEM_KIND_KEYWORD: int = 14
    ITEM_KIND_SNIPPET: int = 15
    ITEM_KIND_COLOR: int = 16
    ITEM_KIND_FILE: int = 17
    ITEM_KIND_REFERENCE: int = 18
    ITEM_KIND_FOLDER: int = 19
    ITEM_KIND_ENUM_MEMBER: int = 20
    ITEM_KIND_CONSTANT: int = 21
    ITEM_KIND_STRUCT: int = 22
    ITEM_KIND_EVENT: int = 23
    ITEM_KIND_OPERATOR: int = 24
    ITEM_KIND_TYPE_PARAMETER: int = 25

    # Symbol kinds
    SYMBOL_KIND_FILE: int = 1
    SYMBOL_KIND_MODULE: int = 2
    SYMBOL_KIND_NAMESPACE: int = 3
    SYMBOL_KIND_PACKAGE: int = 4
    SYMBOL_KIND_CLASS: int = 5
    SYMBOL_KIND_METHOD: int = 6
    SYMBOL_KIND_PROPERTY: int = 7
    SYMBOL_KIND_FIELD: int = 8
    SYMBOL_KIND_CONSTRUCTOR: int = 9
    SYMBOL_KIND_ENUM: int = 10
    SYMBOL_KIND_INTERFACE: int = 11
    SYMBOL_KIND_FUNCTION: int = 12
    SYMBOL_KIND_VARIABLE: int = 13
    SYMBOL_KIND_CONSTANT: int = 14
    SYMBOL_KIND_STRING: int = 15
    SYMBOL_KIND_NUMBER: int = 16
    SYMBOL_KIND_BOOLEAN: int = 17
    SYMBOL_KIND_ARRAY: int = 18
    SYMBOL_KIND_OBJECT: int = 19
    SYMBOL_KIND_KEY: int = 20
    SYMBOL_KIND_NULL: int = 21
    SYMBOL_KIND_ENUM_MEMBER: int = 22
    SYMBOL_KIND_STRUCT: int = 23
    SYMBOL_KIND_EVENT: int = 24
    SYMBOL_KIND_OPERATOR: int = 25
    SYMBOL_KIND_TYPE_PARAMETER: int = 26

    # Diagnostic severity
    DIAGNOSTIC_ERROR: int = 1
    DIAGNOSTIC_WARNING: int = 2
    DIAGNOSTIC_INFORMATION: int = 3
    DIAGNOSTIC_HINT: int = 4

    # Text document sync kind
    TEXT_DOCUMENT_SYNC_NONE: int = 0
    TEXT_DOCUMENT_SYNC_FULL: int = 1
    TEXT_DOCUMENT_SYNC_INCREMENTAL: int = 2

    # Error codes
    ERROR_PARSE_ERROR: int = -32700
    ERROR_INVALID_REQUEST: int = -32600
    ERROR_METHOD_NOT_FOUND: int = -32601
    ERROR_INVALID_PARAMS: int = -32602
    ERROR_INTERNAL_ERROR: int = -32603
    ERROR_SERVER_NOT_INITIALIZED: int = -32002
    ERROR_UNKNOWN_ERROR_CODE: int = -32001
    ERROR_REQUEST_CANCELLED: int = -32800
    ERROR_CONTENT_MODIFIED: int = -32801
