"""Daemon package for llm-lsp-cli.

This package provides daemon process management, document synchronization,
request handling, and cleanup utilities for the LSP daemon.

All public symbols are re-exported here for backward compatibility.
Existing imports like ``from llm_lsp_cli.daemon import DaemonManager``
continue to work unchanged.
"""

# Re-export from submodules for backward compatibility
from llm_lsp_cli.daemon.cleanup import (
    cleanup_runtime_files,
    cleanup_unhealthy_sockets,
)
from llm_lsp_cli.daemon.document_sync import DocumentSyncContext
from llm_lsp_cli.daemon.handler import RequestHandler
from llm_lsp_cli.daemon.manager import DaemonManager
from llm_lsp_cli.daemon.runner import run_daemon

# RESPONSE_KEYS is now defined in lsp/constants.py and re-exported here
# for backward compatibility
from llm_lsp_cli.lsp.constants import RESPONSE_KEYS

__all__ = [
    "RESPONSE_KEYS",
    "DaemonManager",
    "DocumentSyncContext",
    "RequestHandler",
    "cleanup_runtime_files",
    "cleanup_unhealthy_sockets",
    "run_daemon",
]
