# pyright: reportUnannotatedClassAttribute=false
# pyright: reportAny=false
"""Backup manager for LSP rename operations.

Manages session-based backups for atomic file modifications during rename operations.
This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from llm_lsp_cli.output.formatter import Position


@dataclass
class RenameSession:
    """Represents an active rename operation with backup state."""

    session_id: str
    workspace_path: Path
    request_file: str
    request_position: Position
    new_name: str
    timestamp: datetime
    backup_dir: Path
    affected_files: dict[Path, Path] = field(default_factory=dict)
    status: Literal["pending", "applied", "rolled_back", "failed"] = "pending"


class BackupManager:
    """Manages rename session backups.

    Provides backup-and-restore functionality for atomic file modifications
    during LSP rename operations.
    """

    SESSIONS_DIR = ".llm-lsp-cli/rename_sessions"

    def __init__(self, workspace_path: Path):
        """Initialize the backup manager.

        Args:
            workspace_path: Root path of the workspace
        """
        self._workspace_path = Path(workspace_path).resolve()
        self._sessions: dict[str, RenameSession] = {}

    def create_session(
        self,
        file_path: str,
        position: Position,
        new_name: str,
    ) -> RenameSession:
        """Create a new rename session with semi-deterministic ID.

        Args:
            file_path: Relative path to the file being renamed
            position: Position in the file (0-based)
            new_name: New name for the symbol

        Returns:
            RenameSession with generated session_id
        """
        # Generate semi-deterministic session ID
        timestamp = datetime.now()
        session_id = self._generate_session_id(
            file_path=str(self._workspace_path / file_path),
            position=position,
            new_name=new_name,
            timestamp=timestamp,
        )

        # Create backup directory path (not created yet - lazy)
        backup_dir = self._workspace_path / self.SESSIONS_DIR / session_id

        session = RenameSession(
            session_id=session_id,
            workspace_path=self._workspace_path,
            request_file=file_path,
            request_position=position,
            new_name=new_name,
            timestamp=timestamp,
            backup_dir=backup_dir,
            affected_files={},
            status="pending",
        )

        self._sessions[session_id] = session
        return session

    def _generate_session_id(
        self,
        file_path: str,
        position: Position,
        new_name: str,
        timestamp: datetime,
    ) -> str:
        """Generate semi-deterministic session ID.

        Format: rename_{hash12}_{ISO_date}
        Hash is based on workspace + file + position + new_name + minute_timestamp
        """
        # Round timestamp to minute for semi-determinism
        minute_ts = timestamp.strftime("%Y%m%dT%H%M")

        # Create hash input
        hash_input = f"{file_path}:{position.line}:{position.character}:{new_name}:{minute_ts}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

        # Format: rename_{hash}_{ISO_date}
        iso_date = timestamp.strftime("%Y%m%dT%H%M")
        return f"rename_{hash_value}_{iso_date}"

    def backup_files(
        self,
        session: RenameSession,
        files: list[Path],
    ) -> None:
        """Backup files before modification.

        Args:
            session: RenameSession to update
            files: List of absolute file paths to backup
        """
        # Create backup directory
        session.backup_dir.mkdir(parents=True, exist_ok=True)

        for file_path in files:
            if not file_path.exists():
                continue

            # Compute relative path for directory structure preservation
            try:
                rel_path = file_path.relative_to(self._workspace_path)
            except ValueError:
                rel_path = Path(file_path.name)

            backup_path = session.backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file to backup
            shutil.copy2(file_path, backup_path)

            # Update mapping
            session.affected_files[file_path] = backup_path

    def restore(self, session: RenameSession) -> None:
        """Restore files from backup.

        Args:
            session: RenameSession with backup to restore
        """
        for original_path, backup_path in session.affected_files.items():
            if backup_path.exists():
                shutil.copy2(backup_path, original_path)

        session.status = "rolled_back"

    def restore_by_id(self, session_id: str) -> None:
        """Restore files from backup by session ID.

        Args:
            session_id: ID of the session to restore

        Raises:
            ValueError: If session not found
        """
        # Check memory first
        if session_id in self._sessions:
            self.restore(self._sessions[session_id])
            return

        # Look for session on disk
        sessions_dir = self._workspace_path / self.SESSIONS_DIR
        session_dir = sessions_dir / session_id

        if not session_dir.exists():
            raise ValueError(f"Session not found: {session_id}")

        # Load manifest to get affected files
        manifest_path = session_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"Session manifest not found: {session_id}")

        manifest = json.loads(manifest_path.read_text())
        affected_files = {
            Path(orig): session_dir / backup_name
            for orig, backup_name in manifest.get("affected_files", {}).items()
        }

        # Restore files
        for original_path, backup_path in affected_files.items():
            if backup_path.exists():
                original_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, original_path)

        # Clean up session directory after successful restore
        shutil.rmtree(session_dir, ignore_errors=True)

    def cleanup(self, session: RenameSession) -> None:
        """Remove backup directory after successful apply.

        Args:
            session: RenameSession to clean up
        """
        if session.backup_dir.exists():
            shutil.rmtree(session.backup_dir, ignore_errors=True)

    def write_manifest(self, session: RenameSession) -> None:
        """Write manifest.json with session metadata.

        Args:
            session: RenameSession to write manifest for
        """
        manifest_path = session.backup_dir / "manifest.json"

        manifest_data = {
            "session_id": session.session_id,
            "timestamp": session.timestamp.isoformat(),
            "affected_files": {
                str(orig): str(backup)
                for orig, backup in session.affected_files.items()
            },
            "status": session.status,
        }

        manifest_path.write_text(json.dumps(manifest_data, indent=2))

    def write_request_json(self, session: RenameSession) -> None:
        """Write request.json with original request details.

        Args:
            session: RenameSession to write request.json for
        """
        session.backup_dir.mkdir(parents=True, exist_ok=True)
        request_path = session.backup_dir / "request.json"

        request_data = {
            "file": session.request_file,
            "position": {
                "line": session.request_position.line,
                "character": session.request_position.character,
            },
            "new_name": session.new_name,
        }

        request_path.write_text(json.dumps(request_data, indent=2))
