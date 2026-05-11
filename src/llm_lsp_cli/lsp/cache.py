"""Unified diagnostic cache with absolute path keys and client-managed version tracking.

This module implements the DiagnosticCache class as specified in ADR 002.
It replaces the dual-cache system with a single cache using:
- Absolute path keys (not URIs)
- FileState dataclass for tracking document state
- Client-managed version tracking (increment on didChange)
- Async-safe operations with asyncio.Lock
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from llm_lsp_cli.utils.uri import uri_to_absolute_path

from .types import Diagnostic, WorkspaceDiagnosticItem


@dataclass
class FileState:
    """Tracks the state of a single file in the diagnostic cache.

    Version Model:
        - mtime: File modification time (ground truth for content changes)
        - document_version: LSP document version (sent to server)
        - last_result_id: Server's diagnostic version (from textDocument/diagnostic)

    Cache Invalidation:
        - Stale iff incoming_mtime > stored_mtime

    Diagnostics Split (ADR for bug fix):
        - document_diagnostics: Updated by textDocument/publishDiagnostics and textDocument/diagnostic
        - workspace_diagnostics: Updated by workspace/diagnostic via $/progress
        - The two sources are independent and must not overwrite each other

    Attributes:
        mtime: File modification time in epoch seconds (0.0 = untracked)
        document_version: Version number of the document (starts at 1 for open files)
        last_result_id: Optional result ID from LSP server diagnostic response (document-associated)
        is_open: Whether the file is currently open in the editor
        document_diagnostics: Diagnostics from textDocument/publishDiagnostics and textDocument/diagnostic
        workspace_diagnostics: Diagnostics from workspace/diagnostic via $/progress
        uri: The original file URI (for workspace diagnostic responses)
    """

    mtime: float = 0.0
    document_version: int = 0
    last_result_id: str | None = None
    is_open: bool = False
    document_diagnostics: list[dict[str, object]] = field(default_factory=list)
    workspace_diagnostics: list[dict[str, object]] = field(default_factory=list)
    has_workspace_diagnostics: bool = False  # True if workspace diagnostics were explicitly written
    uri: str = ""


class DiagnosticCache:
    """Unified cache for LSP diagnostics using absolute path keys.

    This cache manages diagnostics for all files in a workspace using:
    - Absolute paths as cache keys (resolved from URIs)
    - FileState objects to track document version and state
    - Async-safe operations with asyncio.Lock for concurrent access

    Attributes:
        _workspace_root: The root directory of the workspace
        _cache: Internal storage mapping absolute paths to FileState objects
        _lock: Asyncio lock for thread-safe mutations
    """

    _workspace_root: Path
    _cache: dict[str, FileState]
    _lock: asyncio.Lock

    def __init__(self, workspace_root: Path) -> None:
        """Initialize the diagnostic cache.

        Args:
            workspace_root: The root directory of the workspace for relative path resolution
        """
        self._workspace_root = workspace_root.resolve()
        self._cache = {}
        self._lock = asyncio.Lock()

    def _uri_to_absolute_path(self, uri: str) -> str:
        """Convert a file URI to an absolute path.

        Delegates to the shared utility function.

        Args:
            uri: File URI (e.g., "file:///workspace/src/module/file.py")

        Returns:
            Absolute path (e.g., "/workspace/src/module/file.py")
        """
        return uri_to_absolute_path(uri, self._workspace_root)

    async def update_diagnostics(
        self,
        uri: str,
        diagnostics: list[dict[str, object]],
        result_id: str | None = None,
    ) -> None:
        """Update cached diagnostics for a file.

        DEPRECATED: Use update_document_diagnostics instead.
        This method delegates to update_document_diagnostics for backward compatibility.

        Args:
            uri: File URI to update
            diagnostics: New list of diagnostic items
            result_id: Optional result ID from LSP server response
        """
        await self.update_document_diagnostics(uri, diagnostics, result_id)

    async def update_document_diagnostics(
        self,
        uri: str,
        diagnostics: list[dict[str, object]],
        result_id: str | None = None,
    ) -> None:
        """Update document diagnostics for a file.

        Updated by textDocument/publishDiagnostics and textDocument/diagnostic.
        Does NOT affect workspace_diagnostics.

        Args:
            uri: File URI to update
            diagnostics: New list of diagnostic items
            result_id: Optional result ID from LSP server response
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key, FileState())
            # Update document_diagnostics, preserve all other fields
            state.document_diagnostics = list(diagnostics)  # Defensive copy
            state.uri = uri  # Store original URI for workspace responses
            if result_id is not None:
                state.last_result_id = result_id
            self._cache[key] = state

    async def update_workspace_diagnostics(
        self,
        uri: str,
        diagnostics: list[dict[str, object]],
    ) -> None:
        """Update workspace diagnostics for a file.

        Updated by workspace/diagnostic via $/progress.
        Does NOT affect document_diagnostics.

        Args:
            uri: File URI to update
            diagnostics: New list of diagnostic items
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key, FileState())
            # Update workspace_diagnostics, preserve all other fields
            state.workspace_diagnostics = list(diagnostics)  # Defensive copy
            state.uri = uri  # Store original URI for workspace responses
            state.has_workspace_diagnostics = True  # Mark that workspace diags were written
            self._cache[key] = state

    async def get_document_diagnostics(self, uri: str) -> list[dict[str, object]]:
        """Get document diagnostics for a file.

        Args:
            uri: File URI to query

        Returns:
            List of document diagnostic items, or empty list if not cached
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key)
            if state is None:
                return []
            return list(state.document_diagnostics)  # Return defensive copy

    async def get_workspace_diagnostics_for_uri(self, uri: str) -> list[dict[str, object]]:
        """Get workspace diagnostics for a specific file URI.

        Args:
            uri: File URI to query

        Returns:
            List of workspace diagnostic items, or empty list if not cached
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key)
            if state is None:
                return []
            return list(state.workspace_diagnostics)  # Return defensive copy

    async def get_diagnostics(self, uri: str) -> list[dict[str, object]]:
        """Get cached diagnostics for a file.

        Returns document_diagnostics for backward compatibility with existing callers.

        Args:
            uri: File URI to query

        Returns:
            List of diagnostic items, or empty list if not cached
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key)
            if state is None:
                return []
            return list(state.document_diagnostics)  # Return defensive copy

    def get_cached(self, uri: str) -> list[dict[str, object]]:
        """Get cached diagnostics for a file (synchronous fallback).

        This is a synchronous version for use in notification handlers
        where await is not available. Returns document_diagnostics.

        Args:
            uri: File URI to query

        Returns:
            List of diagnostic items, or empty list if not cached
        """
        key = self._uri_to_absolute_path(uri)
        state = self._cache.get(key)
        if state is None:
            return []
        return list(state.document_diagnostics)  # Return defensive copy

    async def get_file_state(self, uri: str) -> FileState:
        """Get the full FileState for a file.

        Args:
            uri: File URI to query

        Returns:
            FileState object for the file (with defaults if not cached)
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
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
        key = self._uri_to_absolute_path(uri)
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
            key = self._uri_to_absolute_path(uri)
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
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key, FileState())
            state.mtime = mtime
            self._cache[key] = state

    async def increment_version(self, uri: str) -> None:
        """Increment the document version (called on didChange).

        Note: We do NOT clear last_result_id here because:
        - The file content may change without affecting diagnostics (e.g., comments)
        - The LSP server uses previousResultId to return "unchanged" optimization
        - The server tracks document versions internally and will return fresh
          diagnostics when appropriate

        Args:
            uri: File URI that changed
        """
        async with self._lock:
            key = self._uri_to_absolute_path(uri)
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
            key = self._uri_to_absolute_path(uri)
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
            key = self._uri_to_absolute_path(uri)
            state = self._cache.get(key)
            if state is None:
                return False
            # Stale if incoming_mtime > stored_mtime
            return incoming_mtime > state.mtime

    async def get_all_workspace_diagnostics(
        self,
    ) -> list[WorkspaceDiagnosticItem]:
        """Get all workspace diagnostics for the workspace.

        Returns only files that have had workspace_diagnostics written to them.
        Files with only document_diagnostics are NOT included.

        Returns:
            List of workspace diagnostic items, each containing:
            - uri: Original file URI
            - version: Document version
            - diagnostics: List of diagnostic items from workspace_diagnostics field
        """
        async with self._lock:
            result: list[WorkspaceDiagnosticItem] = []
            for key, state in self._cache.items():
                # Only include files that have had workspace diagnostics explicitly written
                # This is tracked by the has_workspace_diagnostics flag
                if not state.has_workspace_diagnostics:
                    continue

                # Convert raw diagnostic dicts to Diagnostic models
                validated_diagnostics = [Diagnostic.model_validate(d) for d in state.workspace_diagnostics]
                item = WorkspaceDiagnosticItem(
                    uri=state.uri if state.uri else key,
                    version=state.document_version,
                    diagnostics=validated_diagnostics,
                )
                result.append(item)
            return result
