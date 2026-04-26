"""Unit tests for BackupManager service."""

from __future__ import annotations

from dataclasses import is_dataclass
from datetime import datetime
from pathlib import Path

import pytest

from llm_lsp_cli.output.formatter import Position

# =============================================================================
# Test Class: TestBackupManagerExists
# =============================================================================


class TestBackupManagerExists:
    """Tests verifying BackupManager class exists and is importable."""

    def test_backup_manager_class_exists(self) -> None:
        """Verify BackupManager can be imported."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        assert BackupManager is not None

    def test_backup_manager_has_sessions_dir_constant(self) -> None:
        """Verify BackupManager has SESSIONS_DIR constant."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        assert hasattr(BackupManager, "SESSIONS_DIR")
        assert BackupManager.SESSIONS_DIR == ".llm-lsp-cli/rename_sessions"


# =============================================================================
# Test Class: TestRenameSessionDataclass
# =============================================================================


class TestRenameSessionDataclass:
    """Tests verifying RenameSession dataclass exists with required fields."""

    def test_rename_session_exists(self) -> None:
        """Verify RenameSession can be imported."""
        from llm_lsp_cli.domain.services.backup_manager import RenameSession

        assert RenameSession is not None

    def test_rename_session_is_dataclass(self) -> None:
        """Verify RenameSession is a dataclass."""
        from llm_lsp_cli.domain.services.backup_manager import RenameSession

        assert is_dataclass(RenameSession)

    def test_rename_session_has_required_fields(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify RenameSession has all required fields."""
        from llm_lsp_cli.domain.services.backup_manager import RenameSession

        session = RenameSession(
            session_id="rename_abc123_20260426T1545",
            workspace_path=temp_workspace,
            request_file="src/main.py",
            request_position=sample_position,
            new_name="NewClassName",
            timestamp=datetime.now(),
            backup_dir=temp_workspace
            / ".llm-lsp-cli"
            / "rename_sessions"
            / "rename_abc123_20260426T1545",
            affected_files={},
            status="pending",
        )
        assert session.session_id == "rename_abc123_20260426T1545"
        assert session.workspace_path == temp_workspace
        assert session.request_file == "src/main.py"
        assert session.request_position == sample_position
        assert session.new_name == "NewClassName"
        assert isinstance(session.timestamp, datetime)
        assert session.status == "pending"
        assert session.affected_files == {}


# =============================================================================
# Test Class: TestBackupManagerCreateSession
# =============================================================================


class TestBackupManagerCreateSession:
    """Tests for BackupManager.create_session method."""

    def test_create_session_returns_rename_session(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify create_session returns a RenameSession instance."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager, RenameSession

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        assert isinstance(session, RenameSession)

    def test_create_session_generates_session_id(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify create_session generates a session_id starting with 'rename_'."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        assert session.session_id.startswith("rename_")

    def test_create_session_id_contains_hash(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify session_id contains a 12-char hash component."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        # Format: rename_{hash12}_{ISO_date}
        parts = session.session_id.split("_")
        assert len(parts) >= 3
        # hash is the second part (index 1)
        hash_part = parts[1]
        assert len(hash_part) == 12
        assert hash_part.isalnum()

    def test_create_session_id_contains_timestamp(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify session_id contains an ISO date format."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        # Format contains ISO date: rename_{hash}_{ISO_date}
        # ISO date format: YYYYMMDDTHHMM
        assert "T" in session.session_id  # ISO format has 'T' separator

    def test_create_session_sets_workspace_path(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify create_session sets workspace_path correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        assert session.workspace_path == temp_workspace

    def test_create_session_sets_request_file(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify create_session sets request_file correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        assert session.request_file == "src/main.py"

    def test_create_session_sets_new_name(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify create_session sets new_name correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        assert session.new_name == "NewClassName"

    def test_create_session_sets_pending_status(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify create_session sets initial status to 'pending'."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        assert session.status == "pending"

    def test_create_session_backup_dir_not_created_yet(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_dir is set but not created (lazy creation)."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        # backup_dir should be set but not exist yet
        assert session.backup_dir is not None
        assert not session.backup_dir.exists()

    def test_create_session_is_semi_deterministic(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify same inputs within same minute produce same ID."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session1 = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        session2 = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        # IDs should be identical if created within same minute
        assert session1.session_id == session2.session_id


# =============================================================================
# Test Class: TestBackupManagerBackupFiles
# =============================================================================


class TestBackupManagerBackupFiles:
    """Tests for BackupManager.backup_files method."""

    def test_backup_files_creates_backup_directory(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_files creates backup directory."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)

        assert session.backup_dir.exists()

    def test_backup_files_copies_files_to_backup(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_files copies files to backup directory."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)

        # Check that backup file exists
        backup_file = session.backup_dir / "src" / "main.py"
        assert backup_file.exists()

    def test_backup_files_updates_affected_files_mapping(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_files updates affected_files mapping."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)

        # Check affected_files mapping
        original_path = temp_workspace / "src" / "main.py"
        assert original_path in session.affected_files
        backup_path = session.affected_files[original_path]
        assert backup_path.exists()

    def test_backup_files_preserves_directory_structure(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_files preserves directory structure."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)

        # Check backup preserves src/ structure
        backup_file = session.backup_dir / "src" / "main.py"
        assert backup_file.exists()

    def test_backup_files_handles_single_file(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_files handles a single file correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)

        assert len(session.affected_files) == 1

    def test_backup_files_handles_multiple_files(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify backup_files handles multiple files correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [
            temp_workspace / "src" / "main.py",
            temp_workspace / "src" / "utils.py",
        ]
        manager.backup_files(session, files)

        assert len(session.affected_files) == 2


# =============================================================================
# Test Class: TestBackupManagerRestore
# =============================================================================


class TestBackupManagerRestore:
    """Tests for BackupManager.restore method."""

    def test_restore_copies_files_from_backup(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify restore copies files from backup to original locations."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        original_content = (temp_workspace / "src" / "main.py").read_text()

        manager.backup_files(session, files)

        # Modify the original file
        (temp_workspace / "src" / "main.py").write_text("modified content")

        # Restore
        manager.restore(session)

        # Verify content is restored
        restored_content = (temp_workspace / "src" / "main.py").read_text()
        assert restored_content == original_content

    def test_restore_updates_session_status(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify restore updates session status to 'rolled_back'."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)
        manager.restore(session)

        assert session.status == "rolled_back"

    def test_restore_handles_missing_session(self, temp_workspace: Path) -> None:
        """Verify restore raises error for non-existent session."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)

        with pytest.raises(ValueError, match="Session not found"):
            manager.restore_by_id("nonexistent_session_id")

    def test_restore_preserves_file_content(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify restore preserves original file content exactly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        original_content = (temp_workspace / "src" / "main.py").read_text()

        manager.backup_files(session, files)
        (temp_workspace / "src" / "main.py").write_text("different content")
        manager.restore(session)

        assert (temp_workspace / "src" / "main.py").read_text() == original_content

    def test_restore_handles_multiple_files(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify restore handles multiple files correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [
            temp_workspace / "src" / "main.py",
            temp_workspace / "src" / "utils.py",
        ]
        original_main = (temp_workspace / "src" / "main.py").read_text()
        original_utils = (temp_workspace / "src" / "utils.py").read_text()

        manager.backup_files(session, files)
        (temp_workspace / "src" / "main.py").write_text("modified main")
        (temp_workspace / "src" / "utils.py").write_text("modified utils")
        manager.restore(session)

        assert (temp_workspace / "src" / "main.py").read_text() == original_main
        assert (temp_workspace / "src" / "utils.py").read_text() == original_utils


# =============================================================================
# Test Class: TestBackupManagerCleanup
# =============================================================================


class TestBackupManagerCleanup:
    """Tests for BackupManager.cleanup method."""

    def test_cleanup_removes_backup_directory(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify cleanup removes backup directory."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)
        backup_dir = session.backup_dir

        manager.cleanup(session)

        assert not backup_dir.exists()

    def test_cleanup_handles_already_removed(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify cleanup handles already-removed directory gracefully."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )

        # Should not raise an error
        manager.cleanup(session)


# =============================================================================
# Test Class: TestBackupManagerManifest
# =============================================================================


class TestBackupManagerManifest:
    """Tests for BackupManager manifest and request JSON files."""

    def test_write_manifest_creates_manifest_json(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify write_manifest creates manifest.json file."""

        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)
        manager.write_manifest(session)

        manifest_path = session.backup_dir / "manifest.json"
        assert manifest_path.exists()

    def test_manifest_contains_session_id(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify manifest.json contains session_id."""
        import json

        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)
        manager.write_manifest(session)

        manifest_path = session.backup_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert "session_id" in manifest

    def test_manifest_contains_file_mapping(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify manifest.json contains file mapping."""
        import json

        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        files = [temp_workspace / "src" / "main.py"]
        manager.backup_files(session, files)
        manager.write_manifest(session)

        manifest_path = session.backup_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert "affected_files" in manifest

    def test_write_request_json_creates_request_json(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify write_request_json creates request.json file."""

        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        manager.write_request_json(session)

        request_path = session.backup_dir / "request.json"
        assert request_path.exists()

    def test_request_json_contains_original_request(
        self, temp_workspace: Path, sample_position: Position
    ) -> None:
        """Verify request.json contains original request details."""
        import json

        from llm_lsp_cli.domain.services.backup_manager import BackupManager

        manager = BackupManager(temp_workspace)
        session = manager.create_session(
            file_path="src/main.py",
            position=sample_position,
            new_name="NewClassName",
        )
        manager.write_request_json(session)

        request_path = session.backup_dir / "request.json"
        request_data = json.loads(request_path.read_text())
        assert "file" in request_data
        assert "position" in request_data
        assert "new_name" in request_data
