"""Daemon process management for llm-lsp-cli."""

import asyncio
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any

from daemon import DaemonContext
from daemon.pidfile import PIDLockFile as PidFile

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.domain.services import LspMethodRouter
from llm_lsp_cli.ipc import UNIXServer
from llm_lsp_cli.lsp.constants import LSPConstants
from llm_lsp_cli.server import ServerRegistry

# Constants
_SHUTDOWN_WAIT_ITERATIONS = 50  # 5 seconds max (50 * 0.1s)
_SHUTDOWN_POLL_INTERVAL = 0.1  # 100ms between process checks
_DAEMON_UMASK = 0o077  # Restrictive permissions (owner only)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm-lsp-cli.daemon")


def _configure_diagnostic_logger(log_path: Path) -> None:
    """Configure the diagnostic logger with a FileHandler.

    Args:
        log_path: Path to the diagnostics.log file

    This configures the 'llm_lsp_cli.lsp.diagnostic' logger to:
    - Write to the specified file with DEBUG level
    - Have propagate=False to prevent double-logging
    - Use restrictive file permissions (0o600)
    """
    import os

    # Ensure parent directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file handler
    handler = logging.FileHandler(str(log_path), mode="a")
    handler.setLevel(logging.DEBUG)

    # Configure diagnostic logger
    diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
    diagnostic_logger.addHandler(handler)
    diagnostic_logger.setLevel(logging.DEBUG)
    diagnostic_logger.propagate = False

    # Set restrictive file permissions (owner read/write only)
    try:
        os.chmod(log_path, 0o600)
    except OSError:
        logger.warning(f"Could not set restrictive permissions on {log_path}")


def _configure_logger_levels(trace: bool = False) -> None:
    """Configure logger levels for debug/trace mode.

    Args:
        trace: If True, enable TRACE_LEVEL for transport logger.
    """
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("llm-lsp-cli").setLevel(logging.DEBUG)
    logging.getLogger("llm_lsp_cli").setLevel(logging.DEBUG)
    logging.getLogger("llm_lsp_cli.lsp").setLevel(logging.DEBUG)
    if trace:
        from llm_lsp_cli.lsp.transport import TRACE_LEVEL

        logging.getLogger("llm_lsp_cli.lsp.transport").setLevel(TRACE_LEVEL)


def cleanup_runtime_files(
    socket_path: Path,
    pid_file: Path,
    workspace: str,
    language: str,
) -> None:
    """Clean up daemon runtime files (socket and PID).

    Args:
        socket_path: Path to the UNIX socket file
        pid_file: Path to the PID lock file
        workspace: Workspace name for logging
        language: Language name for logging

    This function is idempotent - safe to call multiple times.
    """
    logger.info(f"[CLEANUP] Cleaning runtime files: workspace={workspace}, language={language}")

    # Remove socket file
    if socket_path.exists():
        try:
            socket_path.unlink()
            logger.debug(f"[CLEANUP] Removed socket: {socket_path}")
        except OSError as e:
            logger.error(f"[CLEANUP] Failed to remove socket: {e}")
    else:
        logger.debug("[CLEANUP] Socket already absent")

    # Remove PID file
    if pid_file.exists():
        try:
            pid_file.unlink()
            logger.debug(f"[CLEANUP] Removed PID file: {pid_file}")
        except OSError as e:
            logger.error(f"[CLEANUP] Failed to remove PID file: {e}")
    else:
        logger.debug("[CLEANUP] PID file already absent")

    logger.info("[CLEANUP] Cleanup complete")


