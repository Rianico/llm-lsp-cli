"""RPC request handler for daemon LSP operations."""

import asyncio
import logging
import os
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.daemon.document_sync import DocumentSyncContext
from llm_lsp_cli.domain.services import LspMethodRouter
from llm_lsp_cli.domain.services.lsp_method_router import LspMethodConfig, ParamCategory
from llm_lsp_cli.ipc.protocol import serialize_for_json
from llm_lsp_cli.lsp import types as lsp
from llm_lsp_cli.lsp.constants import RESPONSE_KEYS, LSPConstants
from llm_lsp_cli.server import ServerRegistry

if TYPE_CHECKING:
    from llm_lsp_cli.lsp.client import LSPClient

logger = logging.getLogger("llm-lsp-cli.daemon")

# Valid registry method names for validation.
# Actual dispatch uses bound methods from the registry instance.
_VALID_REGISTRY_METHODS: frozenset[str] = frozenset({
    "request_definition",
    "request_references",
    "request_completions",
    "request_hover",
    "request_document_symbols",
    "request_workspace_symbols",
    "request_diagnostics",
    "request_workspace_diagnostics",
    "request_call_hierarchy_incoming",
    "request_call_hierarchy_outgoing",
    "request_prepare_rename",
    "request_rename",
})


def extract_registry_params(
    config: LspMethodConfig,
    params: dict[str, object],
    default_workspace: str,
) -> dict[str, object]:
    """Extract and validate params for a registry method call.

    Converts camelCase RPC params to snake_case registry params.
    Validates required params and applies defaults.

    Args:
        config: Method configuration from LspMethodRouter.
        params: Raw RPC params (camelCase).
        default_workspace: Default workspace path if not provided.

    Returns:
        Dict of snake_case params ready for registry method call.

    Raises:
        ValueError: If required params are missing or have wrong type.
    """
    result: dict[str, object] = {}

    # workspace_path is always present
    workspace_path = params.get("workspacePath", default_workspace)
    if not isinstance(workspace_path, str):
        workspace_path = default_workspace
    result["workspace_path"] = workspace_path

    if config.param_category == ParamCategory.POSITION:
        # filePath required
        file_path = params.get("filePath")
        if file_path is None:
            raise ValueError("Missing 'filePath' parameter")
        if not isinstance(file_path, str):
            raise ValueError("'filePath' must be a string")
        result["file_path"] = file_path

        # line and column with defaults
        line = params.get("line", 0)
        column = params.get("column", 0)
        result["line"] = line if isinstance(line, int) else 0
        result["column"] = column if isinstance(column, int) else 0

        # newName for rename (optional per method, validated at call site)
        new_name = params.get("newName")
        if new_name is not None:
            if not isinstance(new_name, str):
                raise ValueError("'newName' must be a string")
            result["new_name"] = new_name

    elif config.param_category == ParamCategory.FILE:
        # filePath required
        file_path = params.get("filePath")
        if file_path is None:
            raise ValueError("Missing 'filePath' parameter")
        if not isinstance(file_path, str):
            raise ValueError("'filePath' must be a string")
        result["file_path"] = file_path

    elif config.param_category == ParamCategory.WORKSPACE:
        # query for workspace symbols (optional)
        query = params.get("query", "")
        if isinstance(query, str):
            result["query"] = query
        else:
            result["query"] = ""

    return result


