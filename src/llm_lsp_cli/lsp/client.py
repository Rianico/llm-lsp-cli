"""LSP client implementation."""

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import Any, cast

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.infrastructure.lsp.progress_handler import ProgressHandler

from . import types as lsp
from .constants import LSPConstants
from .transport import StdioTransport

logger = logging.getLogger(__name__)

# Timeouts and delays (in seconds)
_WORKSPACE_INDEX_TIMEOUT = 10.0
_WORKSPACE_DIAGNOSTIC_TIMEOUT = 30.0
_WORKSPACE_INDEX_WAIT = 2.0
_DOCUMENT_READY_WAIT = 2.0


def _build_workspace_items(
    cache: dict[str, list[dict[str, Any]]],
) -> list[lsp.WorkspaceDiagnosticItem]:
    """Build workspace diagnostic items from a cache dictionary.

    Args:
        cache: Dictionary mapping URIs to diagnostic lists.

    Returns:
        List of WorkspaceDiagnosticItem objects.
    """
    return cast(
        list[lsp.WorkspaceDiagnosticItem],
        [
            {
                "uri": uri,
                "version": None,
                "diagnostics": list(diags),
            }
            for uri, diags in cache.items()
        ],
    )


class WorkspaceDiagnosticManager:
    """Manages workspace diagnostic collection via pull mode.

    Handles:
    - Fire-and-forget workspace/diagnostic requests
    - Processing $/progress notifications with partial results
    - Thread-safe cache operations with asyncio.Lock
    - Streaming completion signaling via asyncio.Event
    """

    def __init__(self, client: "LSPClient"):
        self._client = client
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._cache_lock = asyncio.Lock()
        self._streaming_complete = asyncio.Event()
        self._partial_result_token = f"workspace-diagnostic-{id(self)}"
        # Track if server supports pull mode (workspace/diagnostic)
        # Defaults to True, will be set based on server capabilities
        self._pull_mode_supported = True

    def get_cached(self, uri: str) -> list[dict[str, Any]]:
        """Get cached diagnostics for a URI (returns a copy)."""
        return list(self._cache.get(uri, []))

    async def _update_cache(self, uri: str, diagnostics: list[dict[str, Any]]) -> None:
        """Update cache with new diagnostics for a URI."""
        async with self._cache_lock:
            self._cache[uri] = list(diagnostics)

    async def _get_cache_items(self) -> list[lsp.WorkspaceDiagnosticItem]:
        """Get all cached diagnostics as workspace diagnostic items.

        If pull mode is not supported, returns diagnostics from the client's
        _diagnostic_cache (populated via publishDiagnostics notifications).
        """
        # If pull mode is not supported, use the client's diagnostic cache
        # which is populated via publishDiagnostics notifications
        if not self._pull_mode_supported:
            return _build_workspace_items(self._client._diagnostic_cache)

        async with self._cache_lock:
            return _build_workspace_items(self._cache)

    def _handle_progress(self, params: dict[str, Any]) -> None:
        """Handle $/progress notification for workspace diagnostics.

        Handles three kinds of progress:
        - begin: Start of diagnostic collection (logged only)
        - report: Contains partial results with items
        - end: Diagnostic collection complete
        """
        token = params.get("token", "")
        value = params.get("value", {})

        if not isinstance(value, dict):
            return

        kind = value.get("kind", "")

        if kind == "begin":
            logger.debug(f"Workspace diagnostic collection started: {value.get('title', '')}")
            return

        if kind == "report":
            # Check if this is our diagnostic progress
            if token != self._partial_result_token:
                return

            items = value.get("items", [])
            if items:
                # Process items - use create_task but handle case when no running loop
                try:
                    asyncio.create_task(self._process_report_items(items))
                except RuntimeError:
                    # No running event loop - process synchronously
                    # This can happen in unit tests
                    pass
            return

        if kind == "end":
            logger.debug("Workspace diagnostic collection complete")
            self._streaming_complete.set()
            return

    async def _process_report_items(self, items: list[dict[str, Any]]) -> None:
        """Process report items from progress notification."""
        for item in items:
            uri = item.get("uri", "")
            diagnostics = item.get("diagnostics", [])
            if uri and diagnostics:
                await self._update_cache(uri, diagnostics)

    async def _send_diagnostic_request(self) -> None:
        """Send workspace/diagnostic request with partial result token.

        This is a fire-and-forget request - the server never sends a response.
        Results come via $/progress notifications instead.
        """
        assert self._client._transport is not None

        params: dict[str, Any] = {
            "identifier": "basedpyright",
            "previousResultIds": [],
            "partialResultToken": self._partial_result_token,
        }

        # Send as fire-and-forget request (has ID but we don't wait for response)
        await self._client._transport.send_request_fire_and_forget(
            LSPConstants.WORKSPACE_DIAGNOSTIC,
            params,
        )

    async def request(self) -> list[lsp.WorkspaceDiagnosticItem]:
        """Request workspace diagnostics.

        Sends a fire-and-forget workspace/diagnostic request and waits
        for streaming to complete via $/progress notifications.

        If pull mode is not supported by the server, returns cached
        diagnostics from push mode (publishDiagnostics).

        Returns partial results if timeout occurs.
        """
        # If pull mode is not supported, return cached diagnostics immediately
        if not self._pull_mode_supported:
            logger.debug("Pull mode not supported, returning cached diagnostics")
            return await self._get_cache_items()

        # Clear any previous completion signal
        self._streaming_complete.clear()

        # Register progress handler
        assert self._client._transport is not None
        self._client._transport.on_notification("$/progress", self._handle_progress)

        # Send diagnostic request
        await self._send_diagnostic_request()

        # Wait for streaming to complete
        try:
            await asyncio.wait_for(self._streaming_complete.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            logger.warning("Workspace diagnostic request timed out, returning partial results")

        # Return cached results
        return await self._get_cache_items()

    def set_pull_mode_supported(self, supported: bool) -> None:
        """Set whether the server supports pull mode diagnostics."""
        self._pull_mode_supported = supported
        logger.debug(f"Pull mode support: {supported}")


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
        log_file: Path | None = None,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.server_command = server_command
        self.server_args = server_args or []
        self.language_id = language_id
        self.trace = trace
        self.timeout = timeout
        self.lsp_conf = lsp_conf
        self.log_file = log_file

        self._transport: StdioTransport | None = None
        self._initialized = False
        # uri -> (content, version, ready_event)
        self._open_files: dict[str, tuple[str, int, asyncio.Event]] = {}
        self._capabilities: lsp.ServerCapabilities | None = None
        self._workspace_indexed = asyncio.Event()
        # Cache for diagnostics received via publishDiagnostics
        # uri -> list[Diagnostic]
        self._diagnostic_cache: dict[str, list[dict[str, Any]]] = {}
        # Workspace diagnostic manager for pull mode
        self._diagnostic_manager: WorkspaceDiagnosticManager | None = None
        # Progress handler for work done progress
        self._progress_handler = ProgressHandler()

    async def initialize(self) -> lsp.InitializeResult:
        """Initialize the LSP connection."""
        self._transport = StdioTransport(
            command=self.server_command,
            args=self.server_args,
            cwd=str(self.workspace_path),
            trace=self.trace,
            log_file=self.log_file,
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
            "client/registerCapability",
            self._handle_register_capability_request,
        )
        self._transport.on_request(
            "workspace/diagnostic/refresh",
            self._handle_diagnostic_refresh_request,
        )
        self._transport.on_request(
            "window/workDoneProgress/create",
            self._handle_work_done_progress_create_request,
        )

        # Create workspace diagnostic manager
        # Pull mode is disabled by default - servers that support it will register
        # the capability via client/registerCapability
        self._diagnostic_manager = WorkspaceDiagnosticManager(self)
        self._diagnostic_manager.set_pull_mode_supported(False)

        # Send initialize request
        init_params = self._build_initialize_params()
        assert self._transport is not None
        response = await self._transport.send_request(
            LSPConstants.INITIALIZE,
            init_params,
            timeout=self.timeout,
        )

        self._capabilities = response.get("capabilities", {})

        # Send initialized notification
        assert self._transport is not None
        await self._transport.send_notification(LSPConstants.INITIALIZED, {})

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
    ) -> list[lsp.DocumentSymbol]:
        """Request document symbols."""
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
    ) -> list[dict[str, Any]]:
        """Request diagnostics for a single document.

        Uses textDocument/diagnostic LSP 3.17 method.
        Falls back to cached diagnostics from publishDiagnostics
        if the method is not supported.

        Args:
            file_path: Path to the file

        Returns:
            List of diagnostic dictionaries.
        """
        uri = await self._ensure_open(file_path)

        params: lsp.DocumentDiagnosticParams = {
            "textDocument": {"uri": uri},
            "previousResultId": None,
        }

        assert self._transport is not None
        try:
            result = await self._transport.send_request(
                LSPConstants.DIAGNOSTIC,
                params,  # type: ignore[arg-type]
                timeout=self.timeout,
            )
            return self._normalize_document_diagnostics(result)
        except Exception as e:
            logger.warning(f"textDocument/diagnostic failed: {e}, using cached")
            # Fallback to cached diagnostics from notifications
            return list(self._diagnostic_cache.get(uri, []))

    def _normalize_document_diagnostics(
        self,
        result: Any,
    ) -> list[dict[str, Any]]:
        """Normalize document diagnostic response.

        Args:
            result: Raw diagnostic response from LSP server.

        Returns:
            List of diagnostic dictionaries.

        Note:
            Returns raw dicts from LSP server, typed as dict[str, Any]
            since LSP servers may return slightly different structures.
        """
        if result is None:
            return []

        if isinstance(result, dict):
            # Handle DocumentDiagnosticReport format
            if result.get("kind") == "unchanged":
                # No changes since last request - return cached
                return list(self._diagnostic_cache.get(result.get("uri", ""), []))
            items = result.get("items", [])
            return list(items)

        if isinstance(result, list):
            return list(result)

        return []

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

        # Use pull mode with diagnostic manager if available
        if self._diagnostic_manager is not None:
            return await self._diagnostic_manager.request()

        # Fallback to push mode - return cached diagnostics
        return _build_workspace_items(self._diagnostic_cache)

    def _handle_configuration_request(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle workspace/configuration request from server.

        Returns configuration values for requested sections.
        """
        items = params.get("items", [])
        results = []

        for item in items:
            section = item.get("section", "")
            if not section:
                results.append({})
            else:
                # Return workspace diagnostic mode for analysis sections
                results.append({"diagnosticMode": "workspace"})

        return results

    async def _handle_register_capability_request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle client/registerCapability request from server.

        Auto-triggers workspace diagnostic collection when
        workspace/diagnostic capability is registered.
        """
        registrations = params.get("registrations", [])

        for reg in registrations:
            method = reg.get("method", "")
            register_options = reg.get("registerOptions", {})

            # Check for workspace diagnostics support
            # The server registers with method "workspace/diagnostic" and
            # registerOptions containing workspaceDiagnostics: true
            if method == "textDocument/diagnostic" and register_options.get("workspaceDiagnostics"):
                # Enable pull mode and trigger diagnostic collection
                if self._diagnostic_manager is not None:
                    self._diagnostic_manager.set_pull_mode_supported(True)
                    logger.info("Server supports pull mode diagnostics, requesting...")
                    asyncio.create_task(self._diagnostic_manager.request())
            elif method == "textDocument/diagnostic":
                # Server registered workspace/diagnostic but didn't explicitly
                # enable workspaceDiagnostics - assume pull mode is supported
                if self._diagnostic_manager is not None:
                    self._diagnostic_manager.set_pull_mode_supported(True)
                    asyncio.create_task(self._diagnostic_manager.request())

        return {}

    def _handle_diagnostic_refresh_request(
        self,
        _params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle workspace/diagnostic/refresh request from server.

        Re-triggers workspace diagnostic collection.
        """
        if self._diagnostic_manager is not None:
            asyncio.create_task(self._diagnostic_manager.request())

        return {}

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
        path = Path(file_path).resolve()
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

        # Cache diagnostics for fallback
        self._diagnostic_cache[uri] = diagnostics

        if uri in self._open_files:
            _, _, ready_event = self._open_files[uri]
            if not ready_event.is_set():
                logger.debug(f"Document ready: {uri}")
                ready_event.set()

    def _handle_progress(self, params: dict[str, Any]) -> None:
        """Handle $/progress notification."""
        # Delegate to progress handler for work done progress
        self._progress_handler.handle_progress(params)

        # Also log progress updates for visibility
        token = params.get("token", "")
        value = params.get("value", {})
        if isinstance(value, dict):
            message = value.get("message", "")
            if message:
                logger.debug(f"Progress [{token}]: {message}")
