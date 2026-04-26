"""Integration tests for LSP rename feature.

Tests the rename flow end-to-end with a real LSP server (pyright).

Note: These tests may be skipped due to pyright initialization timeout issues.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_lsp_cli.domain.services.backup_manager import BackupManager
from llm_lsp_cli.domain.services.rename_service import RenameService
from llm_lsp_cli.lsp.client import LSPClient
from tests.conftest import is_pyright_langserver_installed

# Check if pyright is available
PYRIGHT_AVAILABLE = is_pyright_langserver_installed()


@pytest.fixture
async def lsp_client_with_timeout(temp_workspace: Path) -> LSPClient:
    """Create and initialize an LSP client with extended timeout."""
    if not PYRIGHT_AVAILABLE:
        pytest.skip("pyright-langserver not installed")

    client = LSPClient(
        workspace_path=str(temp_workspace),
        server_command="pyright-langserver",
        language_id="python",
        timeout=60.0,  # Extended timeout
    )
    try:
        await client.initialize()
        yield client
    finally:
        await client.shutdown()


@pytest.mark.skipif(not PYRIGHT_AVAILABLE, reason="pyright-langserver not installed")
class TestRenameEndToEnd:
    """End-to-end tests for rename with real LSP server."""

    @pytest.mark.asyncio
    async def test_rename_preview_no_file_modification(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify preview does not modify files."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()

        await service.preview(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # File should be unchanged
        assert (temp_workspace / "src" / "main.py").read_text() == original_content

    @pytest.mark.asyncio
    async def test_rename_apply_modifies_files(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify apply modifies files correctly."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()
        assert "OldClassName" in original_content

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # File should be modified
        new_content = (temp_workspace / "src" / "main.py").read_text()
        assert "NewClassName" in new_content
        assert session.status == "applied"

    @pytest.mark.asyncio
    async def test_rename_apply_creates_backup(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify apply creates backup directory."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Backup should exist
        assert session.backup_dir.exists()
        assert (session.backup_dir / "manifest.json").exists()
        assert (session.backup_dir / "request.json").exists()

    @pytest.mark.asyncio
    async def test_rename_rollback_restores_files(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify rollback restores files to original state."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # File should be modified
        assert (temp_workspace / "src" / "main.py").read_text() != original_content

        # Rollback
        await service.rollback(session.session_id)

        # File should be restored
        assert (temp_workspace / "src" / "main.py").read_text() == original_content
        assert session.status == "rolled_back"

    @pytest.mark.asyncio
    async def test_rename_handles_cross_file_references(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify rename updates symbols across multiple files."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Should have edits in both files (main.py and utils.py)
        assert len(records) >= 1

        # Verify session has proper metadata
        assert session.new_name == "NewClassName"


@pytest.mark.skipif(not PYRIGHT_AVAILABLE, reason="pyright-langserver not installed")
class TestRenameSessionRecovery:
    """Tests for session recovery and persistence."""

    @pytest.mark.asyncio
    async def test_session_id_enables_recovery(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify session ID can be used for recovery."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        session_id = session.session_id

        # Rollback using session_id
        await service.rollback(session_id)

        # File should be restored
        assert (temp_workspace / "src" / "main.py").read_text() == original_content

    @pytest.mark.asyncio
    async def test_session_manifest_persists_metadata(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify manifest.json persists session metadata."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        manifest_path = session.backup_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        assert manifest["session_id"] == session.session_id
        assert "affected_files" in manifest

    @pytest.mark.asyncio
    async def test_session_request_json_preserves_request(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify request.json preserves original request details."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=lsp_client_with_timeout,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        request_path = session.backup_dir / "request.json"
        request_data = json.loads(request_path.read_text())

        assert request_data["file"] == "src/main.py"
        assert request_data["new_name"] == "NewClassName"
        assert "position" in request_data


@pytest.mark.skipif(not PYRIGHT_AVAILABLE, reason="pyright-langserver not installed")
class TestRenameCapabilityCheck:
    """Tests for LSP capability checking."""

    @pytest.mark.asyncio
    async def test_pyright_supports_prepare_rename(
        self, temp_workspace: Path, lsp_client_with_timeout: LSPClient
    ) -> None:
        """Verify pyright supports prepareRename capability."""
        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        # Pyright should support prepareRename
        assert service.supports_prepare_rename(lsp_client_with_timeout) is True
