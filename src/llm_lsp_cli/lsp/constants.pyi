"""Type stubs for LSP constants.

MAINTENANCE NOTE: This file must be kept in sync with constants.py!
When adding a new method-name constant:
1. Add the runtime value in constants.py with Final[str]
2. Add the type declaration here with Literal["..."]
3. Only method-name constants used in send_request() overloads need Literal types
"""

from typing import Literal

class LSPConstants:
    """LSP protocol constants type stubs.

    MAINTENANCE NOTE: Method-name constants (those used in send_request calls)
    have corresponding Literal type declarations here.
    When adding a new method constant, update BOTH files!
    """

    # === METHOD NAMES USED IN send_request() OVERLOADS ===
    # These MUST match the Literal types in commands/shared.py @overload declarations

    # Text document methods
    DEFINITION: Literal["textDocument/definition"]
    DOCUMENT_SYMBOL: Literal["textDocument/documentSymbol"]
    COMPLETION: Literal["textDocument/completion"]
    HOVER: Literal["textDocument/hover"]
    REFERENCES: Literal["textDocument/references"]
    PREPARE_RENAME: Literal["textDocument/prepareRename"]
    RENAME: Literal["textDocument/rename"]
    DIAGNOSTIC: Literal["textDocument/diagnostic"]
    TEXT_DOCUMENT_DID_CHANGE: Literal["textDocument/didChange"]

    # Workspace methods
    WORKSPACE_SYMBOL: Literal["workspace/symbol"]
    WORKSPACE_DIAGNOSTIC: Literal["workspace/diagnostic"]

    # Call hierarchy methods
    CALL_HIERARCHY_INCOMING_CALLS: Literal["callHierarchy/incomingCalls"]
    CALL_HIERARCHY_OUTGOING_CALLS: Literal["callHierarchy/outgoingCalls"]

    # === OTHER CONSTANTS (not used in overloads, keep as str) ===
    JSONRPC_VERSION: str
    CONTENT_TYPE: str

    # Request methods (client -> server)
    INITIALIZE: str
    INITIALIZED: str
    SHUTDOWN: str
    EXIT: str

    # Text document synchronization (others not used in overloads)
    TEXT_DOCUMENT_DID_OPEN: str
    TEXT_DOCUMENT_DID_CLOSE: str
    TEXT_DOCUMENT_DID_SAVE: str
    TEXT_DOCUMENT_WILL_SAVE: str
    TEXT_DOCUMENT_WILL_SAVE_WAIT_UNTIL: str

    # Language features (others not used in overloads)
    SIGNATURE_HELP: str
    TYPE_DEFINITION: str
    IMPLEMENTATION: str
    DOCUMENT_HIGHLIGHT: str
    CODE_ACTION: str
    CODE_LENS: str
    DOCUMENT_LINK: str
    DOCUMENT_COLOR: str
    COLOR_PRESENTATION: str
    FORMATTING: str
    RANGE_FORMATTING: str
    ON_TYPE_FORMATTING: str
    FOLDING_RANGE: str
    SELECTION_RANGE: str
    PREPARE_CALL_HIERARCHY: str
    SEMANTIC_TOKENS_FULL: str
    PREPARE_TYPE_HIERARCHY: str
    INLINE_VALUE: str
    INLAY_HINT: str

    # Workspace features (others not used in overloads)
    WORKSPACE_EXECUTE_COMMAND: str
    WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS: str
    WORKSPACE_DID_CREATE_FILES: str
    WORKSPACE_WILL_CREATE_FILES: str
    WORKSPACE_DID_RENAME_FILES: str
    WORKSPACE_WILL_RENAME_FILES: str
    WORKSPACE_DID_DELETE_FILES: str
    WORKSPACE_WILL_DELETE_FILES: str

    # Window features
    WINDOW_SHOW_MESSAGE: str
    WINDOW_SHOW_MESSAGE_REQUEST: str
    WINDOW_LOG_MESSAGE: str
    WINDOW_WORK_DONE_PROGRESS_CREATE: str

    # Client features
    CLIENT_REGISTER_CAPABILITY: str
    CLIENT_UNREGISTER_CAPABILITY: str

    # Workspace configuration
    WORKSPACE_CONFIGURATION: str

    # Progress notifications
    PROGRESS: str
    SET_TRACE: str
    LOG_TRACE: str

    # Cancel request
    CANCEL_REQUEST: str

    # Common field names
    TEXT_DOCUMENT: str
    POSITION: str
    RANGE: str
    URI: str
    VERSION: str
    LANGUAGE_ID: str
    CONTENT_CHANGES: str
    CONTEXT: str

    # Completion trigger kinds (int)
    COMPLETION_TRIGGER_INVOKED: int
    COMPLETION_TRIGGER_TRIGGER_CHARACTER: int
    COMPLETION_TRIGGER_TRIGGER_FOR_INCOMPLETE_COMPLETIONS: int

    # Completion item kinds (int)
    ITEM_KIND_TEXT: int
    ITEM_KIND_METHOD: int
    ITEM_KIND_FUNCTION: int
    ITEM_KIND_CONSTRUCTOR: int
    ITEM_KIND_FIELD: int
    ITEM_KIND_VARIABLE: int
    ITEM_KIND_CLASS: int
    ITEM_KIND_INTERFACE: int
    ITEM_KIND_MODULE: int
    ITEM_KIND_PROPERTY: int
    ITEM_KIND_UNIT: int
    ITEM_KIND_VALUE: int
    ITEM_KIND_ENUM: int
    ITEM_KIND_KEYWORD: int
    ITEM_KIND_SNIPPET: int
    ITEM_KIND_COLOR: int
    ITEM_KIND_FILE: int
    ITEM_KIND_REFERENCE: int
    ITEM_KIND_FOLDER: int
    ITEM_KIND_ENUM_MEMBER: int
    ITEM_KIND_CONSTANT: int
    ITEM_KIND_STRUCT: int
    ITEM_KIND_EVENT: int
    ITEM_KIND_OPERATOR: int
    ITEM_KIND_TYPE_PARAMETER: int

    # Symbol kinds (int)
    SYMBOL_KIND_FILE: int
    SYMBOL_KIND_MODULE: int
    SYMBOL_KIND_NAMESPACE: int
    SYMBOL_KIND_PACKAGE: int
    SYMBOL_KIND_CLASS: int
    SYMBOL_KIND_METHOD: int
    SYMBOL_KIND_PROPERTY: int
    SYMBOL_KIND_FIELD: int
    SYMBOL_KIND_CONSTRUCTOR: int
    SYMBOL_KIND_ENUM: int
    SYMBOL_KIND_INTERFACE: int
    SYMBOL_KIND_FUNCTION: int
    SYMBOL_KIND_VARIABLE: int
    SYMBOL_KIND_CONSTANT: int
    SYMBOL_KIND_STRING: int
    SYMBOL_KIND_NUMBER: int
    SYMBOL_KIND_BOOLEAN: int
    SYMBOL_KIND_ARRAY: int
    SYMBOL_KIND_OBJECT: int
    SYMBOL_KIND_KEY: int
    SYMBOL_KIND_NULL: int
    SYMBOL_KIND_ENUM_MEMBER: int
    SYMBOL_KIND_STRUCT: int
    SYMBOL_KIND_EVENT: int
    SYMBOL_KIND_OPERATOR: int
    SYMBOL_KIND_TYPE_PARAMETER: int

    # Diagnostic severity (int)
    DIAGNOSTIC_ERROR: int
    DIAGNOSTIC_WARNING: int
    DIAGNOSTIC_INFORMATION: int
    DIAGNOSTIC_HINT: int

    # Text document sync kind (int)
    TEXT_DOCUMENT_SYNC_NONE: int
    TEXT_DOCUMENT_SYNC_FULL: int
    TEXT_DOCUMENT_SYNC_INCREMENTAL: int

    # Error codes (int)
    ERROR_PARSE_ERROR: int
    ERROR_INVALID_REQUEST: int
    ERROR_METHOD_NOT_FOUND: int
    ERROR_INVALID_PARAMS: int
    ERROR_INTERNAL_ERROR: int
    ERROR_SERVER_NOT_INITIALIZED: int
    ERROR_UNKNOWN_ERROR_CODE: int
    ERROR_REQUEST_CANCELLED: int
    ERROR_CONTENT_MODIFIED: int


RESPONSE_KEYS: dict[str, str]
