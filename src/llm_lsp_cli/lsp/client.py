"""LSP client implementation."""

import asyncio
import contextlib
import logging
import uuid
from pathlib import Path
from typing import Any, cast

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.infrastructure.lsp.progress_handler import ProgressHandler

from . import types as lsp
from .cache import DiagnosticCache
from .constants import LSPConstants
from .transport import LSPError, StdioTransport

logger = logging.getLogger(__name__)

# Timeouts and delays (in seconds)
_WORKSPACE_INDEX_TIMEOUT = 10.0
_WORKSPACE_DIAGNOSTIC_TIMEOUT = 30.0
_WORKSPACE_INDEX_WAIT = 2.0
_DOCUMENT_READY_WAIT = 2.0


class LSPClient:
    """LSP client for a single workspace."""

    def __init__(
        self,
        workspace_path: str,
        server_command: str,
        server_args: list[str] | None = None,
        language_id: str = "python",
        trace: bool = False,
        timeout: float = 30.0,
        lsp_conf: str | None = None,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.server_command = server_command
        self.server_args = server_args or []
        self.language_id = language_id
        self.trace = trace
        self.timeout = timeout
        self.lsp_conf = lsp_conf

        self._transport: StdioTransport | None = None
        self._initialized = False
        # uri -> (content, version, ready_event)
        self._open_files: dict[str, tuple[str, int, asyncio.Event]] = {}
        self._capabilities: lsp.ServerCapabilities | None = None
        self._workspace_indexed = asyncio.Event()
        # Unified diagnostic cache with relative path keys and version tracking
        self._diagnostic_cache = DiagnosticCache(self.workspace_path)
        # GUID tokens for workspace diagnostics (generated once per session)
        self._workspace_diagnostic_token: str | None = None
        self._work_done_token: str | None = None
        # Progress handler for work done progress
        self._progress_handler = ProgressHandler()
        # Server info from initialize response
        self._server_info: dict[str, Any] = {}

    async def initialize(self) -> lsp.InitializeResult:
        """Initialize the LSP connection."""
        self._transport = StdioTransport(
            command=self.server_command,
            args=self.server_args,
            cwd=str(self.workspace_path),
            trace=self.trace,
        )

        await self._transport.start()

        # Register notification handlers
        self._transport.on_notification(
            "window/logMessage",
            self._handle_log_message,
        )
        self._transport.on_notification(
            "textDocument/publishDiagnostics",
            self._handle_diagnostics,
        )
        self._transport.on_notification(
            "$/progress",
            self._handle_progress,
        )

        # Register server->client request handlers
        self._transport.on_request(
            "workspace/configuration",
            self._handle_configuration_request,
        )
        self._transport.on_request(
            "window/workDoneProgress/create",
            self._handle_work_done_progress_create_request,
        )

        # Send initialize request
        init_params = self._build_initialize_params()
        assert self._transport is not None
        response = await self._transport.send_request(
            LSPConstants.INITIALIZE,
            init_params,
            timeout=self.timeout,
        )

        self._capabilities = response.get("capabilities", {})

        # Capture server info if present
        self._server_info = response.get("serverInfo", {}) or {}

        # Send initialized notification
        assert self._transport is not None
        await self._transport.send_notification(LSPConstants.INITIALIZED, {})

        # Send workspace/diagnostic request with GUID tokens
        # This is a fire-and-forget request - results come via $/progress notifications
        await self._send_workspace_diagnostic_request()

        # Send workspace/didChangeConfiguration to set diagnosticMode=workspace
        # This tells the server to analyze the entire workspace, not just open files
        await self._transport.send_notification(
            "workspace/didChangeConfiguration",
            {
                "settings": {
                    "basedpyright": {"analysis": {"diagnosticMode": "workspace"}},
                    "python": {"analysis": {"diagnosticMode": "workspace"}},
                    "pyright": {"analysis": {"diagnosticMode": "workspace"}},
                }
            },
        )
        logger.debug("Sent workspace/didChangeConfiguration with diagnosticMode=workspace")

        # Start background task to mark workspace as indexed after a delay
        # Pyright needs time to scan and index the workspace before workspace/symbol works
        asyncio.create_task(self._wait_for_workspace_index())

        self._initialized = True
        logger.info("LSP server initialized")

        return cast(lsp.InitializeResult, response)

    @property
    def server_capabilities(self) -> lsp.ServerCapabilities:
        """Get the server capabilities.

        Returns:
            Server capabilities dict, or empty dict if not initialized.

        Note:
            This property provides access to the LSP server's capabilities
            for use by services like RenameService.
        """
        return self._capabilities or {}

    @property
    def server_info(self) -> dict[str, Any]:
        """Get the server info from initialize response.

        Returns:
            Server info dict containing 'name' and optionally 'version',
            or empty dict if serverInfo was not provided.
        """
        return self._server_info

    async def _wait_for_workspace_index(self) -> None:
        """Wait for workspace to be indexed by the LSP server.

        Pyright (and other LSP servers) need time to scan and index the workspace
        before workspace/symbol requests can return results. We wait a reasonable
        time then mark the workspace as indexed.
        """
        await asyncio.sleep(_WORKSPACE_INDEX_WAIT)
        self._workspace_indexed.set()
        logger.debug("Workspace indexing complete")

    def _build_initialize_params(self) -> dict[str, Any]:
        """Build initialize parameters."""
        return ConfigManager.load_initialize_params(
            server_command=self.server_command,
            workspace_path=str(self.workspace_path),
            custom_conf_path=self.lsp_conf,
        )

    def get_workspace_diagnostic_token(self) -> str:
        """Get the GUID token for workspace diagnostic progress matching.

        Returns a UUID4 token generated once per client session.
        This token is used to match $/progress notifications for workspace diagnostics.
        """
        if self._workspace_diagnostic_token is None:
            self._workspace_diagnostic_token = str(uuid.uuid4())
        return self._workspace_diagnostic_token

    def get_work_done_token(self) -> str:
        """Get the GUID token for work done progress matching.

        Returns a UUID4 token generated once per client session.
        """
        if self._work_done_token is None:
            self._work_done_token = str(uuid.uuid4())
        return self._work_done_token

    async def _send_workspace_diagnostic_request(self) -> None:
        """Send workspace/diagnostic request with GUID tokens.

        This is a fire-and-forget request - the server never sends a response.
        Results come via $/progress notifications instead.
        """
        assert self._transport is not None

        # Generate tokens if not already generated
        partial_result_token = self.get_workspace_diagnostic_token()
        work_done_token = self.get_work_done_token()

        params: dict[str, Any] = {
            "identifier": "basedpyright",
            "previousResultIds": [],
            "partialResultToken": partial_result_token,
            "workDoneToken": work_done_token,
        }

        # Send as fire-and-forget request
        await self._transport.send_request_fire_and_forget(
            LSPConstants.WORKSPACE_DIAGNOSTIC,
            params,
        )

    def _handle_workspace_diagnostic_progress(self, params: dict[str, Any]) -> None:
        """Handle $/progress notification for workspace diagnostics.

        Processes progress notifications that contain diagnostic items.
        Handles both:
        - Notifications with 'kind' field (begin/end)
        - Notifications with 'items' field (diagnostic reports)
        - basedpyright-style: no 'kind' at value level, just 'items'
        """
        value = params.get("value", {})

        if not isinstance(value, dict):
            return

        kind = value.get("kind", "")
        items = value.get("items", [])

        if kind == "begin":
            logger.debug(f"Workspace diagnostic collection started: {value.get('title', '')}")
            return

        if kind == "end":
            logger.debug("Workspace diagnostic collection complete")
            return

        # Process items if present (report notification or items without kind)
        if items:
            with contextlib.suppress(RuntimeError):
                # No running event loop - skip async processing
                # This can happen in unit tests without event loop
                asyncio.create_task(self._process_workspace_diagnostic_items(items))

    async def _process_workspace_diagnostic_items(self, items: list[dict[str, Any]]) -> None:
        """Process workspace diagnostic items and update cache."""
        for item in items:
            uri = item.get("uri", "")
            diagnostics = item.get("diagnostics", [])
            if uri:
                # Update cache with diagnostics (including empty list for files with no issues)
                await self._diagnostic_cache.update_diagnostics(uri, diagnostics)

    async def shutdown(self) -> None:
        """Shutdown the LSP connection."""
        if not self._initialized:
            return

        logger.info("Shutting down LSP client")

        # Close all open files
        for uri in list(self._open_files.keys()):
            assert self._transport is not None
            await self._transport.send_notification(
                LSPConstants.TEXT_DOCUMENT_DID_CLOSE,
                {"textDocument": {"uri": uri}},
            )

        # Shutdown sequence
        with contextlib.suppress(Exception):
            assert self._transport is not None
            await self._transport.send_request(
                LSPConstants.SHUTDOWN,
                timeout=self.timeout,
            )

        assert self._transport is not None
        await self._transport.send_notification(LSPConstants.EXIT)

        # Stop transport
        await self._transport.stop()

        self._initialized = False
        self._open_files.clear()
        self._capabilities = None

    async def request_definition(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> list[lsp.Location]:
        """Request definition at position."""
        uri = await self._ensure_open(file_path)

        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        }

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.DEFINITION,
            params,
            timeout=self.timeout,
        )

        return self._normalize_locations(result)

    async def request_references(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> list[lsp.Location]:
        """Request references at position."""
        uri = await self._ensure_open(file_path)

        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
            "context": {"includeDeclaration": True},
        }

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.REFERENCES,
            params,
            timeout=self.timeout,
        )

        return self._normalize_locations(result)

    async def request_completions(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> list[lsp.CompletionItem]:
        """Request completions at position."""
        uri = await self._ensure_open(file_path)

        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
            "context": {"triggerKind": LSPConstants.COMPLETION_TRIGGER_INVOKED},
        }

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.COMPLETION,
            params,
            timeout=self.timeout,
        )

        return self._normalize_completions(result)

    async def request_hover(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> lsp.Hover | None:
        """Request hover at position."""
        uri = await self._ensure_open(file_path)

        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        }

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.HOVER,
            params,
            timeout=self.timeout,
        )

        return cast(lsp.Hover | None, result)

    async def request_document_symbols(
        self,
        file_path: str,
        uri: str | None = None,
    ) -> list[lsp.DocumentSymbol]:
        """Request document symbols.

        Args:
            file_path: Path to the file (used if uri not provided)
            uri: Optional file URI. If provided, skips _ensure_open.
        """
        if uri is None:
            uri = await self._ensure_open(file_path)

        params = {"textDocument": {"uri": uri}}

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.DOCUMENT_SYMBOL,
            params,
            timeout=self.timeout,
        )

        return result or []

    async def request_workspace_symbols(
        self,
        query: str,
    ) -> list[lsp.SymbolInformation]:
        """Request workspace symbols."""
        # Wait for workspace to be indexed before requesting symbols
        # This gives pyright time to scan and index all files in the workspace
        try:
            await asyncio.wait_for(
                self._workspace_indexed.wait(),
                timeout=_WORKSPACE_INDEX_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Workspace indexing timed out, proceeding anyway")

        params = {"query": query}

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.WORKSPACE_SYMBOL,
            params,
            timeout=self.timeout,
        )

        return result or []

    async def request_diagnostics(
        self,
        file_path: str,
        uri: str | None = None,
        mtime: float | None = None,
    ) -> list[dict[str, Any]]:
        """Request diagnostics for a single document.

        Uses textDocument/diagnostic LSP 3.17 method.
        Falls back to cached diagnostics from publishDiagnostics
        if the method is not supported.

        When cached diagnostics are valid (have resultId and mtime unchanged),
        returns cached diagnostics directly without server request.

        Args:
            file_path: Path to the file (used if uri not provided)
            uri: Optional file URI. If provided, skips _ensure_open.
            mtime: Optional file modification time for staleness check.

        Returns:
            List of diagnostic dictionaries.
        """
        if uri is None:
            uri = await self._ensure_open(file_path)

        file_state = await self._diagnostic_cache.get_file_state(uri)

        # Optimization: Skip server request if cache is valid
        # Cache is valid when:
        # 1. We have a resultId (previous server response with diagnostics)
        # 2. mtime indicates file hasn't changed (if mtime provided)
        if file_state.last_result_id is not None and mtime is not None:
            is_stale = await self._diagnostic_cache.is_stale(uri, mtime)
            if not is_stale:
                # Structured cache hit log with FileState info
                self._log_cache_hit(uri, file_state, mtime)
                return list(file_state.diagnostics)

        params: lsp.DocumentDiagnosticParams = {
            "textDocument": {"uri": uri},
            "previousResultId": file_state.last_result_id,
        }

        assert self._transport is not None
        try:
            result = await self._transport.send_request(
                LSPConstants.DIAGNOSTIC,
                params,  # type: ignore[arg-type]
                timeout=self.timeout,
            )
            diagnostics, result_id = self._normalize_document_diagnostics(result)
            await self._diagnostic_cache.update_diagnostics(uri, diagnostics, result_id)
            # Update mtime after successful refresh
            if mtime is not None:
                await self._diagnostic_cache.set_mtime(uri, mtime)
            return diagnostics
        except Exception as e:
            logger.warning(f"textDocument/diagnostic failed: {e}, using cached")
            # Fallback to cached diagnostics from notifications
            return await self._diagnostic_cache.get_diagnostics(uri)

    def _normalize_document_diagnostics(
        self,
        result: Any,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Normalize document diagnostic response.

        Args:
            result: Raw diagnostic response from LSP server.

        Returns:
            A tuple containing:
            - List of diagnostic dictionaries (may be empty)
            - result_id string if present in response, otherwise None

        Note:
            For "unchanged" responses, returns cached diagnostics with None result_id.
            Returns ([], None) for None or unrecognized result types.
            Returns raw dicts from LSP server, typed as dict[str, Any]
            since LSP servers may return slightly different structures.
        """
        if result is None:
            return ([], None)

        if isinstance(result, dict):
            if result.get("kind") == "unchanged":
                uri = result.get("uri", "")
                file_state = self._diagnostic_cache.get_file_state_sync(uri)
                self._log_cache_hit_server(uri, file_state, result.get("resultId"))
                return (self._diagnostic_cache.get_cached(uri), None)
            items = result.get("items", [])
            result_id = result.get("resultId")
            logger.debug(f"[← res textDocument/diagnostic] fresh: {len(items)} diagnostics")
            return (list(items), result_id)

        if isinstance(result, list):
            logger.debug(f"[← res textDocument/diagnostic] fresh: {len(result)} diagnostics")
            return (list(result), None)

        return ([], None)

    def _log_cache_hit(
        self,
        uri: str,
        file_state: Any,
        current_mtime: float,
    ) -> None:
        """Log a cache hit with structured FileState information.

        Args:
            uri: File URI
            file_state: FileState object from cache
            current_mtime: Current file modification time
        """
        # Extract relative path for cleaner log output
        rel_path = self._uri_to_relative_path(uri)
        diag_count = len(file_state.diagnostics)

        logger.info(
            f"[cache HIT] {rel_path} | "
            f"resultId={file_state.last_result_id[:8] if file_state.last_result_id else 'None'}... "
            f"| mtime={current_mtime:.2f} | v={file_state.document_version} | "
            f"open={file_state.is_open} | diags={diag_count}"
        )

    def _log_cache_hit_server(
        self,
        uri: str,
        file_state: Any,
        result_id: str | None,
    ) -> None:
        """Log a server-reported cache hit (kind=unchanged).

        Args:
            uri: File URI
            file_state: FileState object from cache
            result_id: Result ID from server response
        """
        rel_path = self._uri_to_relative_path(uri)
        diag_count = len(file_state.diagnostics)

        logger.info(
            f"[← res textDocument/diagnostic] cache HIT (unchanged) {rel_path} | "
            f"resultId={result_id[:8] if result_id else 'None'}... | "
            f"diags={diag_count}"
        )

    def _uri_to_relative_path(self, uri: str) -> str:
        """Convert URI to relative path for cleaner log output.

        Delegates to the shared utility function.

        Args:
            uri: File URI

        Returns:
            Relative path string within workspace
        """
        from llm_lsp_cli.utils.uri import uri_to_relative_path

        # Handle case where workspace_path is not set (mock clients in tests)
        if not hasattr(self, "workspace_path") or self.workspace_path is None:
            from urllib.parse import urlparse

            parsed = urlparse(uri)
            if parsed.scheme != "file":
                return uri
            return parsed.path

        return uri_to_relative_path(uri, self.workspace_path)

    async def request_workspace_diagnostics(
        self,
    ) -> list[lsp.WorkspaceDiagnosticItem]:
        """Request diagnostics for entire workspace.

        Uses workspace/diagnostic LSP 3.17 method.
        Waits for workspace indexing before requesting.

        Returns:
            List of WorkspaceDiagnosticItem objects
        """
        # Wait for workspace to be indexed
        try:
            await asyncio.wait_for(
                self._workspace_indexed.wait(),
                timeout=_WORKSPACE_DIAGNOSTIC_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Workspace indexing timed out, diagnostics may be incomplete")

        # Return cached diagnostics from unified cache
        return await self._diagnostic_cache.get_all_workspace_diagnostics()

    def _handle_configuration_request(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle workspace/configuration request from server.

        Returns configuration values for requested sections.
        """
        items = params.get("items", [])
        results: list[dict[str, str]] = []

        for item in items:
            section = item.get("section", "")
            if not section:
                results.append({})
            else:
                # Return workspace diagnostic mode for analysis sections
                results.append({"diagnosticMode": "workspace"})

        return results

    def _handle_work_done_progress_create_request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle window/workDoneProgress/create request from server.

        The server requests permission to create a work done progress tracker.
        We grant it by returning an empty response.
        """
        token = params.get("token", "unknown")
        logger.debug(f"Work done progress created with token: {token}")
        return {}

    async def _ensure_open(self, file_path: str) -> str:
        """Ensure file is open in LSP server.

        Waits for the server to process the document (signaled by diagnostics)
        before returning. This prevents race conditions where requests are sent
        before the server has finished parsing the document.
        """
        # Resolve relative paths relative to workspace path
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_path / path
        path = path.resolve()
        uri = path.as_uri()

        if uri not in self._open_files:
            content = path.read_text()
            version = 0
            ready_event = asyncio.Event()
            self._open_files[uri] = (content, version, ready_event)

            assert self._transport is not None
            await self._transport.send_notification(
                LSPConstants.TEXT_DOCUMENT_DID_OPEN,
                {
                    "textDocument": {
                        "uri": uri,
                        "languageId": self.language_id,
                        "version": version,
                        "text": content,
                    }
                },
            )

            # Wait for server to process document
            # Using simple sleep like the working test script
            await asyncio.sleep(_DOCUMENT_READY_WAIT)

        return uri

    async def open_document(self, file_path: Path, content: str) -> str:
        """
        Send textDocument/didOpen notification.

        Args:
            file_path: Path to the file
            content: File content to send

        Returns:
            File URI
        """
        uri = file_path.as_uri()
        assert self._transport is not None
        await self._transport.send_notification(
            LSPConstants.TEXT_DOCUMENT_DID_OPEN,
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": self.language_id,
                    "version": 1,
                    "text": content,
                }
            },
        )
        return uri

    async def close_document(self, uri: str) -> None:
        """
        Send textDocument/didClose notification.

        Args:
            uri: File URI to close
        """
        assert self._transport is not None
        await self._transport.send_notification(
            LSPConstants.TEXT_DOCUMENT_DID_CLOSE,
            {"textDocument": {"uri": uri}},
        )

    async def send_did_change(self, file_path: Path, content: str) -> str:
        """
        Send textDocument/didChange notification with full text sync.

        This method sends the file's current content to the LSP server.
        It increments the document version in the cache.

        Args:
            file_path: Path to the file
            content: Current file content

        Returns:
            File URI
        """
        uri = file_path.as_uri()

        # Increment version for this change
        await self._diagnostic_cache.increment_version(uri)
        state = await self._diagnostic_cache.get_file_state(uri)
        version = state.document_version

        assert self._transport is not None
        await self._transport.send_notification(
            LSPConstants.TEXT_DOCUMENT_DID_CHANGE,
            {
                "textDocument": {
                    "uri": uri,
                    "version": version,
                },
                "contentChanges": [
                    {"text": content}
                ],
            },
        )
        return uri

    def _normalize_locations(self, result: Any) -> list[lsp.Location]:
        """Normalize definition/references response to Location[]."""
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return cast(list[lsp.Location], [result])
        return []

    def _normalize_completions(self, result: Any) -> list[lsp.CompletionItem]:
        """Normalize completion response."""
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return cast(list[lsp.CompletionItem], result.get("items", []))
        return []

    def _handle_log_message(self, params: dict[str, Any]) -> None:
        """Handle window/logMessage notification."""
        logger.info(f"LSP: {params.get('message', '')}")

    def _handle_diagnostics(self, params: dict[str, Any]) -> None:
        """Handle textDocument/publishDiagnostics notification.

        Caches diagnostics for fallback and signals document readiness.
        """
        uri = params.get("uri", "")
        diagnostics = params.get("diagnostics", [])

        # Cache diagnostics using unified DiagnosticCache
        # Create task but don't await - this is a notification handler
        asyncio.create_task(self._diagnostic_cache.update_diagnostics(uri, diagnostics))

        if uri in self._open_files:
            _, _, ready_event = self._open_files[uri]
            if not ready_event.is_set():
                logger.debug(f"Document ready: {uri}")
                ready_event.set()

    def _handle_progress(self, params: dict[str, Any]) -> None:
        """Handle $/progress notification."""
        token = params.get("token", "")

        # Check if this is workspace diagnostic progress (token-based routing)
        ws_token = self._workspace_diagnostic_token
        if ws_token is not None and token == ws_token:
            self._handle_workspace_diagnostic_progress(params)
            return

        # Delegate to progress handler for other work done progress
        self._progress_handler.handle_progress(params)

        # Also log progress updates for visibility
        value = params.get("value", {})
        if isinstance(value, dict):
            message = value.get("message", "")
            if message:
                logger.debug(f"Progress [{token}]: {message}")

    async def request_call_hierarchy_incoming(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> list[dict[str, Any]]:
        """Request incoming calls at position.

        Follows the two-step call hierarchy protocol:
        1. Call prepareCallHierarchy to get items at position
        2. Call callHierarchy/incomingCalls for each item

        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)

        Returns:
            List of CallHierarchyIncomingCall dictionaries, or empty list
        """
        uri = await self._ensure_open(file_path)

        # Step 1: Prepare call hierarchy
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        }

        assert self._transport is not None
        prepare_result = await self._transport.send_request(
            LSPConstants.PREPARE_CALL_HIERARCHY,
            params,
            timeout=self.timeout,
        )

        # Handle null or empty prepare result
        items = self._normalize_call_hierarchy_items(prepare_result)
        if not items:
            return []

        # Step 2: Request incoming calls for each item
        # Use the first item (most relevant at position)
        item = items[0]
        incoming_params: dict[str, Any] = {"item": item}

        try:
            result = await self._transport.send_request(
                LSPConstants.CALL_HIERARCHY_INCOMING_CALLS,
                incoming_params,
                timeout=self.timeout,
            )
            return self._normalize_call_hierarchy_calls(result, is_incoming=True)
        except Exception as e:
            # Check for MethodNotFound error
            if self._is_method_not_found_error(e):
                logger.warning("callHierarchy/incomingCalls not supported by server")
                return []
            raise

    async def request_call_hierarchy_outgoing(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> list[dict[str, Any]]:
        """Request outgoing calls at position.

        Follows the two-step call hierarchy protocol:
        1. Call prepareCallHierarchy to get items at position
        2. Call callHierarchy/outgoingCalls for each item

        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)

        Returns:
            List of CallHierarchyOutgoingCall dictionaries, or empty list
        """
        uri = await self._ensure_open(file_path)

        # Step 1: Prepare call hierarchy
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        }

        assert self._transport is not None
        prepare_result = await self._transport.send_request(
            LSPConstants.PREPARE_CALL_HIERARCHY,
            params,
            timeout=self.timeout,
        )

        # Handle null or empty prepare result
        items = self._normalize_call_hierarchy_items(prepare_result)
        if not items:
            return []

        # Step 2: Request outgoing calls for each item
        # Use the first item (most relevant at position)
        item = items[0]
        outgoing_params: dict[str, Any] = {"item": item}

        try:
            result = await self._transport.send_request(
                LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS,
                outgoing_params,
                timeout=self.timeout,
            )
            return self._normalize_call_hierarchy_calls(result, is_incoming=False)
        except Exception as e:
            # Check for MethodNotFound error
            if self._is_method_not_found_error(e):
                logger.warning("callHierarchy/outgoingCalls not supported by server")
                return []
            raise

    def _normalize_call_hierarchy_items(self, result: Any) -> list[dict[str, Any]]:
        """Normalize prepareCallHierarchy response to list of items.

        Args:
            result: Raw response from prepareCallHierarchy

        Returns:
            List of CallHierarchyItem dictionaries
        """
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "items" in result:
            items = result.get("items")
            if items is None:
                return []
            return items if isinstance(items, list) else []
        return []

    def _normalize_call_hierarchy_calls(
        self,
        result: Any,
        is_incoming: bool,
    ) -> list[dict[str, Any]]:
        """Normalize incomingCalls/outgoingCalls response.

        Converts LSP 'from' field to Python 'from_' for incoming calls.

        Args:
            result: Raw response from incomingCalls/outgoingCalls
            is_incoming: True for incoming calls, False for outgoing

        Returns:
            List of call dictionaries with normalized field names
        """
        if result is None:
            return []
        if isinstance(result, list):
            calls = result
        elif isinstance(result, dict) and "calls" in result:
            calls_result = result.get("calls")
            if calls_result is None:
                return []
            calls = calls_result if isinstance(calls_result, list) else []
        else:
            return []

        # Normalize 'from' -> 'from_' for incoming calls
        if is_incoming:
            normalized_calls = []
            for call in calls:
                normalized_call = dict(call)
                if "from" in call:
                    normalized_call["from_"] = call["from"]
                    del normalized_call["from"]
                normalized_calls.append(normalized_call)
            return normalized_calls

        return calls

    async def request_prepare_rename(
        self,
        file_path: str,
        line: int,
        column: int,
    ) -> dict[str, Any] | None:
        """Request prepareRename at position.

        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)

        Returns:
            Range or placeholder dict if rename is valid, None otherwise
        """
        uri = await self._ensure_open(file_path)

        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        }

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.PREPARE_RENAME,
            params,
            timeout=self.timeout,
        )

        return cast(dict[str, Any] | None, result)

    async def request_rename(
        self,
        file_path: str,
        line: int,
        column: int,
        new_name: str,
    ) -> dict[str, Any] | None:
        """Request rename at position.

        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)
            new_name: New name for the symbol

        Returns:
            WorkspaceEdit dict with changes, or None if no changes
        """
        uri = await self._ensure_open(file_path)

        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
            "newName": new_name,
        }

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.RENAME,
            params,
            timeout=self.timeout,
        )

        return cast(dict[str, Any] | None, result)

    def _is_method_not_found_error(self, error: Any) -> bool:
        """Check if error is a MethodNotFound (-32601) error.

        Args:
            error: Exception or error response

        Returns:
            True if error indicates method not found
        """
        # Check for LSPError from transport
        if isinstance(error, LSPError):
            return bool(error.code == LSPConstants.ERROR_METHOD_NOT_FOUND)

        # Check for error response dict
        if isinstance(error, dict):
            error_info = error.get("error", {})
            return bool(error_info.get("code") == LSPConstants.ERROR_METHOD_NOT_FOUND)

        # Check for exception with error response
        if hasattr(error, "response"):
            response = getattr(error, "response", {})
            error_info = response.get("error", {})
            return bool(error_info.get("code") == LSPConstants.ERROR_METHOD_NOT_FOUND)

        return False
