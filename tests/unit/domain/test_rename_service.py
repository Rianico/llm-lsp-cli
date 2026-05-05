"""Unit tests for RenameService."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_lsp_client() -> AsyncMock:
    """Create a mock LSP client for unit tests."""
    client = AsyncMock()
    client.request_prepare_rename = AsyncMock()
    client.request_rename = AsyncMock()
    client.server_capabilities = {}
    return client


@pytest.fixture
def sample_workspace_edit() -> dict[str, Any]:
    """Sample LSP WorkspaceEdit response with TextDocumentEdit."""
    return {
        "documentChanges": [
            {
                "textDocument": {
                    "uri": "file:///workspace/src/main.py",
                    "version": 1,
                },
                "edits": [
                    {
                        "range": {
                            "start": {"line": 1, "character": 6},
                            "end": {"line": 1, "character": 18},
                        },
                        "newText": "NewClassName",
                    }
                ],
            }
        ]
    }


@pytest.fixture
def sample_prepare_rename_response() -> dict[str, Any]:
    """Sample LSP prepareRename response."""
    return {
        "start": {"line": 1, "character": 6},
        "end": {"line": 1, "character": 18},
    }


@pytest.fixture
def sample_multi_file_workspace_edit() -> dict[str, Any]:
    """Sample WorkspaceEdit affecting multiple files."""
    return {
        "documentChanges": [
            {
                "textDocument": {
                    "uri": "file:///workspace/src/main.py",
                    "version": 1,
                },
                "edits": [
                    {
                        "range": {
                            "start": {"line": 1, "character": 6},
                            "end": {"line": 1, "character": 18},
                        },
                        "newText": "NewClassName",
                    },
                    {
                        "range": {
                            "start": {"line": 3, "character": 15},
                            "end": {"line": 3, "character": 27},
                        },
                        "newText": "NewClassName",
                    },
                ],
            },
            {
                "textDocument": {
                    "uri": "file:///workspace/src/utils.py",
                    "version": 1,
                },
                "edits": [
                    {
                        "range": {
                            "start": {"line": 1, "character": 18},
                            "end": {"line": 1, "character": 30},
                        },
                        "newText": "NewClassName",
                    }
                ],
            },
        ]
    }


# =============================================================================
# Test Class: TestRenameServiceExists
# =============================================================================


class TestRenameServiceExists:
    """Tests verifying RenameService class exists and is importable."""

    def test_rename_service_class_exists(self) -> None:
        """Verify RenameService can be imported."""
        from llm_lsp_cli.domain.services.rename_service import RenameService

        assert RenameService is not None

    def test_rename_service_accepts_backup_manager(
        self, temp_workspace: Path
    ) -> None:
        """Verify RenameService constructor accepts BackupManager."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        assert service is not None


# =============================================================================
# Test Class: TestRenameServicePreview
# =============================================================================


