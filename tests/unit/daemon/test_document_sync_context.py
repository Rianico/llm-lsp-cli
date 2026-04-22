"""Tests verifying DocumentSyncContext does NOT send didClose on exit.

Per ADR-001, files must remain open for the session lifetime.
DocumentSyncContext.__aexit__ should NOT call close_document().

Additionally, DocumentSyncContext should NOT send redundant didOpen notifications
when a file is already open. This is tracked via DiagnosticCache.FileState.is_open.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.daemon import DocumentSyncContext
from llm_lsp_cli.lsp.cache import DiagnosticCache


class TestDocumentSyncContextNoDidClose:
    """Tests verifying DocumentSyncContext does not send didClose."""

    @pytest.mark.asyncio
    async def test_exit_does_not_call_close_document(self, temp_dir: Path) -> None:
        """DocumentSyncContext.__aexit__ must NOT call close_document.

        This test verifies the fix for the bug where didClose was sent on
        context exit, breaking the ADR-001 invariant that files remain open
        for the session lifetime.

        Expected behavior:
        - __aenter__ calls open_document() and returns the URI
        - __aexit__ does NOT call close_document() (file stays open)
        """
        # Create mock client with diagnostic cache
        mock_client = MagicMock()
        mock_client.open_document = AsyncMock(return_value=temp_dir.joinpath("test.py").as_uri())
        mock_client.close_document = AsyncMock()
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test content")

        # Enter and exit context
        async with DocumentSyncContext(mock_client, test_file) as uri:
            # Verify open_document was called on enter
            mock_client.open_document.assert_called_once()
            assert uri == test_file.as_uri()

        # ASSERTION: close_document should NOT be called after exit
        # This is the key test - if this fails, the bug is not fixed
        mock_client.close_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_exit_does_not_call_close_document_on_exception(self, temp_dir: Path) -> None:
        """DocumentSyncContext.__aexit__ must NOT call close_document even on exception.

        Even when an exception occurs within the context, close_document
        should NOT be called per ADR-001.
        """
        # Create mock client with diagnostic cache
        mock_client = MagicMock()
        mock_client.open_document = AsyncMock(return_value=temp_dir.joinpath("test.py").as_uri())
        mock_client.close_document = AsyncMock()
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test content")

        # Enter and exit context with exception
        with pytest.raises(ValueError):
            async with DocumentSyncContext(mock_client, test_file) as _:
                raise ValueError("Test exception")

        # ASSERTION: close_document should NOT be called even on exception
        mock_client.close_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_open_document_is_called_on_enter(self, temp_dir: Path) -> None:
        """DocumentSyncContext.__aenter__ must call open_document.

        This test verifies that opening documents still works correctly.
        """
        # Create mock client with diagnostic cache
        mock_client = MagicMock()
        mock_client.open_document = AsyncMock(return_value=temp_dir.joinpath("test.py").as_uri())
        mock_client.close_document = AsyncMock()
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("def foo(): pass")

        # Enter context
        async with DocumentSyncContext(mock_client, test_file) as uri:
            # Verify open_document was called with correct args
            mock_client.open_document.assert_called_once()
            call_args = mock_client.open_document.call_args
            assert call_args[0][0] == test_file  # First positional arg is file path
            assert "def foo(): pass" in call_args[0][1]  # Second arg is content
            assert uri == test_file.as_uri()

        # Even after exit, close_document should not be called
        mock_client.close_document.assert_not_called()


class TestDocumentSyncContextRedundantDidOpenPrevention:
    """Tests verifying DocumentSyncContext skips didOpen when file is already open.

    Per ADR-001, FileState.is_open tracks whether a file is open in the LSP server.
    DocumentSyncContext must check this flag before sending didOpen to avoid
    redundant notifications that cause LSP server warnings.
    """

    @pytest.mark.asyncio
    async def test_first_request_sends_did_open_and_sets_is_open(self, temp_dir: Path) -> None:
        """First request for a file should send didOpen notification and set is_open.

        DocumentSyncContext must:
        1. Check is_open in cache (False on first request)
        2. Call open_document()
        3. Set is_open=True in cache via on_did_open()
        """
        # Arrange
        mock_client = MagicMock()
        mock_client.open_document = AsyncMock(return_value=temp_dir.joinpath("module.py").as_uri())
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)
        file_path = temp_dir / "module.py"
        file_path.write_text("# test content")

        # Pre-condition: file not tracked as open
        state = await mock_client._diagnostic_cache.get_file_state(file_path.as_uri())
        assert state.is_open is False

        # Act
        async with DocumentSyncContext(mock_client, file_path) as _:
            pass

        # Assert - open_document was called
        assert mock_client.open_document.call_count == 1
        # Assert - is_open is now True (DocumentSyncContext must call on_did_open)
        state = await mock_client._diagnostic_cache.get_file_state(file_path.as_uri())
        assert state.is_open is True, "is_open must be True after DocumentSyncContext sends didOpen"

    @pytest.mark.asyncio
    async def test_second_request_skips_did_open(self, temp_dir: Path) -> None:
        """Second request for same file should NOT send didOpen."""
        # Arrange
        mock_client = MagicMock()
        mock_client.open_document = AsyncMock(return_value=temp_dir.joinpath("module.py").as_uri())
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)
        file_path = temp_dir / "module.py"
        file_path.write_text("# test content")

        # Simulate first request already completed - file is marked as open
        await mock_client._diagnostic_cache.on_did_open(file_path.as_uri())

        # Act - second request
        async with DocumentSyncContext(mock_client, file_path) as _:
            pass

        # Assert - no additional didOpen sent
        # This is the KEY assertion that should FAIL before the fix is applied
        assert mock_client.open_document.call_count == 0, (
            "open_document should NOT be called when file is already open"
        )
        state = await mock_client._diagnostic_cache.get_file_state(file_path.as_uri())
        assert state.is_open is True

    @pytest.mark.asyncio
    async def test_different_files_both_open(self, temp_dir: Path) -> None:
        """Each new file should trigger didOpen independently."""
        # Arrange
        mock_client = MagicMock()
        file_a = temp_dir / "a.py"
        file_a.write_text("# file a")
        file_b = temp_dir / "b.py"
        file_b.write_text("# file b")

        mock_client.open_document = AsyncMock(side_effect=[file_a.as_uri(), file_b.as_uri()])
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)

        # Act
        async with DocumentSyncContext(mock_client, file_a) as uri_a:
            assert uri_a == file_a.as_uri()
        async with DocumentSyncContext(mock_client, file_b) as uri_b:
            assert uri_b == file_b.as_uri()

        # Assert - both files opened
        assert mock_client.open_document.call_count == 2

    @pytest.mark.asyncio
    async def test_document_sync_context_uses_cache_for_open_check(self, temp_dir: Path) -> None:
        """DocumentSyncContext should check cache.is_open before sending didOpen."""
        mock_client = MagicMock()
        mock_client.open_document = AsyncMock(return_value=temp_dir.joinpath("module.py").as_uri())
        mock_client._diagnostic_cache = DiagnosticCache(temp_dir)
        file_path = temp_dir / "module.py"
        file_path.write_text("# test content")

        # Manually mark file as open in cache
        await mock_client._diagnostic_cache.on_did_open(file_path.as_uri())

        # Pre-condition: file is already tracked as open
        state_before = await mock_client._diagnostic_cache.get_file_state(file_path.as_uri())
        assert state_before.is_open is True

        # Act - enter context for already-open file
        async with DocumentSyncContext(mock_client, file_path) as uri:
            # URI should still be returned correctly
            assert uri == file_path.as_uri()

        # Assert - didOpen NOT called because file already open
        assert mock_client.open_document.call_count == 0, (
            "open_document should NOT be called when is_open is True in cache"
        )
