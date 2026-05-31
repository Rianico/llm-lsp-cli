"""RPC request handler for daemon LSP operations."""

import asyncio
import logging
import os
from collections import OrderedDict
from pathlib import Path

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.daemon.document_sync import DocumentSyncContext
from llm_lsp_cli.domain.services import LspMethodRouter
from llm_lsp_cli.domain.services.lsp_method_router import LspMethodConfig, ParamCategory
from llm_lsp_cli.ipc.protocol import serialize_for_json
from llm_lsp_cli.lsp.constants import RESPONSE_KEYS, LSPConstants
from llm_lsp_cli.server import ServerRegistry

logger = logging.getLogger("llm-lsp-cli.daemon")


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
        config = self._router.get_config(method)
        if config is None:
            raise ValueError(f"Unknown LSP method: {method}")

        response_key = self.RESPONSE_KEYS.get(method, "result")

        logger.debug(f"Handling LSP method: {method} with params: {params}")

        # Check if this method requires document synchronization
        requires_doc_sync = config.registry_method in {
            "request_diagnostics",
            "request_document_symbols",
        }

        if requires_doc_sync:
            return await self._handle_doc_sync_method(method, params, response_key)
        else:
            return await self._handle_standard_lsp_method(method, params, response_key)

    async def _handle_doc_sync_method(
        self,
        method: str,
        params: dict[str, object],
        response_key: str,
    ) -> dict[str, object]:
        """Handle LSP methods that require document synchronization.

        These methods need didOpen -> request -> done (files stay open per ADR-0008).
        Uses DocumentSyncContext for proper file lifecycle management.

        Args:
            method: LSP method name
            params: Request parameters
            response_key: Key to use in response dict

        Returns:
            Response dict with appropriate key
        """
        file_path_val = params.get("filePath")
        if file_path_val is None:
            raise ValueError("Missing 'filePath' parameter")
        if not isinstance(file_path_val, str):
            raise ValueError("'filePath' must be a string")

        file_path_obj = Path(file_path_val)
        workspace_path_val = params.get("workspacePath", ".")
        if not isinstance(workspace_path_val, str):
            workspace_path_val = "."

        workspace = await self._registry.get_or_create_workspace(workspace_path_val)
        client = await workspace.ensure_initialized()

        lock = self._get_file_lock(file_path_obj)
        try:
            async with lock, DocumentSyncContext(client, file_path_obj) as uri:
                lsp_params: dict[str, object] = {"textDocument": {"uri": uri}}

                # For diagnostics, pass mtime for cache optimization
                if method == LSPConstants.DIAGNOSTIC:
                    try:
                        lsp_params["_mtime"] = os.stat(str(file_path_obj)).st_mtime
                    except OSError:
                        logger.debug(
                            f"Could not stat file {file_path_obj}, "
                            "proceeding without mtime"
                        )

                result = await client.request(method, lsp_params)

                result = serialize_for_json(result)
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
        response_key: str,
    ) -> dict[str, object]:
        """Handle standard LSP methods that don't require document sync.

        Builds LSP params from RPC params and dispatches via client.request().

        Args:
            method: LSP method name
            params: Request parameters
            response_key: Key to use in response dict

        Returns:
            Response dict with appropriate key
        """
        try:
            config = self._router.get_config(method)
            if config is None:
                raise ValueError(f"Unknown LSP method: {method}")

            extracted = extract_registry_params(config, params, self._DEFAULT_WORKSPACE)

            if config.registry_method == "request_rename" and "new_name" not in extracted:
                raise ValueError("Missing 'newName' parameter")

            # Build LSP params from extracted RPC params
            lsp_params = self._build_lsp_params(method, extracted)

            # Get workspace and client
            workspace_path = str(extracted.get("workspace_path", self._DEFAULT_WORKSPACE))
            result = await self._registry.request(workspace_path, method, lsp_params)

            logger.debug(f"Registry method returned for {method}")

            result = serialize_for_json(result)
            if response_key == "hover":
                return {response_key: result} if result else {}
            return {response_key: result}

        except Exception as e:
            logger.exception(f"Error handling LSP method {method}: {e}")
            raise

    def _build_lsp_params(
        self, method: str, extracted: dict[str, object]
    ) -> dict[str, object]:
        """Build LSP params dict from extracted RPC params.

        Args:
            method: LSP method name
            extracted: Extracted and validated RPC params (snake_case)

        Returns:
            LSP params dict ready for client.request()
        """
        file_path = extracted.get("file_path")
        raw_line = extracted.get("line", 0)
        raw_column = extracted.get("column", 0)
        line = int(raw_line) if isinstance(raw_line, (int, float)) else 0
        column = int(raw_column) if isinstance(raw_column, (int, float)) else 0

        if method == LSPConstants.WORKSPACE_SYMBOL:
            query = str(extracted.get("query", ""))
            return {"query": query}

        if method == LSPConstants.WORKSPACE_DIAGNOSTIC:
            return {}

        if file_path is not None:
            # Resolve file path relative to workspace
            workspace_path = str(extracted.get("workspace_path", self._DEFAULT_WORKSPACE))
            path = Path(str(file_path))
            if not path.is_absolute():
                path = Path(workspace_path) / path
            path = path.resolve()
            uri = path.as_uri()

            text_doc: dict[str, object] = {"uri": uri}
            position: dict[str, object] = {"line": line, "character": column}

            if method == LSPConstants.DEFINITION:
                return {"textDocument": text_doc, "position": position}
            if method == LSPConstants.REFERENCES:
                return {
                    "textDocument": text_doc,
                    "position": position,
                    "context": {"includeDeclaration": True},
                }
            if method == LSPConstants.COMPLETION:
                return {
                    "textDocument": text_doc,
                    "position": position,
                    "context": {"triggerKind": 1},
                }
            if method == LSPConstants.HOVER:
                return {"textDocument": text_doc, "position": position}
            if method == LSPConstants.DOCUMENT_SYMBOL:
                return {"textDocument": text_doc}
            if method == LSPConstants.DIAGNOSTIC:
                return {"textDocument": text_doc}
            if method == LSPConstants.PREPARE_CALL_HIERARCHY:
                return {"textDocument": text_doc, "position": position}
            if method == LSPConstants.CALL_HIERARCHY_INCOMING_CALLS:
                return {"textDocument": text_doc, "position": position}
            if method == LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS:
                return {"textDocument": text_doc, "position": position}
            if method == LSPConstants.PREPARE_RENAME:
                return {"textDocument": text_doc, "position": position}
            if method == LSPConstants.RENAME:
                new_name = str(extracted.get("new_name", ""))
                return {
                    "textDocument": text_doc,
                    "position": position,
                    "newName": new_name,
                }

        return {}

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
