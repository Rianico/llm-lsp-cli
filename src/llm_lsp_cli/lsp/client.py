"""LSP client implementation."""

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import Any, cast

from llm_lsp_cli.config import ConfigManager

from . import types as lsp
from .constants import LSPConstants
from .transport import StdioTransport

logger = logging.getLogger(__name__)


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
        await asyncio.sleep(2.0)  # Wait 2 seconds for initial indexing
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
            await asyncio.wait_for(self._workspace_indexed.wait(), timeout=10.0)
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
    ) -> list[lsp.Diagnostic]:
        """Request diagnostics for a single document.

        Uses textDocument/diagnostic LSP 3.17 method.
        Falls back to cached diagnostics from publishDiagnostics
        if the method is not supported.

        Args:
            file_path: Path to the file

        Returns:
            List of Diagnostic objects
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
            return self._diagnostic_cache.get(uri, [])

    def _normalize_document_diagnostics(
        self,
        result: Any,
    ) -> list[lsp.Diagnostic]:
        """Normalize document diagnostic response."""
        if result is None:
            return []

        if isinstance(result, dict):
            # Handle DocumentDiagnosticReport format
            if result.get("kind") == "unchanged":
                # No changes since last request - return cached
                return self._diagnostic_cache.get(
                    result.get("uri", ""), []
                )
            items = result.get("items", [])
            return items

        if isinstance(result, list):
            return result

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
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Workspace indexing timed out, "
                "diagnostics may be incomplete"
            )

        params: dict[str, Any] = {}

        assert self._transport is not None
        result = await self._transport.send_request(
            LSPConstants.WORKSPACE_DIAGNOSTIC,
            params,
            timeout=60.0,  # Longer timeout for workspace
        )

        return self._normalize_workspace_diagnostics(result)

    def _normalize_workspace_diagnostics(
        self,
        result: Any,
    ) -> list[lsp.WorkspaceDiagnosticItem]:
        """Normalize workspace diagnostic response."""
        if result is None:
            return []

        if isinstance(result, dict):
            items = result.get("items", [])
            return items

        if isinstance(result, list):
            return result

        return []

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
            await asyncio.sleep(2.0)  # Increased to 2 seconds for pyright to parse

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
        # Log progress updates for visibility
        token = params.get("token", "")
        value = params.get("value", {})
        if isinstance(value, dict):
            message = value.get("message", "")
            if message:
                logger.debug(f"Progress [{token}]: {message}")
