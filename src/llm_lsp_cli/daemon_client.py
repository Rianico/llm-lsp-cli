"""Daemon client for auto-start functionality.

This module provides the DaemonClient class which abstracts daemon lifecycle
management from the CLI, enabling transparent auto-start behavior.
"""

from __future__ import annotations

import asyncio
from typing import Any

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.daemon import DaemonManager
from llm_lsp_cli.exceptions import (
    DaemonCrashedError,
    DaemonError,
    DaemonStartupError,
    DaemonStartupTimeoutError,
)
from llm_lsp_cli.ipc import UNIXClient


class DaemonClient:
    """Repository layer for daemon lifecycle management.

    The DaemonClient abstracts daemon startup, connection, and request routing.
    It implements auto-start behavior with exponential backoff for socket polling.

    Attributes:
        workspace_path: Path to the workspace directory
        language: Language identifier (e.g., 'python', 'typescript')
        startup_timeout: Maximum time to wait for daemon startup (default: 10.0s)
        connection_timeout: Maximum time for LSP requests (default: 30.0s)
    """

    # Exponential backoff configuration
    BACKOFF_INITIAL = 0.05  # 50ms initial delay
    BACKOFF_MULTIPLIER = 2.0
    BACKOFF_MAX = 1.0  # Cap at 1 second

    # Subprocess spawn configuration
    SUBPROCESS_STARTUP_DELAY = 0.1  # 100ms delay after spawning daemon subprocess

    def __init__(
        self,
        workspace_path: str,
        language: str,
        startup_timeout: float = 10.0,
        connection_timeout: float = 30.0,
    ):
        """Initialize the daemon client.

        Args:
            workspace_path: Path to workspace directory
            language: Language identifier
            startup_timeout: Timeout for daemon startup (default: 10.0s)
            connection_timeout: Timeout for LSP requests (default: 30.0s)
        """
        self.workspace_path = workspace_path
        self.language = language
        self.startup_timeout = startup_timeout
        self.connection_timeout = connection_timeout

        # Build socket path for this workspace/language
        self.socket_path = ConfigManager.build_socket_path(
            workspace_path=workspace_path,
            language=language,
        )

        # Internal state
        self._client: UNIXClient | None = None
        self._manager: DaemonManager | None = None

    async def request(self, method: str, params: dict[str, Any]) -> Any:
        """Send an LSP request, auto-starting daemon if needed.

        Args:
            method: LSP method name (e.g., 'textDocument/definition')
            params: Request parameters

        Returns:
            LSP response

        Raises:
            DaemonStartupError: If daemon fails to start
            DaemonStartupTimeoutError: If socket doesn't appear within timeout
            DaemonCrashedError: If socket exists but connection fails
            CLIError: For other connection/request errors
        """
        # Ensure daemon is running (auto-start if needed)
        await self._ensure_daemon_ready()

        # Create client and send request
        self._client = UNIXClient(
            str(self.socket_path),
            timeout=self.connection_timeout,
        )

        try:
            response = await self._client.request(method, params)
            return response
        except FileNotFoundError:
            # Socket existed but connection failed - daemon crashed
            raise DaemonCrashedError(
                socket_path=str(self.socket_path),
                workspace=self.workspace_path,
                language=self.language,
            ) from None
        except asyncio.TimeoutError as e:
            # Enhanced timeout error with LSP initialization context
            raise DaemonError(
                f"LSP initialization timed out after {self.connection_timeout}s. "
                f"Workspace: {self.workspace_path}, Language: {self.language}. "
                f"Check that the LSP server is properly configured and can start.",
                workspace=self.workspace_path,
                language=self.language,
            ) from e
        finally:
            await self._client.close()
            self._client = None

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        """Send an LSP notification, auto-starting daemon if needed.

        Args:
            method: LSP notification method name
            params: Notification parameters

        Raises:
            DaemonStartupError: If daemon fails to start
            DaemonStartupTimeoutError: If socket doesn't appear within timeout
        """
        # Ensure daemon is running (auto-start if needed)
        await self._ensure_daemon_ready()

        # Create client and send notification
        self._client = UNIXClient(
            str(self.socket_path),
            timeout=self.connection_timeout,
        )

        try:
            await self._client.notify(method, params)
        finally:
            await self._client.close()
            self._client = None

    async def send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a notification to the daemon with error handling.

        This is a convenience wrapper around notify() with consistent error handling
        similar to the request() method.

        Args:
            method: Notification method name
            params: Notification parameters

        Raises:
            CLIError: For connection errors
        """
        from llm_lsp_cli.exceptions import CLIError

        try:
            await self.notify(method, params)
        except DaemonStartupError as e:
            log_file = (
                e.log_file
                if hasattr(e, 'log_file') and e.log_file
                else ConfigManager.build_daemon_log_path(self.workspace_path, self.language)
            )
            raise CLIError(
                f"Failed to start daemon: {e}\n"
                f"Check logs at: {log_file}"
            ) from e
        except DaemonCrashedError as e:
            log_file = (
                e.log_file
                if hasattr(e, 'log_file') and e.log_file
                else ConfigManager.build_daemon_log_path(self.workspace_path, self.language)
            )
            raise CLIError(
                f"Daemon crashed: {e}\n"
                f"Check logs at: {log_file}"
            ) from e
        except FileNotFoundError:
            raise CLIError(
                "Cannot connect to daemon. Socket not found.\n"
                "Ensure the daemon is running: llm-lsp-cli status"
            ) from None
        except OSError as e:
            raise CLIError(
                f"Cannot connect to daemon: {e}\nEnsure the daemon is running: llm-lsp-cli start"
            ) from e

    async def _ensure_daemon_ready(self) -> None:
        """Ensure daemon is running and socket is ready.

        Auto-starts daemon if not running by spawning `llm-lsp-cli start` as a
        background subprocess, then waits for socket with exponential backoff.

        Raises:
            DaemonStartupError: If daemon fails to start
            DaemonStartupTimeoutError: If socket doesn't appear within timeout
        """
        self._manager = DaemonManager(
            workspace_path=self.workspace_path,
            language=self.language,
        )

        # Build log file path for error context
        log_file = ConfigManager.build_daemon_log_path(
            workspace_path=self.workspace_path,
            language=self.language,
        )

        # Check if daemon is already running
        if not self._manager.is_running():
            # Auto-start the daemon by spawning `llm-lsp-cli start` as background process
            try:
                await self._spawn_daemon_subprocess()
            except Exception as e:
                raise DaemonStartupError(
                    f"Failed to start daemon: {e}",
                    workspace=self.workspace_path,
                    language=self.language,
                    log_file=str(log_file),
                ) from e

        # Wait for socket with exponential backoff
        await self._wait_for_socket()

    async def _spawn_daemon_subprocess(self) -> None:
        """Spawn daemon as a background subprocess.

        Spawns `llm-lsp-cli daemon start` as a detached subprocess and returns immediately.
        """
        import asyncio
        import sys
        import tempfile
        from pathlib import Path

        # Build command to start daemon
        cmd = [
            sys.executable,
            "-m",
            "llm_lsp_cli",
            "daemon",
            "start",
            "--workspace",
            self.workspace_path,
            "--language",
            self.language,
        ]

        # Capture stderr to a temp file for diagnostics
        # This preserves immediate crash output (e.g., import errors)
        # Note: delete=False is required because the async subprocess needs
        # the file to persist after the context manager exits
        with tempfile.NamedTemporaryFile(
            mode='w+', delete=False, suffix='.log'
        ) as stderr_file:
            stderr_path = Path(stderr_file.name)

            try:
                # Spawn as detached subprocess
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=stderr_file.fileno(),
                    stdin=asyncio.subprocess.DEVNULL,
                    start_new_session=True,  # Detach from parent session
                )

                # Give the daemon a moment to start
                await asyncio.sleep(self.SUBPROCESS_STARTUP_DELAY)

                # Check if process died immediately
                if process.returncode is not None:
                    # Read stderr for diagnostics
                    stderr_content = (
                        stderr_path.read_text() if stderr_path.exists() else ""
                    )
                    error_detail = (
                        f"Daemon process exited immediately with code {process.returncode}"
                    )
                    if stderr_content:
                        error_detail += f"\nstderr: {stderr_content.strip()}"
                    raise RuntimeError(error_detail)
            finally:
                # Clean up temp file
                if stderr_path.exists():
                    stderr_path.unlink()

    async def _wait_for_socket(self) -> None:
        """Wait for socket to appear using exponential backoff.

        Polls for socket existence with delays: 50ms, 100ms, 200ms, 400ms, ..., 1s cap.
        After socket appears, waits an additional 10ms for socket to be fully ready.

        Raises:
            DaemonStartupTimeoutError: If socket doesn't appear within timeout
        """
        # Build log file path for error context
        log_file = ConfigManager.build_daemon_log_path(
            workspace_path=self.workspace_path,
            language=self.language,
        )

        elapsed = 0.0
        delay = self.BACKOFF_INITIAL

        while elapsed < self.startup_timeout:
            if self.socket_path.exists():
                # Socket appeared - wait a small delay for it to be fully ready
                await asyncio.sleep(0.01)  # 10ms
                return

            await asyncio.sleep(delay)
            elapsed += delay

            # Exponential backoff with cap
            delay = min(delay * self.BACKOFF_MULTIPLIER, self.BACKOFF_MAX)

        # Timeout - socket never appeared
        raise DaemonStartupTimeoutError(
            socket_path=str(self.socket_path),
            timeout=self.startup_timeout,
            workspace=self.workspace_path,
            language=self.language,
            log_file=str(log_file),
        )

    async def close(self) -> None:
        """Clean up resources.

        Closes the underlying UNIX client if present.
        Idempotent - safe to call multiple times.
        """
        if self._client is not None:
            await self._client.close()
            self._client = None
