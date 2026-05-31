"""Daemon process lifecycle management."""

import asyncio
import logging
import os
import signal
import time
from pathlib import Path

from daemon import DaemonContext
from daemon.pidfile import PIDLockFile as PidFile

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.config.path_builder import create_socket_symlink
from llm_lsp_cli.daemon.cleanup import cleanup_runtime_files
from llm_lsp_cli.daemon.runner import run_daemon

logger = logging.getLogger("llm-lsp-cli.daemon")

# Constants
_SHUTDOWN_WAIT_ITERATIONS = 50  # 5 seconds max (50 * 0.1s)
_SHUTDOWN_POLL_INTERVAL = 0.1  # 100ms between process checks
_DAEMON_UMASK = 0o077  # Restrictive permissions (owner only)


class DaemonManager:
    """Manages the daemon process lifecycle for a specific workspace and language."""

    workspace_path: str
    language: str
    lsp_conf: str | None
    debug: bool
    trace: bool
    _lsp_server_name: str
    pid_file: Path
    socket_path: Path
    daemon_log_file: Path

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

    def _check_health(self) -> bool:
        """Check if daemon and language servers are healthy.

        Returns:
            True if daemon responds to ping with healthy status, False otherwise.
        """
        from llm_lsp_cli.ipc import UNIXClient
        from llm_lsp_cli.ipc.models import PingResult

        try:
            client = UNIXClient(str(self.socket_path), timeout=2.0)
            raw = asyncio.run(client.request("ping", {}))
            result = PingResult.model_validate(raw)
            return result.status == "healthy"
        except Exception:
            return False

    def start(self, diagnostic_log: bool = False) -> None:
        """Start the daemon process in background.

        If daemon is already running and healthy, prints warning and returns.
        If daemon is running but unhealthy, stops and restarts.
        If daemon is not running, starts normally.

        Args:
            diagnostic_log: If True, configure diagnostic logger to write to diagnostics.log
        """
        if self.is_running():
            if self._check_health():
                logger.warning("Daemon is already running and healthy.")
                return
            logger.warning("Daemon is running but unhealthy. Restarting...")
            self.stop()

        # Ensure directories exist
        _ = ConfigManager.ensure_runtime_dir()
        _ = ConfigManager.ensure_state_dir()
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.daemon_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create symlink from workspace to socket directory for discoverability
        create_socket_symlink(self.workspace_path, self.socket_path.parent)

        # Start daemon context with exception wrapper
        # This ensures exceptions are logged before the daemon process exits
        stdout_fd = open(self.daemon_log_file, "a")  # noqa: SIM115
        stderr_fd = open(self.daemon_log_file, "a")  # noqa: SIM115
        try:
            with DaemonContext(
                pidfile=PidFile(str(self.pid_file)),
                stdout=stdout_fd,
                stderr=stderr_fd,
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
        finally:
            # Close FDs if DaemonContext didn't take ownership (e.g., __init__ raised)
            stdout_fd.close()
            stderr_fd.close()

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
