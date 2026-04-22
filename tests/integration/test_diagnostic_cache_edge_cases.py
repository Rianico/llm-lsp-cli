"""Integration tests for diagnostic cache edge cases.

These tests verify cache behavior in realistic scenarios:
- Multiple files cached independently
- Cache invalidation on file close
- Concurrent diagnostic requests for same file
- Cache coherence across file lifecycle
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache, FileState
from llm_lsp_cli.lsp.client import LSPClient

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def multi_file_workspace(temp_dir: Path) -> Path:
    """Create a workspace with multiple Python files."""
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()

    # Create multiple files
    (temp_dir / "src" / "module_a.py").write_text("def func_a(): pass")
    (temp_dir / "src" / "module_b.py").write_text("def func_b(): pass")
    (temp_dir / "tests" / "test_a.py").write_text("def test_a(): pass")

    return temp_dir


@pytest.fixture
def diagnostic_cache(multi_file_workspace: Path) -> DiagnosticCache:
    """Create a DiagnosticCache for the multi-file workspace."""
    return DiagnosticCache(multi_file_workspace)


# =============================================================================
# Test: Multiple Files Cached Independently
# =============================================================================


class TestMultipleFilesCachedIndependently:
    """Tests verifying independent cache behavior for multiple files."""

    @pytest.mark.asyncio
    async def test_each_file_has_own_cache_entry(
        self, diagnostic_cache: DiagnosticCache, multi_file_workspace: Path
    ) -> None:
        """Each file should have its own cache entry with independent state."""
        file_a = multi_file_workspace / "src" / "module_a.py"
        file_b = multi_file_workspace / "src" / "module_b.py"

        uri_a = file_a.as_uri()
        uri_b = file_b.as_uri()

        # Cache different diagnostics for each file
        diags_a: list[dict[str, Any]] = [
            {"message": "Error in A", "severity": 1}
        ]
        diags_b: list[dict[str, Any]] = [
            {"message": "Error in B", "severity": 2}
        ]

        await diagnostic_cache.on_did_open(uri_a)
        await diagnostic_cache.on_did_open(uri_b)
        await diagnostic_cache.update_diagnostics(uri_a, diags_a, result_id="result-a")
        await diagnostic_cache.update_diagnostics(uri_b, diags_b, result_id="result-b")

        # Verify independent cache entries
        state_a = await diagnostic_cache.get_file_state(uri_a)
        state_b = await diagnostic_cache.get_file_state(uri_b)

        assert state_a.diagnostics == diags_a
        assert state_a.last_result_id == "result-a"
        assert state_b.diagnostics == diags_b
        assert state_b.last_result_id == "result-b"

    @pytest.mark.asyncio
    async def test_updating_one_file_does_not_affect_others(
        self, diagnostic_cache: DiagnosticCache, multi_file_workspace: Path
    ) -> None:
        """Updating one file's cache should not affect other files."""
        file_a = multi_file_workspace / "src" / "module_a.py"
        file_b = multi_file_workspace / "src" / "module_b.py"

        uri_a = file_a.as_uri()
        uri_b = file_b.as_uri()

        # Initial cache
        initial_diags_a: list[dict[str, Any]] = [{"message": "Initial A"}]
        initial_diags_b: list[dict[str, Any]] = [{"message": "Initial B"}]

        await diagnostic_cache.on_did_open(uri_a)
        await diagnostic_cache.on_did_open(uri_b)
        await diagnostic_cache.update_diagnostics(uri_a, initial_diags_a, result_id="r1")
        await diagnostic_cache.update_diagnostics(uri_b, initial_diags_b, result_id="r2")

        # Update only file A
        updated_diags_a: list[dict[str, Any]] = [{"message": "Updated A"}]
        await diagnostic_cache.update_diagnostics(uri_a, updated_diags_a, result_id="r3")

        # Verify B is unchanged
        state_a = await diagnostic_cache.get_file_state(uri_a)
        state_b = await diagnostic_cache.get_file_state(uri_b)

        assert state_a.diagnostics == updated_diags_a
        assert state_a.last_result_id == "r3"
        assert state_b.diagnostics == initial_diags_b
        assert state_b.last_result_id == "r2"  # Unchanged

    @pytest.mark.asyncio
    async def test_independent_stale_tracking(
        self, diagnostic_cache: DiagnosticCache, multi_file_workspace: Path
    ) -> None:
        """Stale status should be tracked independently per file using mtime."""
        file_a = multi_file_workspace / "src" / "module_a.py"
        file_b = multi_file_workspace / "src" / "module_b.py"

        uri_a = file_a.as_uri()
        uri_b = file_b.as_uri()

        # Setup cache for both files with initial mtime
        mtime_a = 100.0
        mtime_b = 200.0
        await diagnostic_cache.on_did_open(uri_a, mtime=mtime_a)
        await diagnostic_cache.on_did_open(uri_b, mtime=mtime_b)
        await diagnostic_cache.update_diagnostics(uri_a, [{"message": "A"}], result_id="r1")
        await diagnostic_cache.update_diagnostics(uri_b, [{"message": "B"}], result_id="r2")

        # Both should be fresh when mtime matches
        assert await diagnostic_cache.is_stale(uri_a, mtime_a) is False
        assert await diagnostic_cache.is_stale(uri_b, mtime_b) is False

        # File A is modified (new incoming mtime > stored mtime)
        new_mtime_a = 150.0

        # A with new mtime should be stale (incoming > stored)
        assert await diagnostic_cache.is_stale(uri_a, new_mtime_a) is True
        # B should still be fresh
        assert await diagnostic_cache.is_stale(uri_b, mtime_b) is False
        assert await diagnostic_cache.is_stale(uri_b, 250.0) is True  # B also changed


