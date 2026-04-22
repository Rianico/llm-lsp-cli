"""Tests for DiagnosticCache.is_stale() with mtime-based staleness.

These tests verify the refactored is_stale method:
- Signature: is_stale(uri: str, incoming_mtime: float) -> bool
- Stale iff incoming_mtime > stored_mtime
- Not stale when file not tracked (first request)
"""

from pathlib import Path

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache, FileState


class TestDiagnosticCacheIsStaleMtime:
    """Tests for DiagnosticCache.is_stale() with mtime parameter."""

    @pytest.fixture
    def cache(self, temp_dir: Path) -> DiagnosticCache:
        """Create a DiagnosticCache for testing."""
        return DiagnosticCache(temp_dir)

    @pytest.mark.asyncio
    async def test_stale_when_incoming_greater_than_stored(
        self, cache: DiagnosticCache
    ) -> None:
        """Stale when incoming_mtime > stored_mtime."""
        uri = "file:///tmp/test/file.py"
        # Set stored mtime to 100.0
        await cache.set_mtime(uri, 100.0)

        # Check with incoming mtime > stored
        is_stale = await cache.is_stale(uri, 200.0)
        assert is_stale is True

    @pytest.mark.asyncio
    async def test_not_stale_when_incoming_equals_stored(
        self, cache: DiagnosticCache
    ) -> None:
        """Not stale when incoming_mtime == stored_mtime."""
        uri = "file:///tmp/test/file.py"
        await cache.set_mtime(uri, 100.0)

        is_stale = await cache.is_stale(uri, 100.0)
        assert is_stale is False

    @pytest.mark.asyncio
    async def test_not_stale_when_incoming_less_than_stored(
        self, cache: DiagnosticCache
    ) -> None:
        """Not stale when incoming_mtime < stored_mtime (clock skew or cached mtime)."""
        uri = "file:///tmp/test/file.py"
        await cache.set_mtime(uri, 200.0)

        is_stale = await cache.is_stale(uri, 100.0)
        assert is_stale is False

    @pytest.mark.asyncio
    async def test_not_stale_when_no_state_exists(self, cache: DiagnosticCache) -> None:
        """Not stale when file not tracked (first request)."""
        uri = "file:///tmp/test/file.py"
        # No state exists yet

        is_stale = await cache.is_stale(uri, 100.0)
        assert is_stale is False

    @pytest.mark.asyncio
    async def test_stale_when_stored_mtime_is_zero(
        self, cache: DiagnosticCache
    ) -> None:
        """Stale when stored mtime is 0.0 (untracked file with incoming mtime)."""
        uri = "file:///tmp/test/file.py"
        # Create state with default mtime (0.0)
        await cache.on_did_open(uri)  # This creates state but mtime should be 0.0

        is_stale = await cache.is_stale(uri, 100.0)
        assert is_stale is True

    @pytest.mark.asyncio
    async def test_not_stale_when_both_are_zero(self, cache: DiagnosticCache) -> None:
        """Not stale when both stored and incoming mtime are 0.0."""
        uri = "file:///tmp/test/file.py"
        # Create state with default mtime
        await cache.on_did_open(uri)

        is_stale = await cache.is_stale(uri, 0.0)
        assert is_stale is False

    @pytest.mark.asyncio
    async def test_works_with_high_precision(self, cache: DiagnosticCache) -> None:
        """Should work with high-precision mtime values from st_mtime_ns."""
        uri = "file:///tmp/test/file.py"
        # Use values from st_mtime_ns / 1e9 that can actually be differentiated
        # Float precision is about 15-17 significant digits
        mtime_1 = 1713765123.456789
        mtime_2 = 1713765123.456790  # microsecond difference
        await cache.set_mtime(uri, mtime_1)

        is_stale = await cache.is_stale(uri, mtime_2)
        assert is_stale is True


