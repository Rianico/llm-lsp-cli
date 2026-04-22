"""Tests for DiagnosticCache.set_mtime() method.

These tests verify the new set_mtime method that updates file modification time.
"""

from pathlib import Path

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache, FileState


class TestDiagnosticCacheSetMtime:
    """Tests for DiagnosticCache.set_mtime() method."""

    @pytest.fixture
    def cache(self, temp_dir: Path) -> DiagnosticCache:
        """Create a DiagnosticCache for testing."""
        return DiagnosticCache(temp_dir)

    @pytest.mark.asyncio
    async def test_sets_mtime_on_existing_state(self, cache: DiagnosticCache) -> None:
        """set_mtime should update mtime on existing FileState."""
        uri = "file:///tmp/test/file.py"
        # Create initial state
        await cache.on_did_open(uri)
        # Set mtime
        await cache.set_mtime(uri, 100.0)

        state = await cache.get_file_state(uri)
        assert state.mtime == 100.0

    @pytest.mark.asyncio
    async def test_creates_state_if_not_exists(self, cache: DiagnosticCache) -> None:
        """set_mtime should create FileState if it doesn't exist."""
        uri = "file:///tmp/test/file.py"
        # No prior state
        await cache.set_mtime(uri, 200.0)

        state = await cache.get_file_state(uri)
        assert state.mtime == 200.0

    @pytest.mark.asyncio
    async def test_does_not_modify_other_fields(self, cache: DiagnosticCache) -> None:
        """set_mtime should only modify mtime, not other fields."""
        uri = "file:///tmp/test/file.py"
        # Create state with specific values
        await cache.on_did_open(uri)
        await cache.update_diagnostics(
            uri, [{"message": "test"}], result_id="result-123"
        )

        # Set mtime
        await cache.set_mtime(uri, 300.0)

        state = await cache.get_file_state(uri)
        assert state.mtime == 300.0
        assert state.document_version == 1  # Should not change
        assert state.last_result_id == "result-123"  # Should not change
        assert len(state.diagnostics) == 1  # Should not change

    @pytest.mark.asyncio
    async def test_overwrites_existing_mtime(self, cache: DiagnosticCache) -> None:
        """set_mtime should overwrite an existing mtime value."""
        uri = "file:///tmp/test/file.py"
        await cache.set_mtime(uri, 100.0)
        await cache.set_mtime(uri, 200.0)

        state = await cache.get_file_state(uri)
        assert state.mtime == 200.0

    @pytest.mark.asyncio
    async def test_thread_safe_via_lock(self, cache: DiagnosticCache) -> None:
        """set_mtime should be thread-safe via the cache lock."""
        uri = "file:///tmp/test/file.py"
        # Set mtime multiple times concurrently
        import asyncio

        tasks = [cache.set_mtime(uri, float(i)) for i in range(10)]
        await asyncio.gather(*tasks)

        # Should have one of the values set
        state = await cache.get_file_state(uri)
        assert state.mtime in [float(i) for i in range(10)]