class DaemonManager:
    """Manages the daemon process lifecycle for a specific workspace and language."""

    def __init__(
        self,
        workspace_path: str,
        language: str = "python",
        lsp_conf: str | None = None,
        debug: bool = False,
        trace: bool = False,
    ):
        self.workspace_path = workspace_path
        self.language = language
        self.lsp_conf = lsp_conf
        self.debug = debug
        self.trace = trace
        # Resolve server name for file naming
        self._lsp_server_name = ConfigManager.get_lsp_server_name(language)
        self.pid_file = ConfigManager.build_pid_file_path(
            workspace_path, language, lsp_server_name=self._lsp_server_name
        )
        self.socket_path = ConfigManager.build_socket_path(
            workspace_path, language, lsp_server_name=self._lsp_server_name
        )
        self.daemon_log_file = ConfigManager.build_daemon_log_path(workspace_path, language)

    def is_running(self) -> bool:
        """Check if daemon is running."""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return True
        except (ValueError, OSError):
            # PID file exists but process not running
            self.pid_file.unlink(missing_ok=True)
            return False

    def get_pid(self) -> int | None:
        """Get daemon PID if running."""
        if not self.pid_file.exists():
            return None

        try:
            return int(self.pid_file.read_text().strip())
        except ValueError:
            return None

    def _cleanup_files(self) -> None:
        """Clean up daemon runtime files (PID and socket).

        Delegates to cleanup_runtime_files for consistent cleanup behavior.
        """
        cleanup_runtime_files(
            socket_path=self.socket_path,
            pid_file=self.pid_file,
            workspace=Path(self.workspace_path).name,
            language=self.language,
        )

    def _wait_for_process_stop(self, pid: int) -> None:
        """Wait for daemon process to stop, force kill if timeout.

        Args:
            pid: Process ID to wait for
        """
        for _ in range(_SHUTDOWN_WAIT_ITERATIONS):
            try:
                os.kill(pid, 0)
                time.sleep(_SHUTDOWN_POLL_INTERVAL)
            except OSError:
                # Process stopped
                break
        else:
            # Force kill if still running after timeout
            os.kill(pid, signal.SIGKILL)
            logger.info(f"Sent SIGKILL to daemon (PID: {pid})")

    def start(self, diagnostic_log: bool = False) -> None:
        """Start the daemon process in background.

        Args:
            diagnostic_log: If True, configure diagnostic logger to write to diagnostics.log
        """
        if self.is_running():
            raise RuntimeError("Daemon is already running")

        # Validate socket path length (UNIX socket limit is 108 characters)
        # macOS has a lower limit, so we use 100 as a safe maximum
        socket_path_str = str(self.socket_path)
        if len(socket_path_str) >= 100:
            raise RuntimeError(
                f"Socket path too long ({len(socket_path_str)} chars, max ~100): "
                f"{socket_path_str}\n"
                f"Try using a shorter workspace path or set TMPDIR to a shorter path."
            )

        # Ensure directories exist
        ConfigManager.ensure_runtime_dir()
        ConfigManager.ensure_state_dir()
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.daemon_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Start daemon context with exception wrapper
        # This ensures exceptions are logged before the daemon process exits
        try:
            with DaemonContext(
                pidfile=PidFile(str(self.pid_file)),
                stdout=open(self.daemon_log_file, "a"),
                stderr=open(self.daemon_log_file, "a"),
                umask=_DAEMON_UMASK,
            ):
                logger.info("Daemon starting...")
                asyncio.run(
                    run_daemon(
                        str(self.socket_path),
                        self.workspace_path,
                        self.language,
                        self.lsp_conf,
                        self.debug,
                        trace=self.trace,
                        pid_file=self.pid_file,
                        diagnostic_log=diagnostic_log,
                        diagnostic_log_path=ConfigManager.build_diagnostic_log_path(
                            self.workspace_path, self.language
                        ),
                    )
                )
        except Exception as e:
            # Log exception to daemon log file before re-raising
            # This ensures the error is captured even if daemon context swallows it
            logger.exception(f"Daemon startup failed: {e}")
            raise

    def stop(self) -> None:
        """Stop the daemon process."""
        if not self.is_running():
            logger.warning("[SIGNAL] Daemon is not running")
            self._cleanup_files()
            return

        pid = self.get_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"[SIGNAL] Sent SIGTERM to daemon (PID: {pid})")
                self._wait_for_process_stop(pid)
            except ProcessLookupError:
                logger.warning(f"[SIGNAL] Process {pid} not found (already stopped)")

        self._cleanup_files()


