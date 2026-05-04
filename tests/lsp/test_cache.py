"""Unit tests for DiagnosticCache class.

This test file verifies the unified diagnostic cache mechanism with:
- Relative path keys
- Client-managed version tracking
- LSP 3.17 compliance
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache, FileState


# =============================================================================
# Module-Level Fixtures
# =============================================================================


@pytest.fixture
def workspace_path(temp_dir: Path) -> Path:
    """Return resolved workspace path."""
    return temp_dir.resolve()


@pytest.fixture
def diagnostic_cache(workspace_path: Path) -> DiagnosticCache:
    """Create a DiagnosticCache instance for testing."""
    return DiagnosticCache(workspace_path)


@pytest.fixture
def sample_uri() -> str:
    """Return a sample file URI."""
    return "file:///tmp/test_workspace/src/module/file.py"


@pytest.fixture
def sample_diagnostics() -> list[dict[str, Any]]:
    """Return sample diagnostic items."""
    return [
        {
            "range": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 20},
            },
            "severity": 1,
            "code": "E0001",
            "source": "basedpyright",
            "message": "Unused import",
        }
    ]


@pytest.fixture
def sample_file_in_workspace(temp_dir: Path) -> Path:
    """Create a sample file inside the workspace."""
    src_dir = temp_dir / "src" / "module"
    src_dir.mkdir(parents=True, exist_ok=True)
    file_path = src_dir / "file.py"
    file_path.write_text("print('hello')")
    return file_path


@pytest.fixture
def multiple_sample_uris() -> list[str]:
    """Return multiple sample URIs."""
    return [
        "file:///tmp/test_workspace/src/module/file1.py",
        "file:///tmp/test_workspace/src/module/file2.py",
        "file:///tmp/test_workspace/src/utils.py",
    ]


@pytest.fixture
def multiple_sample_diagnostics(
    multiple_sample_uris: list[str],
    sample_diagnostics: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return dict mapping URIs to diagnostics."""
    return {uri: sample_diagnostics for uri in multiple_sample_uris}


# =============================================================================
# TestFileState
# =============================================================================


class TestFileState:
    """Tests for FileState dataclass."""

    def test_filestate_defaults(self) -> None:
        """Verify default values for FileState fields."""
        state = FileState()
        assert state.document_version == 0
        assert state.last_result_id is None
        assert state.is_open is False
        assert state.diagnostics == []

    def test_filestate_with_values(self) -> None:
        """Initialize FileState with explicit values."""
        diags: list[dict[str, Any]] = [{"message": "test"}]
        state = FileState(
            document_version=5,
            last_result_id="result-123",
            is_open=True,
            diagnostics=diags,
        )
        assert state.document_version == 5
        assert state.last_result_id == "result-123"
        assert state.is_open is True
        assert state.diagnostics == diags

    def test_filestate_diagnostics_append(self) -> None:
        """Append diagnostics to list preserves other fields."""
        state = FileState()
        initial_version = state.document_version
        initial_is_open = state.is_open

        state.diagnostics.append({"message": "diag1"})
        state.diagnostics.append({"message": "diag2"})

        assert len(state.diagnostics) == 2
        assert state.document_version == initial_version
        assert state.is_open == initial_is_open

    def test_filestate_version_increment(self) -> None:
        """Increment document version preserves immutability."""
        state = FileState(document_version=1)
        new_version = state.document_version + 1
        # Create new state (immutability pattern)
        new_state = FileState(
            document_version=new_version,
            last_result_id=state.last_result_id,
            is_open=state.is_open,
            diagnostics=list(state.diagnostics),
        )
        assert new_state.document_version == 2
        assert state.document_version == 1  # Original unchanged


# =============================================================================
# TestDiagnosticCache::TestUriConversion
# =============================================================================


