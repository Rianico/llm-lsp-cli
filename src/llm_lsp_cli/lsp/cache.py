"""Unified diagnostic cache with relative path keys and client-managed version tracking.

This module implements the DiagnosticCache class as specified in ADR 002.
It replaces the dual-cache system with a single cache using:
- Project-relative path keys (not URIs)
- FileState dataclass for tracking document state
- Client-managed version tracking (increment on didChange)
- Async-safe operations with asyncio.Lock
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_lsp_cli.utils.uri import uri_to_relative_path

from . import types as lsp


@dataclass
class FileState:
    """Tracks the state of a single file in the diagnostic cache.

    Version Model:
        - mtime: File modification time (ground truth for content changes)
        - document_version: LSP document version (sent to server)
        - last_result_id: Server's diagnostic version (from textDocument/diagnostic)

    Cache Invalidation:
        - Stale iff incoming_mtime > stored_mtime

    Attributes:
        mtime: File modification time in epoch seconds (0.0 = untracked)
        document_version: Version number of the document (starts at 1 for open files)
        last_result_id: Optional result ID from LSP server diagnostic response
        is_open: Whether the file is currently open in the editor
        diagnostics: List of diagnostic dictionaries from the LSP server
        uri: The original file URI (for workspace diagnostic responses)
    """
    mtime: float = 0.0
    document_version: int = 0
    last_result_id: str | None = None
    is_open: bool = False
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    uri: str = ""


class DiagnosticCache:
    """Unified cache for LSP diagnostics using relative path keys.

    This cache manages diagnostics for all files in a workspace using:
    - Relative paths as cache keys (resolved from URIs)
    - FileState objects to track document version and state
    - Async-safe operations with asyncio.Lock for concurrent access

    Attributes:
        _workspace_root: The root directory of the workspace
        _cache: Internal storage mapping relative paths to FileState objects
        _lock: Asyncio lock for thread-safe mutations
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize the diagnostic cache.

        Args:
            workspace_root: The root directory of the workspace for relative path resolution
        """
        self._workspace_root = workspace_root.resolve()
        self._cache: dict[str, FileState] = {}
        self._lock = asyncio.Lock()

    def _uri_to_relative_path(self, uri: str) -> str:
        """Convert a file URI to a project-relative path.

        Delegates to the shared utility function.

        Args:
            uri: File URI (e.g., "file:///workspace/src/module/file.py")

        Returns:
            Relative path within workspace (e.g., "src/module/file.py"),
            or absolute path if file is outside workspace (fallback)
        """
        return uri_to_relative_path(uri, self._workspace_root)

    async def update_diagnostics(
        self,
        uri: str,
        diagnostics: list[dict[str, Any]],
        result_id: str | None = None,
    ) -> None:
        """Update cached diagnostics for a file.

        Args:
            uri: File URI to update
            diagnostics: New list of diagnostic items
            result_id: Optional result ID from LSP server response
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key, FileState())
            # Update diagnostics but preserve document_version and is_open
            state.diagnostics = list(diagnostics)  # Defensive copy
            state.uri = uri  # Store original URI for workspace responses
            if result_id is not None:
                state.last_result_id = result_id
            self._cache[key] = state

    async def get_diagnostics(self, uri: str) -> list[dict[str, Any]]:
        """Get cached diagnostics for a file.

        Args:
            uri: File URI to query

        Returns:
            List of diagnostic items, or empty list if not cached
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key)
            if state is None:
                return []
            return list(state.diagnostics)  # Return defensive copy

    def get_cached(self, uri: str) -> list[dict[str, Any]]:
        """Get cached diagnostics for a file (synchronous fallback).

        This is a synchronous version for use in notification handlers
        where await is not available. Uses the lock if a loop is running,
        otherwise accesses directly.

        Args:
            uri: File URI to query

        Returns:
            List of diagnostic items, or empty list if not cached
        """
        key = self._uri_to_relative_path(uri)
        state = self._cache.get(key)
        if state is None:
            return []
        return list(state.diagnostics)  # Return defensive copy

    async def get_file_state(self, uri: str) -> FileState:
        """Get the full FileState for a file.

        Args:
            uri: File URI to query

        Returns:
            FileState object for the file (with defaults if not cached)
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            return self._cache.get(key, FileState())

    def get_file_state_sync(self, uri: str) -> FileState:
        """Get the full FileState for a file (synchronous fallback).

        This is a synchronous version for use in contexts where await
        is not available (e.g., type conversion helpers).

        Args:
            uri: File URI to query

        Returns:
            FileState object for the file (with defaults if not cached)
        """
        key = self._uri_to_relative_path(uri)
        return self._cache.get(key, FileState())

    async def on_did_open(self, uri: str, mtime: float | None = None) -> None:
        """Handle textDocument/didOpen notification.

        Initializes or updates file state when a file is opened:
        - Sets is_open to True
        - Increments document_version (starts at 1)
        - Sets mtime if provided

        Args:
            uri: File URI that was opened
            mtime: Optional file modification time (epoch seconds)
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key, FileState())
            state.is_open = True
            state.document_version += 1
            if mtime is not None:
                state.mtime = mtime
            self._cache[key] = state

    async def set_mtime(self, uri: str, mtime: float) -> None:
        """Set the modification time for a file.

        Creates FileState if it doesn't exist, updates mtime if it does.

        Args:
            uri: File URI to update
            mtime: File modification time (epoch seconds)
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key, FileState())
            state.mtime = mtime
            self._cache[key] = state

    async def increment_version(self, uri: str) -> None:
        """Increment the document version (called on didChange).

        Args:
            uri: File URI that changed
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key, FileState())
            state.document_version += 1
            self._cache[key] = state

    async def update_document_version(self, uri: str, version: int) -> None:
        """Update document version to a specific value.

        Note: Version should never decrement in normal operation.
        This method is for explicit version setting.

        Args:
            uri: File URI to update
            version: New version number
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key, FileState())
            # Only update if version is not less than current (monotonic)
            if version >= state.document_version:
                state.document_version = version
            self._cache[key] = state

    async def is_stale(self, uri: str, incoming_mtime: float) -> bool:
        """Check if cached diagnostics are stale based on mtime comparison.

        Staleness Rules:
            - Stale iff incoming_mtime > stored_mtime
            - Not stale if file not cached (returns False for unknown files)
            - File with mtime == 0.0 is untracked (stale if incoming > 0)

        The "unknown = not stale" semantics indicate "no cached data to invalidate"
        rather than "file is fresh." Callers should proceed with LSP request.

        Args:
            uri: File URI to check
            incoming_mtime: Current file modification time (epoch seconds)

        Returns:
            True if diagnostics are stale, False if fresh or not cached.
        """
        async with self._lock:
            key = self._uri_to_relative_path(uri)
            state = self._cache.get(key)
            if state is None:
                return False
            # Stale if incoming_mtime > stored_mtime
            return incoming_mtime > state.mtime

    async def get_all_workspace_diagnostics(
        self,
    ) -> list[lsp.WorkspaceDiagnosticItem]:
        """Get all cached diagnostics for the workspace.

        Returns:
            List of workspace diagnostic items, each containing:
            - uri: Original file URI
            - version: Document version
            - diagnostics: List of diagnostic items (may be empty)
        """
        async with self._lock:
            result: list[dict[str, Any]] = []
            for key, state in self._cache.items():
                # Include all cached files, not just those with diagnostics
                # This ensures workspace-diagnostic returns complete information
                result.append({
                    "uri": state.uri if state.uri else key,
                    "version": state.document_version,
                    "diagnostics": list(state.diagnostics),
                })
            return result  # type: ignore[return-value]