class DocumentSyncContext:
    """Async context manager for document synchronization within daemon.

    This context manager handles the didOpen phase for a single file.
    Per ADR-001, files remain open for the session lifetime:
    - didOpen is sent when entering the context
    - didClose is NOT sent when exiting (file stays open for session)
    - The file URI is returned for use in subsequent requests

    Usage:
        async with DocumentSyncContext(lsp_client, file_path) as uri:
            # Use uri for LSP requests
            result = await lsp_client.request_diagnostics(uri)
        # File remains open - no didClose sent
    """

    def __init__(self, lsp_client: Any, file_path: Path):
        """
        Initialize document sync context.

        Args:
            lsp_client: LSPClient instance
            file_path: Path to the file to synchronize
        """
        self.lsp_client = lsp_client
        self.file_path = file_path
        self.uri: str = ""

    async def __aenter__(self) -> str:
        """Open document and return URI if not already open.

        Per ADR-001, files remain open for the session lifetime.
        This method checks the DiagnosticCache to avoid sending redundant
        didOpen notifications when a file is already open.

        Returns:
            File URI for subsequent LSP requests
        """
        uri = self.file_path.as_uri()
        cache = self.lsp_client._diagnostic_cache
        state = await cache.get_file_state(uri)

        if not state.is_open:
            # File not yet open - send didOpen notification
            content = self.file_path.read_text(encoding="utf-8")
            self.uri = await self.lsp_client.open_document(self.file_path, content)
            # Mark file as open in cache
            await cache.on_did_open(uri)
        else:
            # File already open - skip didOpen, just return URI
            self.uri = uri

        return self.uri

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Exit context without closing document.

        Per ADR-001, files remain open for the session lifetime.
        No didClose is sent; the file stays open in the LSP server.
        """
        # No action - file stays open per ADR-001
        pass


class RequestHandler:
    """Handles incoming RPC requests."""

    # Response key for each method
    RESPONSE_KEYS: dict[str, str] = {
        LSPConstants.DEFINITION: "locations",
        LSPConstants.REFERENCES: "locations",
        LSPConstants.COMPLETION: "items",
        LSPConstants.HOVER: "hover",
        LSPConstants.DOCUMENT_SYMBOL: "symbols",
        LSPConstants.DIAGNOSTIC: "diagnostics",
        LSPConstants.WORKSPACE_SYMBOL: "symbols",
        LSPConstants.WORKSPACE_DIAGNOSTIC: "diagnostics",
        LSPConstants.CALL_HIERARCHY_INCOMING_CALLS: "calls",
        LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS: "calls",
    }

    # Default values for common params
    DEFAULTS: dict[str, Any] = {
        "workspace_path": ".",
        "file_path": None,
        "line": 0,
        "column": 0,
        "query": "",
    }

    def __init__(self, workspace_path: str, language: str, lsp_conf: str | None = None):
        self._shutdown = False
        self._workspace_path = workspace_path
        self._language = language
        self._lsp_conf = lsp_conf
        self._registry = ServerRegistry(lsp_conf=lsp_conf)
        self._router = LspMethodRouter()
        self._file_locks: dict[str, asyncio.Lock] = {}

    def _get_file_lock(self, file_path: Path) -> asyncio.Lock:
        """Get or create an asyncio.Lock for a specific file path.

        This ensures that concurrent requests for the same file are serialized
        to prevent interleaving of didOpen/didClose sequences.

        Args:
            file_path: Path to the file

        Returns:
            asyncio.Lock for the file path
        """
        path_str = str(file_path)
        if path_str not in self._file_locks:
            self._file_locks[path_str] = asyncio.Lock()
        return self._file_locks[path_str]

    async def handle(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Route request to appropriate handler."""
        logger.debug(f"Received request: {method} with params: {params}")

        if method == "ping":
            return {"status": "pong"}

        elif method == "shutdown":
            self._shutdown = True
            return {"status": "shutting_down"}

        elif method == "status":
            return {
                "running": True,
                "workspace": self._workspace_path,
                "language": self._language,
                "socket": str(
                    ConfigManager.build_socket_path(self._workspace_path, self._language)
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
        }:
            return await self._handle_lsp_method(method, params)

        # textDocument/didChange - external file change notification
        elif method == LSPConstants.TEXT_DOCUMENT_DID_CHANGE:
            return await self._handle_did_change(params)

        else:
            raise ValueError(f"Unknown method: {method}")

    async def _handle_lsp_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
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
        # (files stay open per ADR-001)
        requires_doc_sync = registry_method in {
            "request_diagnostics",
            "request_document_symbols",
        }

        if requires_doc_sync:
            # Extract file path from params
            file_path = params.get("filePath")
            if file_path is None:
                raise ValueError("Missing 'filePath' parameter")

            file_path_obj = Path(file_path)

            # Get workspace path for registry call
            workspace_path = params.get("workspacePath", ".")

            # Get workspace and ensure client is initialized
            workspace = await self._registry.get_or_create_workspace(workspace_path)
            client = await workspace.ensure_initialized()

            # Use per-file lock to serialize requests for the same file
            lock = self._get_file_lock(file_path_obj)
            async with lock, DocumentSyncContext(client, file_path_obj) as uri:
                # Build params for the LSP request
                lsp_params = {"textDocument": {"uri": uri}}
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
        lsp_params: dict[str, Any],
        client: Any,
        file_path: str,
    ) -> dict[str, Any]:
        """Send LSP request using client directly.

        When called from document sync context, we use the client directly
        to avoid double-opening the document.

        Args:
            method: LSP method name (for logging)
            registry_method: Name of registry method (for routing)
            response_key: Key to use in response dict
            lsp_params: Parameters for the LSP request (textDocument, etc.)
            client: LSPClient instance to use
            file_path: File path for fallback

        Returns:
            Response dict with appropriate key
        """
        try:
            # Extract URI from lsp_params
            uri = lsp_params.get("textDocument", {}).get("uri", "")

            # Get file mtime for cache staleness check
            # Per ADR-001: mtime is ground truth for cache validation
            mtime: float | None = None
            try:
                mtime = os.stat(file_path).st_mtime
            except OSError:
                # File may have been deleted or permission denied
                # Proceed with mtime=None to force server query
                logger.debug(f"Could not stat file {file_path}, proceeding without mtime")

            # Call client method directly with uri to avoid _ensure_open
            if registry_method == "request_diagnostics":
                result = await client.request_diagnostics(file_path=file_path, uri=uri, mtime=mtime)
            elif registry_method == "request_document_symbols":
                result = await client.request_document_symbols(file_path=file_path, uri=uri)
            else:
                # Fallback - should not happen for doc sync methods
                registry_func = getattr(self._registry, registry_method)
                result = await registry_func(workspace_path=".", file_path=file_path)

            logger.debug(f"Client method {registry_method} returned for {method}")

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
        params: dict[str, Any],
        registry_method: str,
        response_key: str,
    ) -> dict[str, Any]:
        """Handle standard LSP methods that don't require document sync.

        This handles workspace-level methods and position-based methods
        that use _ensure_open internally.

        Args:
            method: LSP method name
            params: Request parameters
            registry_method: Name of registry method to call
            response_key: Key to use in response dict

        Returns:
            Response dict with appropriate key
        """
        registry_func = getattr(self._registry, registry_method)

        try:
            # Build kwargs based on RPC-style params mapping
            # The daemon receives RPC params with camelCase (workspacePath, filePath)
            # Registry methods expect snake_case (workspace_path, file_path)
            kwargs: dict[str, Any] = {}

            # Always include workspace_path for all methods
            kwargs["workspace_path"] = params.get("workspacePath", self.DEFAULTS["workspace_path"])

            # Include file_path for methods that need it
            if registry_method in {
                "request_definition",
                "request_references",
                "request_completions",
                "request_hover",
                "request_call_hierarchy_incoming",
                "request_call_hierarchy_outgoing",
            }:
                file_path = params.get("filePath")
                if file_path is None:
                    raise ValueError("Missing 'filePath' parameter")
                kwargs["file_path"] = file_path

            # Include line/column for position-based methods
            if registry_method in {
                "request_definition",
                "request_references",
                "request_completions",
                "request_hover",
                "request_call_hierarchy_incoming",
                "request_call_hierarchy_outgoing",
            }:
                kwargs["line"] = params.get("line", self.DEFAULTS["line"])
                kwargs["column"] = params.get("column", self.DEFAULTS["column"])

            # Include query for workspace symbol
            if registry_method == "request_workspace_symbols":
                kwargs["query"] = params.get("query", self.DEFAULTS["query"])
                logger.debug(
                    f"Workspace symbol request: workspace={kwargs.get('workspace_path')}, "
                    f"query={kwargs.get('query')}"
                )

            result = await registry_func(**kwargs)
            logger.debug(f"Registry method returned for {method}")

            # Wrap result with appropriate response key
            if response_key == "hover":
                return {response_key: result} if result else {}
            return {response_key: result}

        except Exception as e:
            logger.exception(f"Error handling LSP method {method}: {e}")
            raise

    async def _handle_did_change(self, params: dict[str, Any]) -> dict[str, Any]:
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
        file_path_str = params.get("filePath")
        if file_path_str is None:
            raise ValueError("Missing 'filePath' parameter")

        file_path = Path(file_path_str)

        # Verify file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get current mtime
        current_mtime = os.stat(file_path).st_mtime

        # Get workspace and client
        workspace_path = params.get("workspacePath", self._workspace_path)
        workspace = await self._registry.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()

        # Get file URI and cache state
        uri = file_path.as_uri()
        cache = client._diagnostic_cache
        file_state = await cache.get_file_state(uri)

        # Decide if didOpen is needed:
        # - File not open (is_open=False) -> send didOpen
        # - mtime differs (stale) -> send didOpen
        # - mtime matches and is_open -> skip didOpen (optimization)
        needs_didopen = not file_state.is_open
        if not needs_didopen and file_state.mtime > 0:
            is_stale = await cache.is_stale(uri, current_mtime)
            needs_didopen = is_stale

        if needs_didopen:
            # Send didOpen with current content
            content = file_path.read_text(encoding="utf-8")
            await client.open_document(file_path, content)
            # Mark as open in cache WITHOUT updating mtime
            # Per ADR-0010: rely on existing mtime-based invalidation
            await cache.on_did_open(uri)

        # Read current content and send didChange
        content = file_path.read_text(encoding="utf-8")
        await client.send_did_change(file_path, content)

        # Return acknowledgment (not diagnostics)
        return {"status": "acknowledged"}


