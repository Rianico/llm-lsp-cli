"""LSP constants based on LSP 3.17 specification."""


class LSPConstants:
    """LSP protocol constants."""

    # JSON-RPC version
    JSONRPC_VERSION = "2.0"

    # Content type header
    CONTENT_TYPE = "application/vscode-jsonrpc; charset=utf-8"

    # Request methods (client -> server)
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    SHUTDOWN = "shutdown"
    EXIT = "exit"

    # Text document synchronization
    TEXT_DOCUMENT_DID_OPEN = "textDocument/didOpen"
    TEXT_DOCUMENT_DID_CHANGE = "textDocument/didChange"
    TEXT_DOCUMENT_DID_CLOSE = "textDocument/didClose"
    TEXT_DOCUMENT_DID_SAVE = "textDocument/didSave"
    TEXT_DOCUMENT_WILL_SAVE = "textDocument/willSave"
    TEXT_DOCUMENT_WILL_SAVE_WAIT_UNTIL = "textDocument/willSaveWaitUntil"

    # Language features
    COMPLETION = "textDocument/completion"
    HOVER = "textDocument/hover"
    SIGNATURE_HELP = "textDocument/signatureHelp"
    DEFINITION = "textDocument/definition"
    TYPE_DEFINITION = "textDocument/typeDefinition"
    IMPLEMENTATION = "textDocument/implementation"
    REFERENCES = "textDocument/references"
    DOCUMENT_HIGHLIGHT = "textDocument/documentHighlight"
    DOCUMENT_SYMBOL = "textDocument/documentSymbol"
    CODE_ACTION = "textDocument/codeAction"
    CODE_LENS = "textDocument/codeLens"
    DOCUMENT_LINK = "textDocument/documentLink"
    DOCUMENT_COLOR = "textDocument/documentColor"
    COLOR_PRESENTATION = "textDocument/colorPresentation"
    FORMATTING = "textDocument/formatting"
    RANGE_FORMATTING = "textDocument/rangeFormatting"
    ON_TYPE_FORMATTING = "textDocument/onTypeFormatting"
    RENAME = "textDocument/rename"
    FOLDING_RANGE = "textDocument/foldingRange"
    SELECTION_RANGE = "textDocument/selectionRange"
    PREPARE_CALL_HIERARCHY = "textDocument/prepareCallHierarchy"
    SEMANTIC_TOKENS_FULL = "textDocument/semanticTokens/full"
    PREPARE_TYPE_HIERARCHY = "textDocument/prepareTypeHierarchy"
    INLINE_VALUE = "textDocument/inlineValue"
    INLAY_HINT = "textDocument/inlayHint"
    DIAGNOSTIC = "textDocument/diagnostic"

    # Workspace features
    WORKSPACE_SYMBOL = "workspace/symbol"
    WORKSPACE_DIAGNOSTIC = "workspace/diagnostic"
    WORKSPACE_EXECUTE_COMMAND = "workspace/executeCommand"
    WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS = "workspace/didChangeWorkspaceFolders"
    WORKSPACE_DID_CREATE_FILES = "workspace/didCreateFiles"
    WORKSPACE_WILL_CREATE_FILES = "workspace/willCreateFiles"
    WORKSPACE_DID_RENAME_FILES = "workspace/didRenameFiles"
    WORKSPACE_WILL_RENAME_FILES = "workspace/willRenameFiles"
    WORKSPACE_DID_DELETE_FILES = "workspace/didDeleteFiles"
    WORKSPACE_WILL_DELETE_FILES = "workspace/willDeleteFiles"

    # Window features
    WINDOW_SHOW_MESSAGE = "window/showMessage"
    WINDOW_SHOW_MESSAGE_REQUEST = "window/showMessageRequest"
    WINDOW_LOG_MESSAGE = "window/logMessage"
    WINDOW_WORK_DONE_PROGRESS_CREATE = "window/workDoneProgress/create"

    # Client features
    CLIENT_REGISTER_CAPABILITY = "client/registerCapability"
    CLIENT_UNREGISTER_CAPABILITY = "client/unregisterCapability"

    # Workspace configuration
    WORKSPACE_CONFIGURATION = "workspace/configuration"

    # Progress notifications
    PROGRESS = "$/progress"
    SET_TRACE = "$/setTrace"
    LOG_TRACE = "$/logTrace"

    # Cancel request
    CANCEL_REQUEST = "$/cancelRequest"

    # Common field names
    TEXT_DOCUMENT = "textDocument"
    POSITION = "position"
    RANGE = "range"
    URI = "uri"
    VERSION = "version"
    LANGUAGE_ID = "languageId"
    CONTENT_CHANGES = "contentChanges"
    CONTEXT = "context"

    # Completion trigger kinds
    COMPLETION_TRIGGER_INVOKED = 1
    COMPLETION_TRIGGER_TRIGGER_CHARACTER = 2
    COMPLETION_TRIGGER_TRIGGER_FOR_INCOMPLETE_COMPLETIONS = 3

    # Completion item kinds
    ITEM_KIND_TEXT = 1
    ITEM_KIND_METHOD = 2
    ITEM_KIND_FUNCTION = 3
    ITEM_KIND_CONSTRUCTOR = 4
    ITEM_KIND_FIELD = 5
    ITEM_KIND_VARIABLE = 6
    ITEM_KIND_CLASS = 7
    ITEM_KIND_INTERFACE = 8
    ITEM_KIND_MODULE = 9
    ITEM_KIND_PROPERTY = 10
    ITEM_KIND_UNIT = 11
    ITEM_KIND_VALUE = 12
    ITEM_KIND_ENUM = 13
    ITEM_KIND_KEYWORD = 14
    ITEM_KIND_SNIPPET = 15
    ITEM_KIND_COLOR = 16
    ITEM_KIND_FILE = 17
    ITEM_KIND_REFERENCE = 18
    ITEM_KIND_FOLDER = 19
    ITEM_KIND_ENUM_MEMBER = 20
    ITEM_KIND_CONSTANT = 21
    ITEM_KIND_STRUCT = 22
    ITEM_KIND_EVENT = 23
    ITEM_KIND_OPERATOR = 24
    ITEM_KIND_TYPE_PARAMETER = 25

    # Symbol kinds
    SYMBOL_KIND_FILE = 1
    SYMBOL_KIND_MODULE = 2
    SYMBOL_KIND_NAMESPACE = 3
    SYMBOL_KIND_PACKAGE = 4
    SYMBOL_KIND_CLASS = 5
    SYMBOL_KIND_METHOD = 6
    SYMBOL_KIND_PROPERTY = 7
    SYMBOL_KIND_FIELD = 8
    SYMBOL_KIND_CONSTRUCTOR = 9
    SYMBOL_KIND_ENUM = 10
    SYMBOL_KIND_INTERFACE = 11
    SYMBOL_KIND_FUNCTION = 12
    SYMBOL_KIND_VARIABLE = 13
    SYMBOL_KIND_CONSTANT = 14
    SYMBOL_KIND_STRING = 15
    SYMBOL_KIND_NUMBER = 16
    SYMBOL_KIND_BOOLEAN = 17
    SYMBOL_KIND_ARRAY = 18
    SYMBOL_KIND_OBJECT = 19
    SYMBOL_KIND_KEY = 20
    SYMBOL_KIND_NULL = 21
    SYMBOL_KIND_ENUM_MEMBER = 22
    SYMBOL_KIND_STRUCT = 23
    SYMBOL_KIND_EVENT = 24
    SYMBOL_KIND_OPERATOR = 25
    SYMBOL_KIND_TYPE_PARAMETER = 26

    # Diagnostic severity
    DIAGNOSTIC_ERROR = 1
    DIAGNOSTIC_WARNING = 2
    DIAGNOSTIC_INFORMATION = 3
    DIAGNOSTIC_HINT = 4

    # Text document sync kind
    TEXT_DOCUMENT_SYNC_NONE = 0
    TEXT_DOCUMENT_SYNC_FULL = 1
    TEXT_DOCUMENT_SYNC_INCREMENTAL = 2

    # Error codes
    ERROR_PARSE_ERROR = -32700
    ERROR_INVALID_REQUEST = -32600
    ERROR_METHOD_NOT_FOUND = -32601
    ERROR_INVALID_PARAMS = -32602
    ERROR_INTERNAL_ERROR = -32603
    ERROR_SERVER_NOT_INITIALIZED = -32002
    ERROR_UNKNOWN_ERROR_CODE = -32001
    ERROR_REQUEST_CANCELLED = -32800
    ERROR_CONTENT_MODIFIED = -32801
