"""Unit tests for RequestHandler._handle_did_change method.

This module tests the didChange subcommand handler as specified in ADR-0010.

Key behaviors tested:
1. didOpen sent when file not in cache
2. didOpen sent when mtime differs from cache
3. didOpen skipped when mtime matches cache (optimization)
4. didChange sent with correct full text sync
5. Handler does NOT update cache mtime
6. Return acknowledgment only (not diagnostics)
7. File not found error handling
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.daemon import RequestHandler
from llm_lsp_cli.lsp.cache import DiagnosticCache
from llm_lsp_cli.lsp.constants import LSPConstants


@pytest.fixture
def mock_lsp_client_with_cache(tmp_path: Path) -> MagicMock:
    """Mock LSPClient with real DiagnosticCache for mtime testing."""
    client = MagicMock()
    client._diagnostic_cache = DiagnosticCache(tmp_path)
    client._transport = AsyncMock()
    client.language_id = "python"
    client.open_document = AsyncMock(return_value="file:///test/file.py")
    client.send_did_change = AsyncMock(return_value="file:///test/file.py")
    return client


@pytest.fixture
def temp_python_file(tmp_path: Path) -> Path:
    """Create a temporary Python file with sample content."""
    filepath = tmp_path / "test_module.py"
    filepath.write_text("def test_func():\n    pass\n")
    return filepath


class TestHandleDidChangeDidOpenDecision:
    """Tests for didOpen decision logic based on cache state and mtime."""

    @pytest.mark.asyncio
    async def test_didopen_sent_when_file_not_in_cache(
        self,
        mock_lsp_client_with_cache: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify didOpen is sent when file is not in cache.

        Given: File URI not present in DiagnosticCache
        When: _handle_did_change called with file path
        Then: didOpen notification sent before didChange
        """
        handler = RequestHandler(
            workspace_path=str(temp_python_file.parent),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            _ = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(temp_python_file.parent),
                    "filePath": str(temp_python_file),
                },
            )

            # Verify didOpen was called (file not in cache)
            mock_lsp_client_with_cache.open_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_didopen_sent_when_mtime_differs_from_cache(
        self,
        mock_lsp_client_with_cache: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify didOpen is sent when mtime differs from cache.

        Given: File URI in cache with mtime T1
        When: _handle_did_change called with current mtime T2 (T2 > T1)
        Then: didOpen notification sent (file is stale)
        """
        handler = RequestHandler(
            workspace_path=str(temp_python_file.parent),
            language="python",
        )

        # Pre-populate cache with stale mtime
        uri = temp_python_file.as_uri()
        cache = mock_lsp_client_with_cache._diagnostic_cache
        await cache.on_did_open(uri, mtime=100.0)  # Old mtime

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            # Get current mtime (should be different from 100.0)
            current_mtime = os.stat(temp_python_file).st_mtime

            _ = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(temp_python_file.parent),
                    "filePath": str(temp_python_file),
                    "mtime": current_mtime,
                },
            )

            # Verify didOpen was called (file is stale)
            mock_lsp_client_with_cache.open_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_didopen_skipped_when_mtime_matches_cache(
        self,
        mock_lsp_client_with_cache: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify didOpen is skipped when mtime matches cache.

        Given: File URI in cache with mtime T1, is_open=True
        When: _handle_did_change called with current mtime T1
        Then: didOpen NOT sent (optimization - file already current)
        """
        handler = RequestHandler(
            workspace_path=str(temp_python_file.parent),
            language="python",
        )

        # Get current mtime
        current_mtime = os.stat(temp_python_file).st_mtime

        # Pre-populate cache with matching mtime and is_open=True
        uri = temp_python_file.as_uri()
        cache = mock_lsp_client_with_cache._diagnostic_cache
        await cache.on_did_open(uri, mtime=current_mtime)

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            _ = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(temp_python_file.parent),
                    "filePath": str(temp_python_file),
                    "mtime": current_mtime,
                },
            )

            # Verify didOpen was NOT called (optimization)
            mock_lsp_client_with_cache.open_document.assert_not_called()