class RequestHandler:
    """Handles incoming RPC requests."""

    # Reference module-level constant for backward compatibility
    RESPONSE_KEYS: dict[str, str] = RESPONSE_KEYS

    # Default workspace path when not provided in params
    _DEFAULT_WORKSPACE: str = "."

    # Maximum number of file locks before LRU eviction
    _FILE_LOCKS_MAX: int = 1000

    _shutdown: bool
    _workspace_path: str
    _language: str
    _lsp_conf: str | None
    _registry: ServerRegistry
    _router: LspMethodRouter
    _file_locks: OrderedDict[str, asyncio.Lock]

    def __init__(self, workspace_path: str, language: str, lsp_conf: str | None = None):
        self._shutdown = False
        self._workspace_path = workspace_path
        self._language = language
        self._lsp_conf = lsp_conf
        self._registry = ServerRegistry(lsp_conf=lsp_conf)
        self._router = LspMethodRouter()
        self._file_locks = OrderedDict()

    def _get_file_lock(self, file_path: Path) -> asyncio.Lock:
        """Get or create an asyncio.Lock for a specific file path.

        This ensures that concurrent requests for the same file are serialized
        to prevent interleaving of didOpen/didClose sequences.

        Uses OrderedDict for LRU-style eviction when the lock count exceeds
        _FILE_LOCKS_MAX (default 1000). Evicts the oldest half of entries.

        Args:
            file_path: Path to the file

        Returns:
            asyncio.Lock for the file path
        """
        path_str = str(file_path)
        if path_str not in self._file_locks:
            # Evict oldest half if we've exceeded the threshold
            if len(self._file_locks) >= self._FILE_LOCKS_MAX:
                for _ in range(self._FILE_LOCKS_MAX // 2):
                    self._file_locks.popitem(last=False)
            self._file_locks[path_str] = asyncio.Lock()
        else:
            # Move to end (most recently used)
            self._file_locks.move_to_end(path_str)
        return self._file_locks[path_str]

    async def shutdown_servers(self) -> None:
        """Shutdown all LSP servers managed by this handler."""
        await self._registry.shutdown_all()

    async def handle(self, method: str, params: dict[str, object]) -> dict[str, object]:
        """Route request to appropriate handler."""
        logger.debug(f"Received request: {method} with params: {params}")

        if method == "ping":
            return {
                "status": "healthy",
                "daemon": True,
                "lsp_server": self._registry.has_workspaces,
            }

        elif method == "shutdown":
            self._shutdown = True
            return {"status": "shutting_down"}

        elif method == "status":
            socket_path = ConfigManager.build_socket_path(self._workspace_path, self._language)
            return {
                "running": True,
                "workspace": self._workspace_path,
                "language": self._language,
                "socket": str(socket_path),
                "workspace_socket": str(
                    Path(self._workspace_path) / ".llm-lsp-cli" / "socket"
                ),
                "pid": os.getpid(),
            }

        # LSP feature methods - dispatch to common handler
        elif method in {
            LSPConstants.DEFINITION,
            LSPConstants.REFERENCES,
            LSPConstants.COMPLETION,
            LSPConstants.HOVER,
            LSPConstants.DOCUMENT_SYMBOL,
            LSPConstants.DIAGNOSTIC,
            LSPConstants.WORKSPACE_SYMBOL,
            LSPConstants.WORKSPACE_DIAGNOSTIC,
            LSPConstants.CALL_HIERARCHY_INCOMING_CALLS,
            LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS,
            LSPConstants.PREPARE_RENAME,
            LSPConstants.RENAME,
        }:
            return await self._handle_lsp_method(method, params)

        # textDocument/didChange - external file change notification
        elif method == LSPConstants.TEXT_DOCUMENT_DID_CHANGE:
            return await self._handle_did_change(params)

        else:
            raise ValueError(f"Unknown method: {method}")

    async def _handle_lsp_method(self, method: str, params: dict[str, object]) -> dict[str, object]:
        """Handle LSP feature methods using common pattern.

        Args:
            method: LSP method name
            params: Request parameters

        Returns:
            Response dict with appropriate key

        Raises:
            ValueError: If required parameters are missing
        """
        # Get method config from router
        config = self._router.get_config(method)
        if config is None:
            raise ValueError(f"Unknown LSP method: {method}")

        registry_method = config.registry_method
        response_key = self.RESPONSE_KEYS.get(method, "result")

        # Log method entry with parameters
        logger.debug(f"Handling LSP method: {method} with params: {params}")

        # Check if this method requires document synchronization
        # Methods that operate on specific files need didOpen -> request
        # (files stay open per ADR-0008)
        requires_doc_sync = registry_method in {
            "request_diagnostics",
            "request_document_symbols",
        }

        if requires_doc_sync:
            # Extract file path from params
            file_path_val = params.get("filePath")
            if file_path_val is None:
                raise ValueError("Missing 'filePath' parameter")
            if not isinstance(file_path_val, str):
                raise ValueError("'filePath' must be a string")

            file_path_obj = Path(file_path_val)

            # Get workspace path for registry call
            workspace_path_val = params.get("workspacePath", ".")
            if not isinstance(workspace_path_val, str):
                workspace_path_val = "."

            # Get workspace and ensure client is initialized
            workspace = await self._registry.get_or_create_workspace(workspace_path_val)
            client = await workspace.ensure_initialized()

            # Use per-file lock to serialize requests for the same file
            lock = self._get_file_lock(file_path_obj)
            async with lock, DocumentSyncContext(client, file_path_obj) as uri:
                # Build typed params for the LSP request
                text_doc_id = lsp.TextDocumentIdentifier(uri=uri)
                if registry_method == "request_diagnostics":
                    lsp_params: lsp.DocumentSymbolParams | lsp.DocumentDiagnosticParams = (
                        lsp.DocumentDiagnosticParams(textDocument=text_doc_id)
                    )
                else:
                    lsp_params = lsp.DocumentSymbolParams(textDocument=text_doc_id)
                return await self._send_lsp_request(
                    method,
                    registry_method,
                    response_key,
                    lsp_params,
                    client,
                    str(file_path_obj),
                )
        else:
            # Non file-specific methods (workspace symbols, workspace diagnostics)
            # or position-based methods that use _ensure_open internally
            return await self._handle_standard_lsp_method(
                method, params, registry_method, response_key
            )

    async def _send_lsp_request(
        self,
        method: str,
        registry_method: str,
        response_key: str,
        lsp_params: lsp.DocumentSymbolParams | lsp.DocumentDiagnosticParams,
        client: LSPClient,
        file_path: str,
    ) -> dict[str, object]:
        """Send LSP request using client directly.

        When called from document sync context, we use the client directly
        to avoid double-opening the document.

        Args:
            method: LSP method name (for logging)
            registry_method: Name of registry method (for routing)
            response_key: Key to use in response dict
            lsp_params: Typed LSP request parameters
            client: LSPClient instance to use
            file_path: File path for fallback

        Returns:
            Response dict with appropriate key
        """
        try:
            # Extract URI from typed params
            uri = lsp_params.text_document.uri

            # Get file mtime for cache staleness check
            # Per ADR-0008: mtime is ground truth for cache validation
            mtime: float | None = None
            try:
                mtime = os.stat(file_path).st_mtime
            except OSError:
                # File may have been deleted or permission denied
                # Proceed with mtime=None to force server query
                logger.debug(f"Could not stat file {file_path}, proceeding without mtime")

            # Call client method directly with uri to avoid _ensure_open
            # Result type varies: diagnostics -> list[dict], symbols -> list[DocumentSymbol]
            result: object
            if registry_method == "request_diagnostics":
                result = await client.request_diagnostics(file_path=file_path, uri=uri, mtime=mtime)
            elif registry_method == "request_document_symbols":
                result = await client.request_document_symbols(file_path=file_path, uri=uri)
            else:
                # Should never happen - only diagnostics and document_symbols
                raise ValueError(f"Unsupported doc sync method: {registry_method}")

            logger.debug(f"Client method {registry_method} returned for {method}")

            # Convert Pydantic models to JSON-serializable dicts
            result = serialize_for_json(result)

            # Wrap result with appropriate response key
            if response_key == "hover":
                return {response_key: result} if result else {}
            return {response_key: result}

        except Exception as e:
            logger.exception(f"Error handling LSP method {method}: {e}")
            raise

    async def _handle_standard_lsp_method(
        self,
        method: str,
        params: dict[str, object],
        registry_method: str,
        response_key: str,
    ) -> dict[str, object]:
        """Handle standard LSP methods that don't require document sync.

        Uses extract_registry_params() for param extraction and dispatches
        to the registry method via getattr.

        Args:
            method: LSP method name
            params: Request parameters
            registry_method: Name of registry method to call
            response_key: Key to use in response dict

        Returns:
            Response dict with appropriate key
        """
        try:
            # Get method config from router
            config = self._router.get_config(method)
            if config is None:
                raise ValueError(f"Unknown LSP method: {method}")

            # Extract validated params using the router config
            extracted = extract_registry_params(
                config, params, self._DEFAULT_WORKSPACE
            )

            # Validate rename requires newName
            if registry_method == "request_rename" and "new_name" not in extracted:
                raise ValueError("Missing 'newName' parameter")

            # Dispatch to registry method via validated lookup
            if registry_method not in _VALID_REGISTRY_METHODS:
                raise ValueError(f"Unknown registry method: {registry_method}")
            registry_fn: Callable[..., Awaitable[object]] = getattr(
                self._registry, registry_method
            )
            result: object = await registry_fn(**extracted)

            logger.debug(f"Registry method returned for {method}")

            # Convert Pydantic models to JSON-serializable dicts
            result = serialize_for_json(result)

            # Wrap result with appropriate response key
            if response_key == "hover":
                return {response_key: result} if result else {}
            return {response_key: result}

        except Exception as e:
            logger.exception(f"Error handling LSP method {method}: {e}")
            raise

    async def _handle_did_change(self, params: dict[str, object]) -> dict[str, object]:
        """Handle textDocument/didChange for external file change notification.

        Per ADR-0010, this method:
        1. Checks cache state and mtime to decide if didOpen is needed
        2. Sends didOpen if file is not open or mtime differs (stale)
        3. Sends didChange with full text sync
        4. Returns acknowledgment (not diagnostics)
        5. Does NOT mutate cache mtime

        Args:
            params: Request parameters with filePath and optional mtime

        Returns:
            {"status": "acknowledged"}

        Raises:
            ValueError: If filePath parameter is missing
            FileNotFoundError: If file does not exist
        """
        # Extract and validate file path
        file_path_val = params.get("filePath")
        if file_path_val is None:
            raise ValueError("Missing 'filePath' parameter")
        if not isinstance(file_path_val, str):
            raise ValueError("'filePath' must be a string")

        file_path = Path(file_path_val)

        # Verify file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get current mtime
        current_mtime = os.stat(file_path).st_mtime

        # Get workspace and client
        workspace_path_val = params.get("workspacePath", self._workspace_path)
        if not isinstance(workspace_path_val, str):
            workspace_path_val = self._workspace_path
        workspace = await self._registry.get_or_create_workspace(workspace_path_val)
        client = await workspace.ensure_initialized()

        # Get file URI and cache state
        uri = file_path.as_uri()
        file_state = await client.get_diagnostic_cache_state(uri)

        # Decide if didOpen is needed:
        # - File not open (is_open=False) -> send didOpen
        # - mtime differs (stale) -> send didOpen
        # - mtime matches and is_open -> skip didOpen (optimization)
        needs_didopen = not file_state.is_open
        if not needs_didopen and file_state.mtime > 0:
            is_stale = await client.is_diagnostic_cache_stale(uri, current_mtime)
            needs_didopen = is_stale

        if needs_didopen:
            # Send didOpen with current content
            content = file_path.read_text(encoding="utf-8")
            _ = await client.open_document(file_path, content)
            # Mark as open in cache WITHOUT updating mtime
            # Per ADR-0010: rely on existing mtime-based invalidation
            await client.mark_diagnostic_cache_open(uri)

        # Read current content and send didChange
        content = file_path.read_text(encoding="utf-8")
        _ = await client.send_did_change(file_path, content)

        # Return acknowledgment (not diagnostics)
        return {"status": "acknowledged"}