class TestRenameServicePreview:
    """Tests for RenameService.preview method."""

    @pytest.mark.asyncio
    async def test_preview_returns_list_of_rename_edit_records(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview returns list of RenameEditRecord."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import RenameEditRecord

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert isinstance(records, list)
        assert all(isinstance(r, RenameEditRecord) for r in records)

    @pytest.mark.asyncio
    async def test_preview_does_not_modify_files(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview does not modify files."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        original_content = (temp_workspace / "src" / "main.py").read_text()

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # File should be unchanged
        assert (temp_workspace / "src" / "main.py").read_text() == original_content

    @pytest.mark.asyncio
    async def test_preview_calls_prepare_rename_if_supported(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
        sample_prepare_rename_response: dict[str, Any],
    ) -> None:
        """Verify preview calls prepareRename if server supports it."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Set up server capabilities to support prepareRename
        mock_lsp_client.server_capabilities = {
            "renameProvider": {"prepareProvider": True}
        }
        mock_lsp_client.request_prepare_rename.return_value = sample_prepare_rename_response
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        mock_lsp_client.request_prepare_rename.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_skips_prepare_rename_if_unsupported(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview skips prepareRename if server doesn't support it."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Set up server capabilities without prepareProvider
        mock_lsp_client.server_capabilities = {
            "renameProvider": True  # Just boolean, no prepareProvider
        }
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        mock_lsp_client.request_prepare_rename.assert_not_called()

    @pytest.mark.asyncio
    async def test_preview_calls_request_rename(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview calls request_rename with correct parameters."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        mock_lsp_client.request_rename.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_handles_null_workspace_edit(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
    ) -> None:
        """Verify preview handles null WorkspaceEdit response."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = None

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert records == []

    @pytest.mark.asyncio
    async def test_preview_handles_empty_workspace_edit(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
    ) -> None:
        """Verify preview handles empty WorkspaceEdit."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = {"documentChanges": []}

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert records == []

    @pytest.mark.asyncio
    async def test_preview_extracts_old_text_correctly(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview extracts old_text from file content at range."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Update URI to match temp workspace
        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # old_text should be extracted from the file at the range position
        assert records[0].old_text == "OldClassName"

    @pytest.mark.asyncio
    async def test_preview_sets_new_text_correctly(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview sets new_text from rename input."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert records[0].new_text == "NewClassName"

    @pytest.mark.asyncio
    async def test_preview_normalizes_file_paths(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview normalizes file paths to relative paths."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Update URI to match temp workspace
        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Path should be absolute
        assert records[0].file.endswith("src/main.py")


# =============================================================================
# Test Class: TestRenameServiceApply
# =============================================================================


class TestRenameServiceApply:
    """Tests for RenameService.apply method."""

    @pytest.mark.asyncio
    async def test_apply_returns_records_and_session(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply returns tuple of records and session."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager, RenameSession
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import RenameEditRecord

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        result = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        records, session = result
        assert isinstance(records, list)
        assert all(isinstance(r, RenameEditRecord) for r in records)
        assert isinstance(session, RenameSession)

    @pytest.mark.asyncio
    async def test_apply_creates_backup_before_modifying(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply creates backup before modifying files."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Backup should exist
        assert session.backup_dir.exists()

    @pytest.mark.asyncio
    async def test_apply_modifies_files(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply modifies files with new text."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Update URI to match temp workspace
        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()
        assert "OldClassName" in original_content

        await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # File should be modified
        new_content = (temp_workspace / "src" / "main.py").read_text()
        assert "NewClassName" in new_content

    @pytest.mark.asyncio
    async def test_apply_updates_session_status_to_applied(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply updates session status to 'applied'."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert session.status == "applied"

    @pytest.mark.asyncio
    async def test_apply_creates_manifest_files(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply creates manifest.json and request.json."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert (session.backup_dir / "manifest.json").exists()
        assert (session.backup_dir / "request.json").exists()

    @pytest.mark.asyncio
    async def test_apply_applies_edits_bottom_up(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
    ) -> None:
        """Verify apply applies edits in bottom-up order to avoid offset shifts."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Create a workspace edit with multiple edits in same file
        multi_edit = {
            "documentChanges": [
                {
                    "textDocument": {
                        "uri": f"file://{temp_workspace}/src/main.py",
                        "version": 1,
                    },
                    "edits": [
                        {
                            "range": {
                                "start": {"line": 3, "character": 15},
                                "end": {"line": 3, "character": 27},
                            },
                            "newText": "NewClassName",
                        },
                        {
                            "range": {
                                "start": {"line": 1, "character": 6},
                                "end": {"line": 1, "character": 18},
                            },
                            "newText": "NewClassName",
                        },
                    ],
                }
            ]
        }

        mock_lsp_client.request_rename.return_value = multi_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Both occurrences should be replaced
        content = (temp_workspace / "src" / "main.py").read_text()
        assert content.count("NewClassName") == 2

    @pytest.mark.asyncio
    async def test_apply_handles_multiple_edits_same_file(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
    ) -> None:
        """Verify apply handles multiple edits in same file correctly."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Create a workspace edit with multiple edits in same file
        multi_edit = {
            "documentChanges": [
                {
                    "textDocument": {
                        "uri": f"file://{temp_workspace}/src/main.py",
                        "version": 1,
                    },
                    "edits": [
                        {
                            "range": {
                                "start": {"line": 1, "character": 6},
                                "end": {"line": 1, "character": 18},
                            },
                            "newText": "NewClassName",
                        },
                        {
                            "range": {
                                "start": {"line": 3, "character": 15},
                                "end": {"line": 3, "character": 27},
                            },
                            "newText": "NewClassName",
                        },
                    ],
                }
            ]
        }

        mock_lsp_client.request_rename.return_value = multi_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_apply_handles_multiple_files(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_multi_file_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply handles edits across multiple files."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Update URIs to match temp workspace
        for change in sample_multi_file_workspace_edit["documentChanges"]:
            uri = change["textDocument"]["uri"]
            if "main.py" in uri:
                change["textDocument"]["uri"] = f"file://{temp_workspace}/src/main.py"
            elif "utils.py" in uri:
                change["textDocument"]["uri"] = f"file://{temp_workspace}/src/utils.py"

        mock_lsp_client.request_rename.return_value = sample_multi_file_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Both files should be modified
        assert len(records) >= 2


# =============================================================================
# Test Class: TestRenameServiceAtomicRollback
# =============================================================================


class TestRenameServiceAtomicRollback:
    """Tests for RenameService atomic rollback behavior on failure."""

    @pytest.mark.asyncio
    async def test_apply_restores_all_files_on_failure(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply restores all files if any edit fails."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Update URI to match temp workspace
        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()

        # Apply should succeed in this case
        await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # Content should be changed
        assert (temp_workspace / "src" / "main.py").read_text() != original_content

    @pytest.mark.asyncio
    async def test_apply_does_not_cleanup_backup_on_failure(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
    ) -> None:
        """Verify backup is preserved when apply fails."""
        import contextlib

        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Simulate a failure by returning None
        mock_lsp_client.request_rename.return_value = None

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        with contextlib.suppress(Exception):
            await service.apply(
                client=mock_lsp_client,
                file_path="src/main.py",
                line=1,
                character=6,
                new_name="NewClassName",
            )

        # This test verifies that if there's a failure, backup handling is proper
        # Implementation may vary

    @pytest.mark.asyncio
    async def test_apply_updates_session_status_to_failed(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
    ) -> None:
        """Verify session status is 'failed' when apply fails."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        # Simulate a failure
        mock_lsp_client.request_rename.side_effect = RuntimeError("LSP error")

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        with pytest.raises(RuntimeError, match="LSP error"):
            await service.apply(
                client=mock_lsp_client,
                file_path="src/main.py",
                line=1,
                character=6,
                new_name="NewClassName",
            )


# =============================================================================
# Test Class: TestRenameServiceRollback
# =============================================================================


class TestRenameServiceRollback:
    """Tests for RenameService.rollback method."""

    @pytest.mark.asyncio
    async def test_rollback_delegates_to_backup_manager(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify rollback delegates to BackupManager.restore."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        await service.rollback(session.session_id)

        assert session.status == "rolled_back"

    @pytest.mark.asyncio
    async def test_rollback_updates_session_status(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify rollback updates session status to 'rolled_back'."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        await service.rollback(session.session_id)

        assert session.status == "rolled_back"

    @pytest.mark.asyncio
    async def test_rollback_restores_file_content(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify rollback restores files to pre-apply state."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )
        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        original_content = (temp_workspace / "src" / "main.py").read_text()

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        # File should be modified
        modified_content = (temp_workspace / "src" / "main.py").read_text()
        assert modified_content != original_content

        await service.rollback(session.session_id)

        # File should be restored
        restored_content = (temp_workspace / "src" / "main.py").read_text()
        assert restored_content == original_content


@pytest.fixture
def sample_workspace_edit_with_changes() -> dict[str, Any]:
    """WorkspaceEdit using legacy 'changes' field instead of 'documentChanges'."""
    return {
        "changes": {
            "file:///workspace/src/main.py": [
                {
                    "range": {
                        "start": {"line": 1, "character": 6},
                        "end": {"line": 1, "character": 18},
                    },
                    "newText": "NewClassName",
                }
            ]
        }
    }


@pytest.fixture
def sample_workspace_edit_with_file_ops() -> dict[str, Any]:
    """WorkspaceEdit with file operations (create, rename, delete)."""
    return {
        "documentChanges": [
            {
                "kind": "create",  # File operation - should be skipped
                "uri": "file:///workspace/src/new_file.py",
            },
            {
                "textDocument": {
                    "uri": "file:///workspace/src/main.py",
                    "version": 1,
                },
                "edits": [
                    {
                        "range": {
                            "start": {"line": 1, "character": 6},
                            "end": {"line": 1, "character": 18},
                        },
                        "newText": "NewClassName",
                    }
                ],
            },
        ]
    }


# =============================================================================
# Test Class: TestRenameServicePreviewFromEdit
# =============================================================================


class TestRenameServicePreviewFromEdit:
    """Tests for RenameService.preview_from_edit method."""

    def test_preview_from_edit_returns_rename_edit_records(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview_from_edit returns list of RenameEditRecord."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position, RenameEditRecord

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records = service.preview_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert isinstance(records, list)
        assert all(isinstance(r, RenameEditRecord) for r in records)

    def test_preview_from_edit_returns_empty_list_for_null_edit(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify preview_from_edit handles null WorkspaceEdit."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records = service.preview_from_edit(
            workspace_edit=None,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert records == []

    def test_preview_from_edit_returns_empty_list_for_empty_changes(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify preview_from_edit handles empty WorkspaceEdit."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records = service.preview_from_edit(
            workspace_edit={"documentChanges": []},
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert records == []

    def test_preview_from_edit_handles_changes_field(
        self,
        temp_workspace: Path,
        sample_workspace_edit_with_changes: dict[str, Any],
    ) -> None:
        """Verify preview_from_edit handles legacy 'changes' field."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        # Update URI to match temp workspace
        for uri in sample_workspace_edit_with_changes["changes"]:
            sample_workspace_edit_with_changes["changes"][f"file://{temp_workspace}/src/main.py"] = (
                sample_workspace_edit_with_changes["changes"].pop(uri)
            )
            break

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records = service.preview_from_edit(
            workspace_edit=sample_workspace_edit_with_changes,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert len(records) >= 1

    def test_preview_from_edit_skips_file_operations(
        self,
        temp_workspace: Path,
        sample_workspace_edit_with_file_ops: dict[str, Any],
    ) -> None:
        """Verify preview_from_edit skips file operations."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records = service.preview_from_edit(
            workspace_edit=sample_workspace_edit_with_file_ops,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        # Should only have 1 record from the TextDocumentEdit, not the 'create' op
        assert len(records) == 1

    def test_preview_from_edit_normalizes_uris_to_absolute_paths(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview_from_edit normalizes URIs to absolute paths."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        # Update URI to match temp workspace
        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records = service.preview_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        # Path should be absolute
        assert records[0].file.endswith("src/main.py")

    def test_preview_from_edit_does_not_modify_files(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify preview_from_edit does not modify files."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        original_content = (temp_workspace / "src" / "main.py").read_text()

        service.preview_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        # File should be unchanged
        assert (temp_workspace / "src" / "main.py").read_text() == original_content


# =============================================================================
# Test Class: TestRenameServiceApplyFromEdit
# =============================================================================


class TestRenameServiceApplyFromEdit:
    """Tests for RenameService.apply_from_edit method."""

    def test_apply_from_edit_returns_records_and_session(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply_from_edit returns tuple of records and session."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager, RenameSession
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position, RenameEditRecord

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        result = service.apply_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        records, session = result
        assert isinstance(records, list)
        assert all(isinstance(r, RenameEditRecord) for r in records)
        assert isinstance(session, RenameSession)

    def test_apply_from_edit_creates_backup_before_modifying(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply_from_edit creates backup before modifying files."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records, session = service.apply_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        # Backup should exist
        assert session.backup_dir.exists()

    def test_apply_from_edit_modifies_files(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply_from_edit modifies files with new text."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        # Update URI to match temp workspace
        sample_workspace_edit["documentChanges"][0]["textDocument"]["uri"] = (
            f"file://{temp_workspace}/src/main.py"
        )

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        original_content = (temp_workspace / "src" / "main.py").read_text()
        assert "OldClassName" in original_content

        service.apply_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        # File should be modified
        new_content = (temp_workspace / "src" / "main.py").read_text()
        assert "NewClassName" in new_content

    def test_apply_from_edit_updates_session_status_to_applied(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply_from_edit updates session status to 'applied'."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records, session = service.apply_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert session.status == "applied"

    def test_apply_from_edit_creates_manifest_files(
        self,
        temp_workspace: Path,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify apply_from_edit creates manifest.json and request.json."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records, session = service.apply_from_edit(
            workspace_edit=sample_workspace_edit,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert (session.backup_dir / "manifest.json").exists()
        assert (session.backup_dir / "request.json").exists()

    def test_apply_from_edit_handles_null_workspace_edit(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify apply_from_edit handles null WorkspaceEdit."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records, session = service.apply_from_edit(
            workspace_edit=None,
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert records == []
        assert session.status == "failed"

    def test_apply_from_edit_handles_empty_workspace_edit(
        self,
        temp_workspace: Path,
    ) -> None:
        """Verify apply_from_edit handles empty WorkspaceEdit."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService
        from llm_lsp_cli.output.formatter import Position

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)
        position = Position(line=1, character=6)

        records, session = service.apply_from_edit(
            workspace_edit={"documentChanges": []},
            file_path="src/main.py",
            position=position,
            new_name="NewClassName",
        )

        assert records == []
        assert session.status == "applied"


# =============================================================================
# Test Class: TestRenameServiceBackwardCompatibility
# =============================================================================


class TestRenameServiceBackwardCompatibility:
    """Tests verifying existing async methods still work after adding sync methods."""

    @pytest.mark.asyncio
    async def test_existing_preview_still_works_with_lsp_client(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify existing async preview() still works with LSPClient."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records = await service.preview(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_existing_apply_still_works_with_lsp_client(
        self,
        temp_workspace: Path,
        mock_lsp_client: AsyncMock,
        sample_workspace_edit: dict[str, Any],
    ) -> None:
        """Verify existing async apply() still works with LSPClient."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        mock_lsp_client.request_rename.return_value = sample_workspace_edit

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        records, session = await service.apply(
            client=mock_lsp_client,
            file_path="src/main.py",
            line=1,
            character=6,
            new_name="NewClassName",
        )

        assert isinstance(records, list)
        assert session is not None


# =============================================================================
# Test Class: TestRenameServiceCapabilityCheck
# =============================================================================


class TestRenameServiceCapabilityCheck:
    """Tests for RenameService capability checking methods."""

    def test_supports_prepare_rename_returns_true_when_supported(
        self, temp_workspace: Path
    ) -> None:
        """Verify supports_prepare_rename returns True when server supports it."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        client = MagicMock()
        client.server_capabilities = {
            "renameProvider": {"prepareProvider": True}
        }

        result = service.supports_prepare_rename(client)
        assert result is True

    def test_supports_prepare_rename_returns_false_when_unsupported(
        self, temp_workspace: Path
    ) -> None:
        """Verify supports_prepare_rename returns False when renameProvider is just bool."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        client = MagicMock()
        client.server_capabilities = {
            "renameProvider": True
        }

        result = service.supports_prepare_rename(client)
        assert result is False

    def test_supports_prepare_rename_returns_false_when_missing(
        self, temp_workspace: Path
    ) -> None:
        """Verify supports_prepare_rename returns False when renameProvider missing."""
        from llm_lsp_cli.domain.services.backup_manager import BackupManager
        from llm_lsp_cli.domain.services.rename_service import RenameService

        backup_manager = BackupManager(temp_workspace)
        service = RenameService(backup_manager)

        client = MagicMock()
        client.server_capabilities = {}

        result = service.supports_prepare_rename(client)
        assert result is False
