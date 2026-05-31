"""Daemon cleanup utilities and logging configuration."""

import asyncio
import logging
import os
from pathlib import Path

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
    cleanup_pid: bool = True,
) -> None:
    """Clean up daemon runtime files (socket and PID).

    Args:
        socket_path: Path to the UNIX socket file
        pid_file: Path to the PID lock file
        workspace: Workspace name for logging
        language: Language name for logging
        cleanup_pid: If True, remove PID file. Set to False when called from
            within DaemonContext, since the context manager handles PID cleanup.

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

    # Remove PID file only if explicitly requested
    # DaemonContext manages its own PID file, so we skip this when running
    # inside the context to avoid NotLocked errors during shutdown
    if cleanup_pid and pid_file.exists():
        try:
            pid_file.unlink()
            logger.debug(f"[CLEANUP] Removed PID file: {pid_file}")
        except OSError as e:
            logger.error(f"[CLEANUP] Failed to remove PID file: {e}")
    elif not cleanup_pid:
        logger.debug("[CLEANUP] Skipping PID file cleanup (managed by DaemonContext)")
    else:
        logger.debug("[CLEANUP] PID file already absent")

    logger.info("[CLEANUP] Cleanup complete")


def cleanup_unhealthy_sockets(socket_base_dir: str | None = None) -> list[Path]:
    """Clean up socket directories with no healthy daemon.

    Iterates all directories under the socket base directory and removes
    those where no daemon process is running or the daemon is unhealthy.

    Args:
        socket_base_dir: Base directory containing socket directories.

    Returns:
        List of cleaned directory paths.
    """
    if socket_base_dir is None:
        socket_base_dir = f"/tmp/llm-lsp-cli-{os.getuid()}"

    base = Path(socket_base_dir)
    if not base.is_dir():
        return []

    cleaned: list[Path] = []
    for socket_dir in base.iterdir():
        if not socket_dir.is_dir():
            continue

        # Try to determine workspace from socket directory
        # Socket dir name format: {sanitized}_{hash}
        # We can't recover the original workspace path, so we check health directly
        sock_files = list(socket_dir.glob("*.sock"))
        if not sock_files:
            # No socket files, remove empty directory
            import shutil

            shutil.rmtree(socket_dir)
            cleaned.append(socket_dir)
            continue

        # Check if any daemon is healthy by trying to ping
        is_healthy = False
        for sock_file in sock_files:
            try:
                from llm_lsp_cli.ipc import UNIXClient
                from llm_lsp_cli.ipc.models import PingResult

                client = UNIXClient(str(sock_file), timeout=2.0)
                raw = asyncio.run(client.request("ping", {}))
                result = PingResult.model_validate(raw)
                if result.status == "healthy":
                    is_healthy = True
                    break
            except Exception:
                continue

        if not is_healthy:
            import shutil

            shutil.rmtree(socket_dir)
            cleaned.append(socket_dir)
            logger.info(f"[CLEANUP] Removed unhealthy socket directory: {socket_dir}")

    return cleaned