class TestDiagnosticCacheOnDidOpenMtime:
    """Tests for DiagnosticCache.on_did_open() with optional mtime parameter."""

    @pytest.fixture
    def cache(self, temp_dir: Path) -> DiagnosticCache:
        """Create a DiagnosticCache for testing."""
        return DiagnosticCache(temp_dir)

    @pytest.mark.asyncio
    async def test_accepts_optional_mtime(self, cache: DiagnosticCache) -> None:
        """on_did_open should accept optional mtime parameter."""
        uri = "file:///tmp/test/file.py"
        await cache.on_did_open(uri, mtime=100.0)

        state = await cache.get_file_state(uri)
        assert state.mtime == 100.0

    @pytest.mark.asyncio
    async def test_works_without_mtime(self, cache: DiagnosticCache) -> None:
        """on_did_open should work without mtime (backward compatible)."""
        uri = "file:///tmp/test/file.py"
        await cache.on_did_open(uri)  # No mtime provided

        state = await cache.get_file_state(uri)
        assert state.mtime == 0.0  # Default value

    @pytest.mark.asyncio
    async def test_increments_document_version(self, cache: DiagnosticCache) -> None:
        """on_did_open should increment document_version."""
        uri = "file:///tmp/test/file.py"
        await cache.on_did_open(uri, mtime=100.0)

        state = await cache.get_file_state(uri)
        assert state.document_version == 1

    @pytest.mark.asyncio
    async def test_sets_is_open_true(self, cache: DiagnosticCache) -> None:
        """on_did_open should set is_open to True."""
        uri = "file:///tmp/test/file.py"
        await cache.on_did_open(uri, mtime=100.0)

        state = await cache.get_file_state(uri)
        assert state.is_open is True


class TestDiagnosticCacheOnDidCloseRemoval:
    """Tests verifying on_did_close method is removed."""

    @pytest.fixture
    def cache(self, temp_dir: Path) -> DiagnosticCache:
        """Create a DiagnosticCache for testing."""
        return DiagnosticCache(temp_dir)

    def test_on_did_close_method_does_not_exist(self, cache: DiagnosticCache) -> None:
        """on_did_close method should NOT exist on DiagnosticCache."""
        assert not hasattr(cache, "on_did_close"), (
            "on_did_close method should be removed from DiagnosticCache"
        )


class TestDiagnosticCacheUpdateDiagnosticsMtime:
    """Tests for DiagnosticCache.update_diagnostics() without diagnostics_version."""

    @pytest.fixture
    def cache(self, temp_dir: Path) -> DiagnosticCache:
        """Create a DiagnosticCache for testing."""
        return DiagnosticCache(temp_dir)

    @pytest.mark.asyncio
    async def test_does_not_set_diagnostics_version(
        self, cache: DiagnosticCache
    ) -> None:
        """update_diagnostics should NOT set diagnostics_version (field removed)."""
        uri = "file:///tmp/test/file.py"
        await cache.on_did_open(uri, mtime=100.0)
        await cache.update_diagnostics(uri, [{"message": "test"}])

        state = await cache.get_file_state(uri)
        # diagnostics_version should not exist
        assert not hasattr(state, "diagnostics_version")

    @pytest.mark.asyncio
    async def test_updates_diagnostics_list(self, cache: DiagnosticCache) -> None:
        """update_diagnostics should update the diagnostics list."""
        uri = "file:///tmp/test/file.py"
        diagnostics = [{"message": "error1"}, {"message": "error2"}]
        await cache.update_diagnostics(uri, diagnostics)

        state = await cache.get_file_state(uri)
        assert len(state.diagnostics) == 2

    @pytest.mark.asyncio
    async def test_updates_last_result_id(self, cache: DiagnosticCache) -> None:
        """update_diagnostics should update last_result_id."""
        uri = "file:///tmp/test/file.py"
        await cache.update_diagnostics(uri, [], result_id="result-456")

        state = await cache.get_file_state(uri)
        assert state.last_result_id == "result-456"
