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
    ):
        self.workspace_path = workspace_path
        self.language = language
        self.lsp_conf = lsp_conf
        self.debug = debug
        # Resolve server name for file naming
        self._lsp_server_name = ConfigManager.get_lsp_server_name(language)
        self.pid_file = ConfigManager.build_pid_file_path(
            workspace_path, language, lsp_server_name=self._lsp_server_name
        )
        self.socket_path = ConfigManager.build_socket_path(
            workspace_path, language, lsp_server_name=self._lsp_server_name
        )
        self.log_file = ConfigManager.build_log_file_path(
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

    def start(self) -> None:
        """Start the daemon process in background."""
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
        ConfigManager.ensure_project_dir(self.workspace_path)
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
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
                        pid_file=self.pid_file,
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
        }:
            return await self._handle_lsp_method(method, params)

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

        # Get registry method by name
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
                "request_document_symbols",
                "request_diagnostics",
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


async def run_daemon(
    socket_path: str,
    workspace_path: str,
    language: str = "python",
    lsp_conf: str | None = None,
    debug: bool = False,
    pid_file: Path | None = None,
) -> None:
    """Run the daemon main loop.

    Args:
        socket_path: Path to UNIX socket
        workspace_path: Workspace directory path
        language: Language identifier
        lsp_conf: Optional LSP configuration
        debug: Enable debug logging
        pid_file: Path to PID file for cleanup
    """
    # Enable debug logging if requested
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)  # Root logger
        logging.getLogger("llm-lsp-cli").setLevel(logging.DEBUG)
        logging.getLogger("llm_lsp_cli").setLevel(logging.DEBUG)
        logging.getLogger("llm_lsp_cli.lsp").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

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