class TestDiagnosticCache:
    """Tests for DiagnosticCache class."""

    class TestUriConversion:
        """URI conversion tests."""

        def test_uri_to_absolute_path_normal(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_file_in_workspace: Path,
        ) -> None:
            """Standard file inside workspace returns absolute path."""
            uri = sample_file_in_workspace.as_uri()
            absolute_path = diagnostic_cache._uri_to_absolute_path(uri)
            # Now returns absolute path
            assert absolute_path == str(sample_file_in_workspace.resolve())

        def test_uri_to_absolute_path_root_file(
            self,
            diagnostic_cache: DiagnosticCache,
            temp_dir: Path,
        ) -> None:
            """File at workspace root returns absolute path."""
            root_file = temp_dir / "root_file.py"
            root_file.write_text("# root file")
            uri = root_file.as_uri()
            absolute_path = diagnostic_cache._uri_to_absolute_path(uri)
            # Now returns absolute path
            assert absolute_path == str(root_file.resolve())

        def test_uri_to_absolute_path_external(
            self,
            diagnostic_cache: DiagnosticCache,
        ) -> None:
            """File outside workspace returns absolute path."""
            external_uri = "file:///external/path/file.py"
            absolute_path = diagnostic_cache._uri_to_absolute_path(external_uri)
            # Returns absolute path
            assert absolute_path == "/external/path/file.py"

        def test_uri_to_absolute_path_symlink(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_file_in_workspace: Path,
        ) -> None:
            """Symlinked file resolves and returns absolute path."""
            # Create symlink
            symlink_path = diagnostic_cache._workspace_root / "symlink_file.py"
            if symlink_path.exists():
                symlink_path.unlink()
            symlink_path.symlink_to(sample_file_in_workspace)

            uri = symlink_path.as_uri()
            absolute_path = diagnostic_cache._uri_to_absolute_path(uri)
            # Should resolve symlink and return absolute path
            assert str(symlink_path.resolve()) in absolute_path or str(sample_file_in_workspace.resolve()) in absolute_path


