"""Daemon process management for llm-lsp-cli."""

import asyncio
import logging
import os
import signal
import time
from typing import Any, cast

from daemon import DaemonContext  # type: ignore[import-untyped]
from daemon.pidfile import PIDLockFile as PidFile  # type: ignore[import-untyped]

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.ipc import UNIXServer
from llm_lsp_cli.server import ServerRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm-lsp-cli.daemon")


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
        self._lsp_server_name = ConfigManager._get_lsp_server_name(language)
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

    def start(self) -> None:
        """Start the daemon process in background."""
        if self.is_running():
            raise RuntimeError("Daemon is already running")

        # Ensure directories exist
        ConfigManager.ensure_runtime_dir()
        ConfigManager.ensure_state_dir()
        ConfigManager.ensure_project_dir(self.workspace_path)
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.daemon_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Start daemon context
        with DaemonContext(
            pidfile=PidFile(str(self.pid_file)),
            stdout=open(self.daemon_log_file, "a"),
            stderr=open(self.daemon_log_file, "a"),
            umask=0o077,  # Restrictive permissions
        ):
            logger.info("Daemon starting...")
            asyncio.run(
                run_daemon(
                    str(self.socket_path),
                    self.workspace_path,
                    self.language,
                    self.lsp_conf,
                    self.debug,
                )
            )

    def stop(self) -> None:
        """Stop the daemon process."""
        if not self.is_running():
            logger.warning("Daemon is not running")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return

        pid = self.get_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Sent SIGTERM to daemon (PID: {pid})")

                # Wait for process to stop
                for _ in range(50):  # 5 seconds max
                    try:
                        os.kill(pid, 0)
                        time.sleep(0.1)
                    except OSError:
                        # Process stopped
                        break
                else:
                    # Force kill if still running
                    os.kill(pid, signal.SIGKILL)
                    logger.info(f"Sent SIGKILL to daemon (PID: {pid})")

            except ProcessLookupError:
                pass

        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

        # Clean up socket file
        if self.socket_path.exists():
            self.socket_path.unlink()


class RequestHandler:
    """Handles incoming RPC requests."""

    def __init__(self, workspace_path: str, language: str, lsp_conf: str | None = None):
        self._shutdown = False
        self._workspace_path = workspace_path
        self._language = language
        self._lsp_conf = lsp_conf
        self._registry = ServerRegistry(lsp_conf=lsp_conf)

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

        # LSP feature methods
        elif method == "textDocument/definition":
            return {"locations": await self.handle_definition(params)}

        elif method == "textDocument/references":
            return {"locations": await self.handle_references(params)}

        elif method == "textDocument/completion":
            return {"items": await self.handle_completion(params)}

        elif method == "textDocument/hover":
            result = await self.handle_hover(params)
            return {"hover": result} if result else {}

        elif method == "textDocument/documentSymbol":
            return {"symbols": await self.handle_document_symbol(params)}

        elif method == "workspace/symbol":
            return {"symbols": await self.handle_workspace_symbol(params)}

        else:
            raise ValueError(f"Unknown method: {method}")

    async def handle_definition(self, params: dict[str, Any]) -> list[Any]:
        """Handle textDocument/definition request."""
        workspace_path = params.get("workspacePath", ".")
        file_path = params.get("filePath")
        line = params.get("line", 0)
        column = params.get("column", 0)

        if not file_path:
            raise ValueError("Missing 'filePath' parameter")

        locations = await self._registry.request_definition(
            workspace_path=workspace_path,
            file_path=file_path,
            line=line,
            column=column,
        )
        return locations

    async def handle_references(self, params: dict[str, Any]) -> list[Any]:
        """Handle textDocument/references request."""
        workspace_path = params.get("workspacePath", ".")
        file_path = params.get("filePath")
        line = params.get("line", 0)
        column = params.get("column", 0)

        if not file_path:
            raise ValueError("Missing 'filePath' parameter")

        locations = await self._registry.request_references(
            workspace_path=workspace_path,
            file_path=file_path,
            line=line,
            column=column,
        )
        return locations

    async def handle_completion(self, params: dict[str, Any]) -> list[Any]:
        """Handle textDocument/completion request."""
        workspace_path = params.get("workspacePath", ".")
        file_path = params.get("filePath")
        line = params.get("line", 0)
        column = params.get("column", 0)

        if not file_path:
            raise ValueError("Missing 'filePath' parameter")

        items = await self._registry.request_completions(
            workspace_path=workspace_path,
            file_path=file_path,
            line=line,
            column=column,
        )
        return items

    async def handle_hover(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Handle textDocument/hover request."""
        workspace_path = params.get("workspacePath", ".")
        file_path = params.get("filePath")
        line = params.get("line", 0)
        column = params.get("column", 0)

        if not file_path:
            raise ValueError("Missing 'filePath' parameter")

        hover = await self._registry.request_hover(
            workspace_path=workspace_path,
            file_path=file_path,
            line=line,
            column=column,
        )
        return cast(dict[str, Any] | None, hover)

    async def handle_document_symbol(self, params: dict[str, Any]) -> list[Any]:
        """Handle textDocument/documentSymbol request."""
        workspace_path = params.get("workspacePath", ".")
        file_path = params.get("filePath")

        if not file_path:
            raise ValueError("Missing 'filePath' parameter")

        symbols = await self._registry.request_document_symbols(
            workspace_path=workspace_path,
            file_path=file_path,
        )
        return symbols

    async def handle_workspace_symbol(self, params: dict[str, Any]) -> list[Any]:
        """Handle workspace/symbol request."""
        workspace_path = params.get("workspacePath", ".")
        query = params.get("query", "")

        logger.debug(f"Workspace symbol request: workspace={workspace_path}, query={query}")
        symbols = await self._registry.request_workspace_symbols(
            workspace_path=workspace_path,
            query=query,
        )
        logger.debug(f"Workspace symbol response: {len(symbols)} symbols found")
        return symbols


async def run_daemon(
    socket_path: str,
    workspace_path: str,
    language: str = "python",
    lsp_conf: str | None = None,
    debug: bool = False,
) -> None:
    """Run the daemon main loop."""
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

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await server.start()
        logger.info("Daemon server started")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.exception(f"Daemon error: {e}")
        raise

    finally:
        logger.info("Shutting down daemon...")
        await server.stop()
        logger.info("Daemon stopped")


if __name__ == "__main__":
    # For testing
    import sys

    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    language = sys.argv[2] if len(sys.argv) > 2 else "python"
    manager = DaemonManager(workspace, language)
    manager.start()