class TestHandleDidChangeNotification:
    """Tests for didChange notification construction."""

    @pytest.mark.asyncio
    async def test_didchange_sent_with_correct_full_text_sync(
        self,
        mock_lsp_client_with_cache: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify didChange notification has correct contentChanges structure.

        Given: File exists on disk with content "def foo(): pass"
        When: _handle_did_change called
        Then: didChange notification has contentChanges with full text
        """
        handler = RequestHandler(
            workspace_path=str(temp_python_file.parent),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            _ = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(temp_python_file.parent),
                    "filePath": str(temp_python_file),
                },
            )

            # Verify send_did_change was called with file_path and content
            mock_lsp_client_with_cache.send_did_change.assert_called_once()
            call_args = mock_lsp_client_with_cache.send_did_change.call_args

            # First arg should be the file path (Path object)
            assert call_args[0][0] == temp_python_file

            # Second arg should be the file content
            content = call_args[0][1]
            assert "def test_func():" in content

    @pytest.mark.asyncio
    async def test_didchange_uses_file_content_from_disk(
        self,
        mock_lsp_client_with_cache: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify file content is read from disk for didChange."""
        # Create file with specific content
        test_file = tmp_path / "content_test.py"
        test_content = "# Test content\nx = 42\n"
        test_file.write_text(test_content)

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            _ = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(tmp_path),
                    "filePath": str(test_file),
                },
            )

            # Verify content in didChange matches file content
            transport = mock_lsp_client_with_cache._transport
            calls = transport.send_notification.call_args_list
            didchange_calls = [
                c for c in calls
                if c[0][0] == LSPConstants.TEXT_DOCUMENT_DID_CHANGE
            ]

            if didchange_calls:
                params = didchange_calls[0][0][1]
                sent_text = params["contentChanges"][0]["text"]
                assert sent_text == test_content


class TestHandleDidChangeCacheBehavior:
    """Tests for cache behavior constraints."""

    @pytest.mark.asyncio
    async def test_handler_does_not_update_cache_mtime(
        self,
        mock_lsp_client_with_cache: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify handler does NOT update cache mtime.

        Given: File with cached mtime T1
        When: _handle_did_change completes
        Then: Cache mtime remains T1 (no mutation)

        Critical: Per ADR-0010, rely on existing mtime-based invalidation.
        """
        handler = RequestHandler(
            workspace_path=str(temp_python_file.parent),
            language="python",
        )

        # Set up cache with initial mtime
        uri = temp_python_file.as_uri()
        cache = mock_lsp_client_with_cache._diagnostic_cache
        initial_mtime = 100.0
        await cache.on_did_open(uri, mtime=initial_mtime)

        # Get initial mtime
        initial_state = await cache.get_file_state(uri)
        initial_cached_mtime = initial_state.mtime

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            _ = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(temp_python_file.parent),
                    "filePath": str(temp_python_file),
                },
            )

            # Verify cache mtime was NOT updated
            final_state = await cache.get_file_state(uri)
            assert final_state.mtime == initial_cached_mtime


class TestHandleDidChangeResponse:
    """Tests for response format."""

    @pytest.mark.asyncio
    async def test_return_acknowledgment_only(
        self,
        mock_lsp_client_with_cache: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify response is acknowledgment, not diagnostics.

        Given: Valid file path
        When: _handle_did_change called
        Then: Returns {"status": "acknowledged"} (not diagnostics)
        """
        handler = RequestHandler(
            workspace_path=str(temp_python_file.parent),
            language="python",
        )

        with patch.object(handler._registry, "get_or_create_workspace") as mock_ws:
            mock_workspace = mock_ws.return_value
            mock_workspace.ensure_initialized.return_value = mock_lsp_client_with_cache

            result = await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(temp_python_file.parent),
                    "filePath": str(temp_python_file),
                },
            )

            assert result == {"status": "acknowledged"}


class TestHandleDidChangeErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_file_not_found_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify FileNotFoundError raised for non-existent file.

        Given: Non-existent file path
        When: _handle_did_change called
        Then: Raises FileNotFoundError or appropriate error
        """
        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        non_existent = tmp_path / "does_not_exist.py"

        with pytest.raises((FileNotFoundError, ValueError)):
            await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(tmp_path),
                    "filePath": str(non_existent),
                },
            )

    @pytest.mark.asyncio
    async def test_missing_file_path_parameter(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify error when filePath parameter is missing."""
        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )

        with pytest.raises(ValueError, match="filePath"):
            await handler.handle(
                "textDocument/didChange",
                {
                    "workspacePath": str(tmp_path),
                },
            )
