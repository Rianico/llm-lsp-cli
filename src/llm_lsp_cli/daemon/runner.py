"""Daemon main loop entry point."""

import asyncio
import logging
import signal
from pathlib import Path

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.daemon.cleanup import (
    _configure_diagnostic_logger,
    _configure_logger_levels,
    cleanup_runtime_files,
)
from llm_lsp_cli.daemon.handler import RequestHandler
from llm_lsp_cli.ipc import UNIXServer

logger = logging.getLogger("llm-lsp-cli.daemon")


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
        _ = await shutdown_event.wait()

    except asyncio.CancelledError:
        logger.info("[ASYNC] Daemon task cancelled")
        raise

    except Exception as e:
        logger.exception(f"Daemon error: {e}")
        raise

    finally:
        logger.info("Shutting down daemon...")
        # Shutdown all LSP servers before stopping the socket server
        # This ensures the daemon-to-LSP parent-child lifecycle is respected
        try:
            await handler.shutdown_servers()
        except Exception as e:
            logger.exception(f"Error shutting down LSP servers: {e}")
        await server.stop()
        logger.info("Daemon stopped")

        # Clean up runtime files
        # Note: cleanup_pid=False because DaemonContext manages the PID file.
        # We only clean up the socket here; DaemonContext.__exit__ will
        # release the PID file lock naturally.
        if pid_file is not None:
            cleanup_runtime_files(
                socket_path=Path(socket_path),
                pid_file=pid_file,
                workspace=Path(workspace_path).name,
                language=language,
                cleanup_pid=False,
            )
        else:
            # Fallback: construct paths from workspace
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
                cleanup_pid=False,
            )