async def run_daemon(
    socket_path: str,
    workspace_path: str,
    language: str = "python",
    lsp_conf: str | None = None,
    debug: bool = False,
    trace: bool = False,
    pid_file: Path | None = None,
    diagnostic_log: bool = False,
    diagnostic_log_path: Path | None = None,
) -> None:
    """Run the daemon main loop.

    Args:
        socket_path: Path to UNIX socket
        workspace_path: Workspace directory path
        language: Language identifier
        lsp_conf: Optional LSP configuration
        debug: Enable debug logging
        trace: Enable trace logging (more verbose than debug)
        pid_file: Path to PID file for cleanup
        diagnostic_log: If True, configure diagnostic logger with FileHandler
        diagnostic_log_path: Path to diagnostics.log file
    """
    # Enable debug/trace logging if requested
    if debug or trace:
        _configure_logger_levels(trace=trace)
        logger.debug(f"{'Trace' if trace else 'Debug'} logging enabled")

    # Configure diagnostic logger if enabled
    if diagnostic_log and diagnostic_log_path is not None:
        _configure_diagnostic_logger(diagnostic_log_path)

    logger.info(f"Starting daemon with socket: {socket_path}")
    logger.info(f"Workspace: {workspace_path}, Language: {language}")

    handler = RequestHandler(workspace_path, language, lsp_conf)
    server = UNIXServer(socket_path, handler.handle)

    # Set up signal handlers
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        shutdown_event.set()

    # Register handlers for SIGTERM, SIGINT, and SIGQUIT
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
        loop.add_signal_handler(sig, signal_handler)

    logger.info("Registered signal handlers for SIGTERM, SIGINT, SIGQUIT")

    try:
        await server.start()
        logger.info("Daemon server started")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except asyncio.CancelledError:
        logger.info("[ASYNC] Daemon task cancelled")
        raise

    except Exception as e:
        logger.exception(f"Daemon error: {e}")
        raise

    finally:
        logger.info("Shutting down daemon...")
        await server.stop()
        logger.info("Daemon stopped")

        # Clean up runtime files
        if pid_file is not None:
            cleanup_runtime_files(
                socket_path=Path(socket_path),
                pid_file=pid_file,
                workspace=Path(workspace_path).name,
                language=language,
            )
        else:
            # Fallback: construct paths from workspace
            from llm_lsp_cli.config import ConfigManager

            socket_p = Path(socket_path)
            pid_p = ConfigManager.build_pid_file_path(
                workspace_path=workspace_path,
                language=language,
            )
            cleanup_runtime_files(
                socket_path=socket_p,
                pid_file=pid_p,
                workspace=Path(workspace_path).name,
                language=language,
            )


if __name__ == "__main__":
    # For testing
    import sys

    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    language = sys.argv[2] if len(sys.argv) > 2 else "python"
    manager = DaemonManager(workspace, language)
    manager.start()