# =============================================================================
# Test: Cache Invalidation Scenarios
# =============================================================================


class TestCacheInvalidationScenarios:
    """Tests for cache invalidation behavior using mtime."""

    @pytest.mark.asyncio
    async def test_mtime_change_invalidates_cache(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """File modification (mtime change) should mark cache as stale."""
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")
        uri = test_file.as_uri()

        # Setup: open file with initial mtime and cache diagnostics
        initial_mtime = 100.0
        await diagnostic_cache.on_did_open(uri, mtime=initial_mtime)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Test error"}], result_id="result-123"
        )

        # Verify cache state is fresh when mtime matches
        state = await diagnostic_cache.get_file_state(uri)
        assert state.is_open is True
        assert state.last_result_id == "result-123"
        assert state.mtime == initial_mtime
        assert await diagnostic_cache.is_stale(uri, initial_mtime) is False

        # File modified - new mtime
        new_mtime = 200.0
        assert await diagnostic_cache.is_stale(uri, new_mtime) is True

        # Update mtime to new value
        await diagnostic_cache.set_mtime(uri, new_mtime)

        # Now should be fresh with new mtime
        assert await diagnostic_cache.is_stale(uri, new_mtime) is False

    @pytest.mark.asyncio
    async def test_version_increment_for_lsp_protocol(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Version increment is for LSP protocol, not cache staleness."""
        test_file = temp_dir / "test.py"
        test_file.write_text("x = 1")
        uri = test_file.as_uri()

        # Setup: open file with mtime
        mtime = 100.0
        await diagnostic_cache.on_did_open(uri, mtime=mtime)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Unused variable"}], result_id="result-1"
        )

        # Cache should be fresh with matching mtime
        assert await diagnostic_cache.is_stale(uri, mtime) is False

        # Version increment (LSP protocol)
        await diagnostic_cache.increment_version(uri)

        # Cache should still be fresh (mtime unchanged)
        assert await diagnostic_cache.is_stale(uri, mtime) is False

    @pytest.mark.asyncio
    async def test_reopen_file_increments_version(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Re-opening a file should increment document version."""
        test_file = temp_dir / "test.py"
        test_file.write_text("y = 2")
        uri = test_file.as_uri()

        # First open
        mtime1 = 100.0
        await diagnostic_cache.on_did_open(uri, mtime=mtime1)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "First diag"}], result_id="result-1"
        )
        state1 = await diagnostic_cache.get_file_state(uri)
        version1 = state1.document_version

        # Re-open (file stays open per new design, version increments)
        mtime2 = 150.0
        await diagnostic_cache.on_did_open(uri, mtime=mtime2)
        state2 = await diagnostic_cache.get_file_state(uri)

        # Version should increment on reopen
        assert state2.document_version == version1 + 1
        assert state2.is_open is True
        assert state2.mtime == mtime2

    @pytest.mark.asyncio
    async def test_mtime_update_after_diagnostic_refresh(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Updating mtime after refresh makes cache fresh again."""
        test_file = temp_dir / "test.py"
        test_file.write_text("z = 3")
        uri = test_file.as_uri()

        # Setup: open with old mtime
        old_mtime = 100.0
        await diagnostic_cache.on_did_open(uri, mtime=old_mtime)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Old diag"}], result_id="old"
        )

        # File changed - new mtime means stale
        new_mtime = 200.0
        assert await diagnostic_cache.is_stale(uri, new_mtime) is True

        # After refresh with new mtime
        await diagnostic_cache.set_mtime(uri, new_mtime)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "New diag"}], result_id="new"
        )

        # Should be fresh again
        assert await diagnostic_cache.is_stale(uri, new_mtime) is False


# =============================================================================
# Test: Concurrent Diagnostic Requests
# =============================================================================


class TestConcurrentDiagnosticRequests:
    """Tests for concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_file_returns_consistent_data(
        self, temp_dir: Path
    ) -> None:
        """Concurrent diagnostic requests for same file with same mtime return cached."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///tmp/test/file.py"
        test_diagnostics: list[dict[str, Any]] = [
            {"message": "Concurrent error", "severity": 1}
        ]
        mtime = 100.0

        # Setup cache with mtime
        await client._diagnostic_cache.on_did_open(test_uri, mtime=mtime)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, test_diagnostics, result_id="result-1"
        )

        # Mock transport
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock()
        client._transport = mock_transport

        # Simulate concurrent requests with same mtime
        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            # Run multiple concurrent requests with same mtime
            results = await asyncio.gather(
                client.request_diagnostics("/tmp/test/file.py", mtime=mtime),
                client.request_diagnostics("/tmp/test/file.py", mtime=mtime),
                client.request_diagnostics("/tmp/test/file.py", mtime=mtime),
            )

        # All should return cached diagnostics without server call
        for result in results:
            assert result == test_diagnostics

        # Server should not have been called (cache was valid)
        mock_transport.send_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_read_write_operations(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Concurrent read and write operations should be safe."""
        test_file = temp_dir / "concurrent.py"
        test_file.write_text("a = 1")
        uri = test_file.as_uri()

        # Setup initial state
        await diagnostic_cache.on_did_open(uri)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Initial"}], result_id="r0"
        )

        async def reader() -> list[dict[str, Any]]:
            return await diagnostic_cache.get_diagnostics(uri)

        async def writer(n: int) -> None:
            await diagnostic_cache.update_diagnostics(
                uri, [{"message": f"Update {n}"}], result_id=f"r{n}"
            )

        # Run concurrent operations
        await asyncio.gather(
            *[reader() for _ in range(10)],
            *[writer(i) for i in range(5)],
        )

        # Final state should be consistent
        final_state = await diagnostic_cache.get_file_state(uri)
        assert len(final_state.diagnostics) == 1
        assert "Update" in final_state.diagnostics[0]["message"]

    @pytest.mark.asyncio
    async def test_concurrent_stale_checks_during_update(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Stale checks during concurrent updates should be consistent."""
        test_file = temp_dir / "stale_test.py"
        test_file.write_text("b = 2")
        uri = test_file.as_uri()

        mtime = 100.0
        await diagnostic_cache.on_did_open(uri, mtime=mtime)

        async def check_stale(check_mtime: float) -> bool:
            return await diagnostic_cache.is_stale(uri, check_mtime)

        async def update(n: int) -> None:
            await diagnostic_cache.update_diagnostics(
                uri, [{"message": f"D{n}"}], result_id=f"r{n}"
            )

        async def increment() -> None:
            await diagnostic_cache.increment_version(uri)

        # Run interleaved operations
        results = await asyncio.gather(
            update(1),
            check_stale(mtime),
            increment(),
            check_stale(mtime),
            update(2),
            check_stale(mtime),
            return_exceptions=True,
        )

        # No exceptions should have occurred
        for r in results:
            assert not isinstance(r, Exception)


# =============================================================================
# Test: Client-Level Cache Skip Integration
# =============================================================================


class TestClientCacheSkipIntegration:
    """Integration tests for client-level cache skip behavior using mtime."""

    @pytest.mark.asyncio
    async def test_first_request_sends_to_server_second_returns_cached(
        self, temp_dir: Path
    ) -> None:
        """First request sends to server, second returns cached when mtime unchanged."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///workspace/src/code.py"
        test_diagnostics: list[dict[str, Any]] = [
            {"message": "Server error", "severity": 1}
        ]
        mtime = 100.0

        # First request - should send to server
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "result-first",
                "items": test_diagnostics,
            }
        )
        client._transport = mock_transport

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            result1 = await client.request_diagnostics("/workspace/src/code.py", mtime=mtime)

        assert result1 == test_diagnostics
        mock_transport.send_request.assert_called_once()

        # Second request with same mtime - should return cached without server call
        mock_transport.send_request.reset_mock()

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            result2 = await client.request_diagnostics("/workspace/src/code.py", mtime=mtime)

        assert result2 == test_diagnostics
        mock_transport.send_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_file_mtime_change_triggers_server_request_after_cache(
        self, temp_dir: Path
    ) -> None:
        """After caching, file mtime change should trigger new server request."""
        client = LSPClient(
            workspace_path=str(temp_dir),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
        )

        test_uri = "file:///workspace/src/changed.py"
        old_diagnostics: list[dict[str, Any]] = [
            {"message": "Old error", "severity": 1}
        ]
        new_diagnostics: list[dict[str, Any]] = [
            {"message": "New error", "severity": 2}
        ]
        old_mtime = 100.0
        new_mtime = 200.0

        # First request - cache old diagnostics with old mtime
        await client._diagnostic_cache.on_did_open(test_uri, mtime=old_mtime)
        await client._diagnostic_cache.update_diagnostics(
            test_uri, old_diagnostics, result_id="old-result"
        )

        # Request with new mtime should go to server
        mock_transport = AsyncMock()
        mock_transport.send_request = AsyncMock(
            return_value={
                "kind": "full",
                "resultId": "new-result",
                "items": new_diagnostics,
            }
        )
        client._transport = mock_transport

        with patch.object(client, "_ensure_open", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = test_uri

            result = await client.request_diagnostics("/workspace/src/changed.py", mtime=new_mtime)

        assert result == new_diagnostics
        mock_transport.send_request.assert_called_once()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestDiagnosticCacheEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_diagnostics_cached_correctly(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Empty diagnostics (no errors) should be cached correctly."""
        test_file = temp_dir / "clean.py"
        test_file.write_text("# Clean file")
        uri = test_file.as_uri()

        await diagnostic_cache.on_did_open(uri)
        await diagnostic_cache.update_diagnostics(uri, [], result_id="empty-result")

        # Should return empty list, not None or error
        result = await diagnostic_cache.get_diagnostics(uri)
        assert result == []

        # Should still have resultId for cache optimization
        state = await diagnostic_cache.get_file_state(uri)
        assert state.last_result_id == "empty-result"

    @pytest.mark.asyncio
    async def test_nonexistent_file_uri_handled_gracefully(
        self, diagnostic_cache: DiagnosticCache
    ) -> None:
        """Requesting state for non-existent URI should return defaults."""
        nonexistent_uri = "file:///nonexistent/path/file.py"

        state = await diagnostic_cache.get_file_state(nonexistent_uri)
        assert isinstance(state, FileState)
        assert state.document_version == 0
        assert state.last_result_id is None
        assert state.diagnostics == []

    @pytest.mark.asyncio
    async def test_multiple_version_increments(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Multiple version increments should accumulate correctly."""
        test_file = temp_dir / "multi_edit.py"
        test_file.write_text("x = 1")
        uri = test_file.as_uri()

        await diagnostic_cache.on_did_open(uri)
        initial_state = await diagnostic_cache.get_file_state(uri)
        initial_version = initial_state.document_version

        # Multiple increments
        for _ in range(5):
            await diagnostic_cache.increment_version(uri)

        final_state = await diagnostic_cache.get_file_state(uri)
        assert final_state.document_version == initial_version + 5

    @pytest.mark.asyncio
    async def test_result_id_overwrite_on_update(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """ResultId should be overwritten on new diagnostic update."""
        test_file = temp_dir / "overwrite.py"
        test_file.write_text("y = 2")
        uri = test_file.as_uri()

        await diagnostic_cache.on_did_open(uri)

        # First update
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "First"}], result_id="result-1"
        )
        state1 = await diagnostic_cache.get_file_state(uri)
        assert state1.last_result_id == "result-1"

        # Second update with different resultId
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Second"}], result_id="result-2"
        )
        state2 = await diagnostic_cache.get_file_state(uri)
        assert state2.last_result_id == "result-2"

    @pytest.mark.asyncio
    async def test_update_without_result_id_preserves_existing(
        self, diagnostic_cache: DiagnosticCache, temp_dir: Path
    ) -> None:
        """Updating diagnostics without resultId should preserve existing resultId."""
        test_file = temp_dir / "preserve_id.py"
        test_file.write_text("z = 3")
        uri = test_file.as_uri()

        await diagnostic_cache.on_did_open(uri)

        # First update with resultId
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Initial"}], result_id="initial-id"
        )

        # Second update without resultId (e.g., from publishDiagnostics)
        await diagnostic_cache.update_diagnostics(
            uri, [{"message": "Updated"}], result_id=None
        )

        state = await diagnostic_cache.get_file_state(uri)
        # resultId should be preserved
        assert state.last_result_id == "initial-id"
        assert state.diagnostics[0]["message"] == "Updated"
