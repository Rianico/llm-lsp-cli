"""Rename service for LSP rename operations.

Orchestrates the rename flow: prepare -> rename -> backup -> apply.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llm_lsp_cli.output.formatter import Position, Range, RenameEditRecord
from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute

from .backup_manager import BackupManager, RenameSession

if TYPE_CHECKING:
    from llm_lsp_cli.lsp.client import LSPClient

logger = logging.getLogger(__name__)


class RenameService:
    """Orchestrates the rename flow: prepare -> rename -> backup -> apply."""

    def __init__(self, backup_manager: BackupManager):
        """Initialize the rename service.

        Args:
            backup_manager: BackupManager instance for file backups
        """
        self._backup_manager = backup_manager

    def supports_prepare_rename(self, client: Any) -> bool:
        """Check if the LSP server supports prepareRename.

        Args:
            client: LSP client with server_capabilities

        Returns:
            True if server supports prepareRename, False otherwise
        """
        capabilities = getattr(client, "server_capabilities", {}) or {}
        rename_provider = capabilities.get("renameProvider")

        if isinstance(rename_provider, dict):
            return bool(rename_provider.get("prepareProvider", False))
        return False

    async def preview(
        self,
        client: LSPClient,
        file_path: str,
        line: int,
        character: int,
        new_name: str,
    ) -> list[RenameEditRecord]:
        """Get rename preview without applying changes.

        Args:
            client: LSP client
            file_path: Relative path to the file
            line: Line number (0-based)
            character: Character position (0-based)
            new_name: New name for the symbol

        Returns:
            List of RenameEditRecord objects representing changes
        """
        # Optionally call prepareRename if supported
        if self.supports_prepare_rename(client):
            try:
                await client.request_prepare_rename(file_path, line, character)
            except Exception as e:
                logger.warning(f"prepareRename failed: {e}")

        # Request rename
        workspace_edit = await client.request_rename(
            file_path, line, character, new_name
        )

        # Handle null or empty response
        if workspace_edit is None:
            return []

        # Extract records from WorkspaceEdit
        return self._extract_edit_records(workspace_edit, client)

    async def apply(
        self,
        client: LSPClient,
        file_path: str,
        line: int,
        character: int,
        new_name: str,
    ) -> tuple[list[RenameEditRecord], RenameSession]:
        """Apply rename with backup.

        Args:
            client: LSP client
            file_path: Relative path to the file
            line: Line number (0-based)
            character: Character position (0-based)
            new_name: New name for the symbol

        Returns:
            Tuple of (list of RenameEditRecord, RenameSession)
        """
        workspace_path = self._backup_manager._workspace_path

        # Create session
        position = Position(line=line, character=character)
        session = self._backup_manager.create_session(
            file_path=file_path,
            position=position,
            new_name=new_name,
        )

        # Optionally call prepareRename if supported
        if self.supports_prepare_rename(client):
            try:
                await client.request_prepare_rename(file_path, line, character)
            except Exception as e:
                logger.warning(f"prepareRename failed: {e}")

        # Request rename
        workspace_edit = await client.request_rename(
            file_path, line, character, new_name
        )

        # Handle null or empty response
        if workspace_edit is None:
            session.status = "failed"
            return [], session

        # Extract records from WorkspaceEdit
        records = self._extract_edit_records(workspace_edit, client)

        if not records:
            session.status = "applied"
            return [], session

        # Get unique files to backup
        files_to_backup = self._get_files_to_backup(records, workspace_path)

        # Backup files before modifying
        self._backup_manager.backup_files(session, files_to_backup)

        try:
            # Apply edits to files
            self._apply_edits(records, workspace_path)

            # Update session status
            session.status = "applied"

            # Write manifest and request files
            self._backup_manager.write_request_json(session)
            self._backup_manager.write_manifest(session)

            return records, session

        except Exception as e:
            # Restore all files on failure
            logger.error(f"Apply failed, restoring files: {e}")
            self._backup_manager.restore(session)
            session.status = "failed"
            raise

    async def rollback(self, session_id: str) -> None:
        """Rollback a rename operation by session ID.

        Args:
            session_id: ID of the session to rollback
        """
        self._backup_manager.restore_by_id(session_id)

    def preview_from_edit(
        self,
        workspace_edit: dict[str, Any] | None,
        file_path: str,
        position: Position,
        new_name: str,
    ) -> list[RenameEditRecord]:
        """Get rename preview from a pre-fetched workspace_edit.

        This is a synchronous method for use when the workspace_edit has
        already been obtained (e.g., from the daemon).

        Args:
            workspace_edit: LSP WorkspaceEdit response (can be None)
            file_path: Relative path to the file (unused, for API consistency)
            position: Position object with line and character (unused, for API consistency)
            new_name: New name for the symbol (unused, for API consistency)

        Returns:
            List of RenameEditRecord objects representing changes
        """
        _ = file_path, position, new_name  # Mark as intentionally unused
        if workspace_edit is None:
            return []

        return self._extract_edit_records_from_dict(workspace_edit)

    def apply_from_edit(
        self,
        workspace_edit: dict[str, Any] | None,
        file_path: str,
        position: Position,
        new_name: str,
    ) -> tuple[list[RenameEditRecord], RenameSession]:
        """Apply rename from a pre-fetched workspace_edit with backup.

        This is a synchronous method for use when the workspace_edit has
        already been obtained (e.g., from the daemon).

        Args:
            workspace_edit: LSP WorkspaceEdit response (can be None)
            file_path: Relative path to the file
            position: Position object with line and character
            new_name: New name for the symbol

        Returns:
            Tuple of (list of RenameEditRecord, RenameSession)
        """
        workspace_path = self._backup_manager._workspace_path

        # Create session
        session = self._backup_manager.create_session(
            file_path=file_path,
            position=position,
            new_name=new_name,
        )

        # Handle null response
        if workspace_edit is None:
            session.status = "failed"
            return [], session

        # Extract records from WorkspaceEdit
        records = self._extract_edit_records_from_dict(workspace_edit)

        if not records:
            session.status = "applied"
            return [], session

        # Get unique files to backup
        files_to_backup = self._get_files_to_backup(records, workspace_path)

        # Backup files before modifying
        self._backup_manager.backup_files(session, files_to_backup)

        try:
            # Apply edits to files
            self._apply_edits(records, workspace_path)

            # Update session status
            session.status = "applied"

            # Write manifest and request files
            self._backup_manager.write_request_json(session)
            self._backup_manager.write_manifest(session)

            return records, session

        except Exception as e:
            # Restore all files on failure
            logger.error(f"Apply failed, restoring files: {e}")
            self._backup_manager.restore(session)
            session.status = "failed"
            raise

    def _extract_edit_records(
        self,
        workspace_edit: dict[str, Any],
        client: LSPClient,
    ) -> list[RenameEditRecord]:
        """Extract RenameEditRecord from WorkspaceEdit.

        Args:
            workspace_edit: LSP WorkspaceEdit response
            client: LSP client for workspace path

        Returns:
            List of RenameEditRecord objects
        """
        return self._extract_edit_records_from_dict(workspace_edit)

    def _extract_edit_records_from_dict(
        self,
        workspace_edit: dict[str, Any],
    ) -> list[RenameEditRecord]:
        """Extract RenameEditRecord from WorkspaceEdit dict.

        This method does not require an LSPClient and is used by
        the synchronous `*_from_edit()` methods.

        Args:
            workspace_edit: LSP WorkspaceEdit response

        Returns:
            List of RenameEditRecord objects
        """
        records: list[RenameEditRecord] = []
        workspace_path = self._backup_manager._workspace_path

        # Get documentChanges (we only support TextDocumentEdit, not file operations)
        document_changes = workspace_edit.get("documentChanges", [])

        if not document_changes:
            # Fallback to changes field
            changes = workspace_edit.get("changes", {})
            for uri, edits in changes.items():
                file_path = normalize_uri_to_absolute(uri, workspace_path)
                full_path = workspace_path / file_path
                content = full_path.read_text() if full_path.exists() else ""
                records.extend(self._create_edit_records(file_path, content, edits))
        else:
            for doc_change in document_changes:
                # Skip file operations (have 'kind' field)
                if "kind" in doc_change:
                    continue

                text_doc = doc_change.get("textDocument", {})
                uri = text_doc.get("uri", "")
                file_path = normalize_uri_to_absolute(uri, workspace_path)
                full_path = workspace_path / file_path
                content = full_path.read_text() if full_path.exists() else ""
                edits = doc_change.get("edits", [])
                records.extend(self._create_edit_records(file_path, content, edits))

        return records

    def _create_edit_records(
        self,
        file_path: str,
        content: str,
        edits: list[dict[str, Any]],
    ) -> list[RenameEditRecord]:
        """Create RenameEditRecord objects from a list of edits.

        Args:
            file_path: Relative path to the file
            content: File content for extracting old_text
            edits: List of LSP TextEdit objects

        Returns:
            List of RenameEditRecord objects
        """
        records: list[RenameEditRecord] = []
        for edit in edits:
            range_obj = Range.from_dict(edit.get("range", {}))
            old_text = self._extract_text_at_range(content, range_obj)
            new_text = edit.get("newText", "")
            records.append(RenameEditRecord(
                file=file_path,
                range=range_obj,
                old_text=old_text,
                new_text=new_text,
            ))
        return records

    def _extract_text_at_range(self, content: str, range_obj: Range) -> str:
        """Extract text from content at the given range.

        Args:
            content: File content
            range_obj: Range to extract

        Returns:
            Text at the given range
        """
        lines = content.split("\n")
        start_line = range_obj.start.line
        start_char = range_obj.start.character
        end_line = range_obj.end.line
        end_char = range_obj.end.character

        if start_line == end_line:
            # Single line
            if start_line < len(lines):
                return lines[start_line][start_char:end_char]
            return ""

        # Multi-line (not typical for rename, but handle it)
        result = []
        for i in range(start_line, end_line + 1):
            if i >= len(lines):
                break
            if i == start_line:
                result.append(lines[i][start_char:])
            elif i == end_line:
                result.append(lines[i][:end_char])
            else:
                result.append(lines[i])

        return "\n".join(result)

    def _get_files_to_backup(
        self,
        records: list[RenameEditRecord],
        workspace_path: Path,
    ) -> list[Path]:
        """Get unique file paths that need to be backed up.

        Args:
            records: List of edit records
            workspace_path: Workspace root path

        Returns:
            List of unique absolute file paths
        """
        unique_files: set[Path] = set()
        for record in records:
            full_path = workspace_path / record.file
            unique_files.add(full_path)
        return list(unique_files)

    def _apply_edits(
        self,
        records: list[RenameEditRecord],
        workspace_path: Path,
    ) -> None:
        """Apply edits to files.

        Edits are applied bottom-up (reverse sort by start position) to avoid
        offset shifts from earlier edits affecting later ones.

        Args:
            records: List of edit records to apply
            workspace_path: Workspace root path
        """
        # Group records by file
        by_file: dict[str, list[RenameEditRecord]] = {}
        for record in records:
            if record.file not in by_file:
                by_file[record.file] = []
            by_file[record.file].append(record)

        # Apply edits to each file
        for file_path, file_records in by_file.items():
            full_path = workspace_path / file_path
            if not full_path.exists():
                continue

            content = full_path.read_text()
            lines = content.split("\n")

            # Sort records by position (reverse order for bottom-up application)
            sorted_records = sorted(
                file_records,
                key=lambda r: (r.range.start.line, r.range.start.character),
                reverse=True,
            )

            # Apply each edit
            for record in sorted_records:
                start_line = record.range.start.line
                start_char = record.range.start.character
                end_line = record.range.end.line
                end_char = record.range.end.character

                if start_line == end_line:
                    # Single line edit
                    if start_line < len(lines):
                        line = lines[start_line]
                        lines[start_line] = (
                            line[:start_char] + record.new_text + line[end_char:]
                        )
                else:
                    # Multi-line edit (replace entire range)
                    new_lines = record.new_text.split("\n")
                    if start_line < len(lines):
                        # Build the replacement
                        prefix = lines[start_line][:start_char]
                        suffix = lines[end_line][end_char:] if end_line < len(lines) else ""

                        new_lines[0] = prefix + new_lines[0]
                        new_lines[-1] = new_lines[-1] + suffix

                        # Replace the lines
                        lines = (
                            lines[:start_line]
                            + new_lines
                            + lines[end_line + 1 :]
                        )

            # Write back to file
            full_path.write_text("\n".join(lines))