# =============================================================================
# TestDiagnosticCache::TestBasicOperations
# =============================================================================

    class TestBasicOperations:
        """Basic cache operation tests."""

        @pytest.mark.asyncio
        async def test_update_diagnostics_basic(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Update diagnostics for URI stores in cache."""
            await diagnostic_cache.update_diagnostics(
                sample_uri, sample_diagnostics
            )
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert result == sample_diagnostics

        @pytest.mark.asyncio
        async def test_update_diagnostics_overwrites(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Update replaces existing diagnostics."""
            initial_diags = [{"message": "initial"}]
            new_diags = [{"message": "new"}]

            await diagnostic_cache.update_diagnostics(sample_uri, initial_diags)
            await diagnostic_cache.update_diagnostics(sample_uri, new_diags)

            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert result == new_diags

        @pytest.mark.asyncio
        async def test_update_diagnostics_with_result_id(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Update with server result ID stores correctly."""
            result_id = "workspace-diagnostic-123"
            await diagnostic_cache.update_diagnostics(
                sample_uri, sample_diagnostics, result_id=result_id
            )
            state = await diagnostic_cache.get_file_state(sample_uri)
            assert state.last_result_id == result_id

        @pytest.mark.asyncio
        async def test_get_diagnostics_hit(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Get existing diagnostics returns cached."""
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert result == sample_diagnostics

        @pytest.mark.asyncio
        async def test_get_diagnostics_miss(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Get non-existent diagnostics returns empty list."""
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert result == []

        @pytest.mark.asyncio
        async def test_get_diagnostics_returns_copy(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Verify defensive copy is returned."""
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            result.append({"message": "mutated"})

            # Original cache should be unchanged
            original = await diagnostic_cache.get_diagnostics(sample_uri)
            assert len(original) == len(sample_diagnostics)


# =============================================================================
# TestDiagnosticCache::TestVersionTracking
# =============================================================================

    class TestVersionTracking:
        """Version tracking tests."""

        @pytest.mark.asyncio
        async def test_on_did_open_sets_state(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """on_did_open initializes state with correct defaults."""
            await diagnostic_cache.on_did_open(sample_uri)
            state = await diagnostic_cache.get_file_state(sample_uri)
            assert state.is_open is True
            assert state.document_version == 1

        @pytest.mark.asyncio
        async def test_on_did_open_increment_version(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Re-opening increments version."""
            await diagnostic_cache.on_did_open(sample_uri)
            state1 = await diagnostic_cache.get_file_state(sample_uri)
            first_version = state1.document_version

            await diagnostic_cache.on_did_open(sample_uri)
            state2 = await diagnostic_cache.get_file_state(sample_uri)

            assert state2.document_version == first_version + 1

        @pytest.mark.asyncio
        async def test_increment_version(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Manual version increment increases by 1."""
            await diagnostic_cache.on_did_open(sample_uri)
            await diagnostic_cache.increment_version(sample_uri)
            state = await diagnostic_cache.get_file_state(sample_uri)
            assert state.document_version == 2

        @pytest.mark.asyncio
        async def test_update_document_version_explicit(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Set version explicitly to specified value."""
            await diagnostic_cache.on_did_open(sample_uri)
            await diagnostic_cache.update_document_version(sample_uri, 10)
            state = await diagnostic_cache.get_file_state(sample_uri)
            assert state.document_version == 10

        @pytest.mark.asyncio
        async def test_file_stays_open_after_diagnostics(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Files stay open after diagnostics (no didClose in new design)."""
            mtime = 100.0
            await diagnostic_cache.on_did_open(sample_uri, mtime=mtime)
            await diagnostic_cache.update_diagnostics(
                sample_uri, [{"message": "test"}], result_id="result-1"
            )

            state = await diagnostic_cache.get_file_state(sample_uri)
            assert state.is_open is True
            assert state.last_result_id == "result-1"
            assert state.mtime == mtime

        @pytest.mark.asyncio
        async def test_version_never_decrements(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Verify version is monotonic (never decreases)."""
            await diagnostic_cache.on_did_open(sample_uri)
            await diagnostic_cache.increment_version(sample_uri)
            state1 = await diagnostic_cache.get_file_state(sample_uri)

            # Attempt to set lower version
            await diagnostic_cache.update_document_version(sample_uri, 1)
            state2 = await diagnostic_cache.get_file_state(sample_uri)

            # Version should not decrease
            assert state2.document_version >= state1.document_version


# =============================================================================
# TestDiagnosticCache::TestStaleDetection
# =============================================================================

    class TestStaleDetection:
        """Stale detection tests using mtime."""

        @pytest.mark.asyncio
        async def test_is_stale_fresh(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Cache is fresh when mtime matches."""
            mtime = 100.0
            await diagnostic_cache.on_did_open(sample_uri, mtime=mtime)
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)
            is_stale = await diagnostic_cache.is_stale(sample_uri, mtime)
            assert is_stale is False

        @pytest.mark.asyncio
        async def test_is_stale_mtime_changed(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Cache is stale when incoming mtime > stored mtime."""
            old_mtime = 100.0
            new_mtime = 200.0
            await diagnostic_cache.on_did_open(sample_uri, mtime=old_mtime)
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)
            is_stale = await diagnostic_cache.is_stale(sample_uri, new_mtime)
            assert is_stale is True

        @pytest.mark.asyncio
        async def test_is_stale_nonexistent_uri(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Check stale for missing URI returns False (not tracked)."""
            mtime = 100.0
            is_stale = await diagnostic_cache.is_stale(sample_uri, mtime)
            assert is_stale is False

        @pytest.mark.asyncio
        async def test_is_stale_after_mtime_update(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """After updating mtime, cache is fresh again."""
            old_mtime = 100.0
            new_mtime = 200.0
            await diagnostic_cache.on_did_open(sample_uri, mtime=old_mtime)
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)

            # Stale with new mtime
            assert await diagnostic_cache.is_stale(sample_uri, new_mtime) is True

            # Update mtime
            await diagnostic_cache.set_mtime(sample_uri, new_mtime)

            # Should be fresh with new mtime
            assert await diagnostic_cache.is_stale(sample_uri, new_mtime) is False


# =============================================================================
# TestDiagnosticCache::TestWorkspaceOperations
# =============================================================================

    class TestWorkspaceOperations:
        """Workspace-wide operation tests."""

        @pytest.mark.asyncio
        async def test_get_all_workspace_diagnostics_empty(
            self,
            diagnostic_cache: DiagnosticCache,
        ) -> None:
            """Empty cache returns empty list."""
            result = await diagnostic_cache.get_all_workspace_diagnostics()
            assert result == []

        @pytest.mark.asyncio
        async def test_get_all_workspace_diagnostics_multiple(
            self,
            diagnostic_cache: DiagnosticCache,
            multiple_sample_uris: list[str],
            multiple_sample_diagnostics: dict[str, list[dict[str, Any]]],
        ) -> None:
            """Multiple files cached returns all items."""
            for uri, diags in multiple_sample_diagnostics.items():
                await diagnostic_cache.update_diagnostics(uri, diags)

            result = await diagnostic_cache.get_all_workspace_diagnostics()

            assert len(result) == len(multiple_sample_uris)
            result_uris = {item["uri"] for item in result}
            assert result_uris == set(multiple_sample_uris)

        @pytest.mark.asyncio
        async def test_get_all_workspace_diagnostics_format(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Verify item format has required fields."""
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)

            result = await diagnostic_cache.get_all_workspace_diagnostics()

            assert len(result) == 1
            item = result[0]
            assert "uri" in item
            assert "version" in item
            assert "diagnostics" in item
            # URI should be the original file URI
            assert item["uri"] == sample_uri
            assert isinstance(item["diagnostics"], list)

        @pytest.mark.asyncio
        async def test_get_all_workspace_diagnostics_includes_empty_diagnostics(
            self,
            diagnostic_cache: DiagnosticCache,
        ) -> None:
            """Files with empty diagnostics are included in results.

            This tests the fix for the bug where files without errors were
            being filtered out. All cached files should be returned, even
            those with empty diagnostic lists.
            """
            ws_path = diagnostic_cache._workspace_root

            # Create test files
            test_file_with_errors = ws_path / "with_errors.py"
            test_file_no_errors = ws_path / "no_errors.py"
            test_file_with_errors.write_text("# has errors")
            test_file_no_errors.write_text("# clean file")

            uri_with_errors = test_file_with_errors.as_uri()
            uri_no_errors = test_file_no_errors.as_uri()

            # Add diagnostics - one file has errors, one doesn't
            await diagnostic_cache.update_diagnostics(
                uri_with_errors,
                [{"message": "Error"}]
            )
            await diagnostic_cache.update_diagnostics(
                uri_no_errors,
                []  # Empty diagnostics - file has no errors
            )

            result = await diagnostic_cache.get_all_workspace_diagnostics()

            # Both files should be in results
            assert len(result) == 2
            result_uris = {item["uri"] for item in result}
            assert uri_with_errors in result_uris
            assert uri_no_errors in result_uris

            # Find the file with empty diagnostics and verify it's empty
            for item in result:
                if item["uri"] == uri_no_errors:
                    assert item["diagnostics"] == []


# =============================================================================
# TestDiagnosticCache::TestConcurrency
# =============================================================================

    class TestConcurrency:
        """Concurrency and thread-safety tests."""

        @pytest.mark.asyncio
        async def test_concurrent_updates(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """Multiple concurrent updates apply correctly."""
            async def update(n: int) -> None:
                diags = [{"message": f"update-{n}"}]
                await diagnostic_cache.update_diagnostics(sample_uri, diags)

            # Run multiple updates concurrently
            await asyncio.gather(*(update(i) for i in range(10)))

            # All updates should have been applied (last one wins)
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert len(result) == 1

        @pytest.mark.asyncio
        async def test_concurrent_read_write(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
            sample_diagnostics: list[dict[str, Any]],
        ) -> None:
            """Simultaneous read and write has no race conditions."""
            await diagnostic_cache.update_diagnostics(sample_uri, sample_diagnostics)

            async def reader() -> list[dict[str, Any]]:
                return await diagnostic_cache.get_diagnostics(sample_uri)

            async def writer(n: int) -> None:
                diags = [{"message": f"write-{n}"}]
                await diagnostic_cache.update_diagnostics(sample_uri, diags)

            # Run concurrent reads and writes
            tasks = [reader() for _ in range(5)] + [writer(i) for i in range(5)]
            await asyncio.gather(*tasks)

            # Final read should return consistent data
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert len(result) == 1

        @pytest.mark.asyncio
        async def test_lock_prevents_corruption(
            self,
            diagnostic_cache: DiagnosticCache,
            sample_uri: str,
        ) -> None:
            """asyncio.Lock prevents data corruption under load."""
            async def stress_update(n: int) -> None:
                for i in range(10):
                    diags = [{"message": f"stress-{n}-{i}"}]
                    await diagnostic_cache.update_diagnostics(sample_uri, diags)

            # Run multiple stress tasks concurrently
            await asyncio.gather(*(stress_update(i) for i in range(5)))

            # Cache should be in consistent state
            result = await diagnostic_cache.get_diagnostics(sample_uri)
            assert len(result) == 1
