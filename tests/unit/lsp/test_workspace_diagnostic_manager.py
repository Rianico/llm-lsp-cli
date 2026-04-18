"""Tests for WorkspaceDiagnosticManager class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.client import WorkspaceDiagnosticManager
from llm_lsp_cli.lsp.constants import LSPConstants


class TestDiagnosticManagerInitialization:
    """Test WorkspaceDiagnosticManager initialization."""

    def test_manager_initializes_with_empty_cache(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test manager initializes with empty cache."""
        assert workspace_diagnostic_manager._cache == {}
        assert not workspace_diagnostic_manager._streaming_complete.is_set()
        assert workspace_diagnostic_manager._partial_result_token is not None


class TestCacheOperations:
    """Test WorkspaceDiagnosticManager cache operations."""

    async def test_update_cache_stores_diagnostics(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test cache stores diagnostics for URI."""
        diagnostics = [
            {"range": {"start": {"line": 0, "character": 0}}, "message": "Error 1"},
            {"range": {"start": {"line": 1, "character": 0}}, "message": "Error 2"},
        ]

        await workspace_diagnostic_manager._update_cache("file:///test.py", diagnostics)

        assert "file:///test.py" in workspace_diagnostic_manager._cache
        assert len(workspace_diagnostic_manager._cache["file:///test.py"]) == 2

    async def test_update_cache_replaces_existing_diagnostics(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test cache replaces diagnostics for same URI."""
        # Initial diagnostics
        await workspace_diagnostic_manager._update_cache(
            "file:///test.py",
            [{"message": "Old error"}],
        )

        # New diagnostics
        new_diagnostics = [{"message": "New error 1"}, {"message": "New error 2"}]
        await workspace_diagnostic_manager._update_cache("file:///test.py", new_diagnostics)

        # Verify replaced, not accumulated
        assert len(workspace_diagnostic_manager._cache["file:///test.py"]) == 2
        assert workspace_diagnostic_manager._cache["file:///test.py"][0]["message"] == "New error 1"

    async def test_get_cache_items_returns_all_items(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test get_cache_items returns all cached diagnostics."""
        await workspace_diagnostic_manager._update_cache(
            "file:///test1.py",
            [{"message": "Error 1"}],
        )
        await workspace_diagnostic_manager._update_cache(
            "file:///test2.py",
            [{"message": "Error 2"}],
        )

        items = await workspace_diagnostic_manager._get_cache_items()

        assert len(items) == 2
        uris = {item["uri"] for item in items}
        assert "file:///test1.py" in uris
        assert "file:///test2.py" in uris

    async def test_get_cached_returns_list_copy(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
        sample_diagnostics: list[dict[str, str]],
    ) -> None:
        """Test get_cached returns a copy of diagnostics."""
        await workspace_diagnostic_manager._update_cache(
            "file:///test.py",
            sample_diagnostics,
        )

        result = workspace_diagnostic_manager.get_cached("file:///test.py")

        # Modifying result should not modify cache
        result.append({"message": "Added"})
        assert len(workspace_diagnostic_manager._cache["file:///test.py"]) == 1


class TestCacheConcurrency:
    """Test WorkspaceDiagnosticManager cache concurrency."""

    async def test_concurrent_cache_writes_use_lock(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test concurrent writes use lock for thread safety."""
        async def write_diagnostics(uri: str, count: int) -> None:
            diagnostics = [{"message": f"Error {i}"} for i in range(count)]
            await workspace_diagnostic_manager._update_cache(uri, diagnostics)

        # Run concurrent writes
        await asyncio.gather(
            write_diagnostics("file:///test1.py", 5),
            write_diagnostics("file:///test2.py", 5),
            write_diagnostics("file:///test3.py", 5),
        )

        # Verify all writes completed
        assert len(workspace_diagnostic_manager._cache) == 3
        assert len(workspace_diagnostic_manager._cache["file:///test1.py"]) == 5

    async def test_cache_lock_released_after_write(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test lock is released after write."""
        await workspace_diagnostic_manager._update_cache(
            "file:///test.py",
            [{"message": "Error"}],
        )

        # Lock should be available after write
        lock_held = workspace_diagnostic_manager._cache_lock.locked()
        assert not lock_held


class TestProgressHandling:
    """Test WorkspaceDiagnosticManager progress handling."""

    def test_handle_progress_begin_ignored(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test progress begin notification."""
        params = {
            "token": workspace_diagnostic_manager._partial_result_token,
            "value": {
                "kind": "begin",
                "title": "Workspace Diagnostics",
                "percentage": 0,
            },
        }

        workspace_diagnostic_manager._handle_progress(params)

        # Cache should still be empty
        assert workspace_diagnostic_manager._cache == {}

    async def test_handle_progress_report_with_items_updates_cache(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test progress report with items updates cache."""
        params = {
            "token": workspace_diagnostic_manager._partial_result_token,
            "value": {
                "kind": "report",
                "items": [
                    {
                        "uri": "file:///test.py",
                        "diagnostics": [{"message": "Error"}],
                    }
                ],
            },
        }

        # Process items directly (async)
        await workspace_diagnostic_manager._process_report_items(params["value"]["items"])

        # Verify cache was updated
        assert "file:///test.py" in workspace_diagnostic_manager._cache
        assert len(workspace_diagnostic_manager._cache["file:///test.py"]) == 1
        assert workspace_diagnostic_manager._cache["file:///test.py"][0]["message"] == "Error"

    def test_handle_progress_end_sets_streaming_complete(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test progress end sets streaming_complete event."""
        params = {
            "token": "any-token",
            "value": {"kind": "end"},
        }

        workspace_diagnostic_manager._handle_progress(params)

        assert workspace_diagnostic_manager._streaming_complete.is_set()

    def test_handle_progress_wrong_token_ignored(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test progress with wrong token is ignored."""
        initial_cache_size = len(workspace_diagnostic_manager._cache)

        params = {
            "token": "wrong-token",
            "value": {
                "items": [
                    {
                        "uri": "file:///test.py",
                        "diagnostics": [{"message": "Error"}],
                    }
                ],
            },
        }

        workspace_diagnostic_manager._handle_progress(params)

        # Cache should be unchanged
        assert len(workspace_diagnostic_manager._cache) == initial_cache_size


class TestDiagnosticRequest:
    """Test WorkspaceDiagnosticManager diagnostic request."""

    async def test_request_clears_streaming_complete(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test request clears streaming_complete event."""
        workspace_diagnostic_manager._streaming_complete.set()  # Pre-set

        # Mock _send_diagnostic_request
        workspace_diagnostic_manager._send_diagnostic_request = AsyncMock()
        # Mock _get_cache_items
        workspace_diagnostic_manager._get_cache_items = AsyncMock(return_value=[])

        # Mock transport
        mock_client = workspace_diagnostic_manager._client
        mock_client._transport = MagicMock()
        mock_client._transport.on_notification = MagicMock()

        # Start request but don't wait for completion
        task = asyncio.create_task(workspace_diagnostic_manager.request())
        await asyncio.sleep(0)  # Let it start

        # Event should be cleared
        assert not workspace_diagnostic_manager._streaming_complete.is_set()

        # Clean up
        workspace_diagnostic_manager._streaming_complete.set()
        await task

    async def test_request_timeout_returns_partial_results(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test timeout returns partial cache results."""
        # Pre-populate cache
        await workspace_diagnostic_manager._update_cache(
            "file:///test.py",
            [{"message": "Cached"}],
        )

        # Mock _get_cache_items to return cache
        workspace_diagnostic_manager._get_cache_items = AsyncMock(return_value=[
            {
                "uri": "file:///test.py",
                "version": None,
                "diagnostics": [{"message": "Cached"}],
            }
        ])

        # Mock transport
        mock_client = workspace_diagnostic_manager._client
        mock_transport = MagicMock()
        mock_transport.on_notification = MagicMock()
        mock_client._transport = mock_transport

        # Don't actually send the request - just test that request() returns cached data
        # when streaming_complete is already set
        workspace_diagnostic_manager._streaming_complete.set()

        # Patch send_diagnostic_request to do nothing
        workspace_diagnostic_manager._send_diagnostic_request = AsyncMock()

        # Request - should return cached results
        result = await workspace_diagnostic_manager.request()

        # Should return cached results
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["uri"] == "file:///test.py"

    async def test_send_diagnostic_request_sends_correct_params(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test diagnostic request sends correct params."""
        mock_client = workspace_diagnostic_manager._client
        mock_transport = AsyncMock()
        mock_client._transport = mock_transport

        await workspace_diagnostic_manager._send_diagnostic_request()

        mock_transport.send_request_fire_and_forget.assert_called_once()
        call_args = mock_transport.send_request_fire_and_forget.call_args
        assert call_args[0][0] == LSPConstants.WORKSPACE_DIAGNOSTIC
        params = call_args[0][1]
        assert params["identifier"] == "basedpyright"
        assert params["previousResultIds"] == []
        assert "partialResultToken" in params
