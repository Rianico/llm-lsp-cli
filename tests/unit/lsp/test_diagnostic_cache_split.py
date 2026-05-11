"""Tests for split diagnostics cache in FileState.

Test scenarios from spec sections 1.1-1.6:
- FileState dataclass field changes
- DiagnosticCache document diagnostic operations
- DiagnosticCache workspace diagnostic operations
- Cross-source isolation (core bug fix)
- get_all_workspace_diagnostics
- get_diagnostics backward compat
"""

import asyncio
from pathlib import Path

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache, FileState
from llm_lsp_cli.lsp.types import WorkspaceDiagnosticItem


# =============================================================================
# Section 1.1: FileState Dataclass
# =============================================================================


class TestFileStateDataclass:
    """Tests for FileState dataclass with split diagnostics fields."""

    def test_fs01_document_diagnostics_defaults_to_empty_list(self) -> None:
        """FS-01: FileState() defaults: document_diagnostics=[], workspace_diagnostics=[]"""
        state = FileState()
        assert state.document_diagnostics == []
        assert state.workspace_diagnostics == []

    def test_fs01_both_fields_are_independent(self) -> None:
        """FS-01: Both fields are empty lists, independent."""
        state = FileState()
        # Mutate one list should not affect the other
        state.document_diagnostics.append({"test": "value"})
        assert state.workspace_diagnostics == []

    def test_fs02_set_document_diagnostics_does_not_alter_workspace_diagnostics(self) -> None:
        """FS-02: Set document_diagnostics does not alter workspace_diagnostics."""
        state = FileState()
        state.document_diagnostics = [{"message": "doc error"}]
        assert state.workspace_diagnostics == []

    def test_fs03_set_workspace_diagnostics_does_not_alter_document_diagnostics(self) -> None:
        """FS-03: Set workspace_diagnostics does not alter document_diagnostics."""
        state = FileState()
        state.workspace_diagnostics = [{"message": "ws error"}]
        assert state.document_diagnostics == []

    def test_fs04_old_diagnostics_field_no_longer_exists(self) -> None:
        """FS-04: Old diagnostics field no longer exists on FileState."""
        state = FileState()
        assert not hasattr(state, "diagnostics")


# =============================================================================
# Section 1.2: DiagnosticCache -- Document Diagnostic Operations
# =============================================================================


class TestDocumentDiagnosticOperations:
    """Tests for document diagnostic operations on DiagnosticCache."""

    @pytest.mark.asyncio
    async def test_cd01_update_document_diagnostics_stores_in_document_diagnostics(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CD-01: update_document_diagnostics(uri, diags) stores in document_diagnostics."""
        diags = [{"message": "doc error", "severity": 1}]
        await diagnostic_cache.update_document_diagnostics(sample_uri, diags)
        result = await diagnostic_cache.get_document_diagnostics(sample_uri)
        assert result == diags

    @pytest.mark.asyncio
    async def test_cd02_update_document_diagnostics_does_not_write_to_workspace_diagnostics(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CD-02: update_document_diagnostics(uri, diags) does not write to workspace_diagnostics."""
        diags = [{"message": "doc error", "severity": 1}]
        await diagnostic_cache.update_document_diagnostics(sample_uri, diags)
        result = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        assert result == []

    @pytest.mark.asyncio
    async def test_cd03_update_document_diagnostics_with_result_id_sets_last_result_id(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CD-03: update_document_diagnostics with result_id sets last_result_id."""
        diags = [{"message": "doc error", "severity": 1}]
        await diagnostic_cache.update_document_diagnostics(
            sample_uri, diags, result_id="result-1"
        )
        state = await diagnostic_cache.get_file_state(sample_uri)
        assert state.last_result_id == "result-1"

    @pytest.mark.asyncio
    async def test_cd04_update_document_diagnostics_overwrites_previous(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CD-04: update_document_diagnostics overwrites previous document diagnostics."""
        diags1 = [{"message": "first error", "severity": 1}]
        diags2 = [{"message": "second error", "severity": 2}]

        await diagnostic_cache.update_document_diagnostics(sample_uri, diags1)
        await diagnostic_cache.update_document_diagnostics(sample_uri, diags2)

        result = await diagnostic_cache.get_document_diagnostics(sample_uri)
        assert result == diags2

    @pytest.mark.asyncio
    async def test_cd05_defensive_copy_mutation_does_not_affect_cache(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CD-05: Defensive copy: mutating returned list does not affect cache."""
        diags = [{"message": "doc error", "severity": 1}]
        await diagnostic_cache.update_document_diagnostics(sample_uri, diags)

        # Get and mutate
        result = await diagnostic_cache.get_document_diagnostics(sample_uri)
        result.append({"message": "new error", "severity": 2})

        # Re-read should still have original
        result2 = await diagnostic_cache.get_document_diagnostics(sample_uri)
        assert len(result2) == 1
        assert result2[0]["message"] == "doc error"


# =============================================================================
# Section 1.3: DiagnosticCache -- Workspace Diagnostic Operations
# =============================================================================


class TestWorkspaceDiagnosticOperations:
    """Tests for workspace diagnostic operations on DiagnosticCache."""

    @pytest.mark.asyncio
    async def test_cw01_update_workspace_diagnostics_stores_in_workspace_diagnostics(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CW-01: update_workspace_diagnostics(uri, diags) stores in workspace_diagnostics."""
        diags = [{"message": "ws error", "severity": 2}]
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, diags)
        result = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        assert result == diags

    @pytest.mark.asyncio
    async def test_cw02_update_workspace_diagnostics_does_not_write_to_document_diagnostics(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CW-02: update_workspace_diagnostics(uri, diags) does not write to document_diagnostics."""
        diags = [{"message": "ws error", "severity": 2}]
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, diags)
        result = await diagnostic_cache.get_document_diagnostics(sample_uri)
        assert result == []

    @pytest.mark.asyncio
    async def test_cw03_update_workspace_diagnostics_overwrites_previous(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CW-03: update_workspace_diagnostics overwrites previous workspace diagnostics."""
        diags1 = [{"message": "first ws error", "severity": 1}]
        diags2 = [{"message": "second ws error", "severity": 2}]

        await diagnostic_cache.update_workspace_diagnostics(sample_uri, diags1)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, diags2)

        result = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        assert result == diags2

    @pytest.mark.asyncio
    async def test_cw04_defensive_copy_on_both_read_paths(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CW-04: Defensive copy on both read paths."""
        diags = [{"message": "ws error", "severity": 2}]
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, diags)

        # Mutate returned list
        result = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        result.append({"message": "new error", "severity": 3})

        # Re-read should still have original
        result2 = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        assert len(result2) == 1


# =============================================================================
# Section 1.4: DiagnosticCache -- Cross-Source Isolation (Core Bug)
# =============================================================================


class TestCrossSourceIsolation:
    """Tests for cross-source isolation - the core bug fix."""

    @pytest.mark.asyncio
    async def test_ci01_write_doc_then_workspace_preserves_doc(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CI-01: Write document diags, then workspace diags: document diags preserved."""
        doc_diags = [{"message": "doc error", "severity": 1}]
        ws_diags = [{"message": "ws error", "severity": 2}]

        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)

        # Document diagnostics should be preserved
        result = await diagnostic_cache.get_document_diagnostics(sample_uri)
        assert result == doc_diags

    @pytest.mark.asyncio
    async def test_ci02_write_workspace_then_document_preserves_workspace(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CI-02: Write workspace diags, then document diags: workspace diags preserved."""
        doc_diags = [{"message": "doc error", "severity": 1}]
        ws_diags = [{"message": "ws error", "severity": 2}]

        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)
        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)

        # Workspace diagnostics should be preserved
        result = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        assert result == ws_diags

    @pytest.mark.asyncio
    async def test_ci03_overwrite_document_diagnostics_does_not_invalidate_workspace(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CI-03: Overwrite document diags does not invalidate workspace diags."""
        doc_diags1 = [{"message": "first doc error", "severity": 1}]
        doc_diags2 = [{"message": "second doc error", "severity": 2}]
        ws_diags = [{"message": "ws error", "severity": 2}]

        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags1)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)
        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags2)

        # Workspace diagnostics should be unchanged
        result = await diagnostic_cache.get_workspace_diagnostics_for_uri(sample_uri)
        assert result == ws_diags

    @pytest.mark.asyncio
    async def test_ci04_overwrite_workspace_diagnostics_does_not_invalidate_document(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CI-04: Overwrite workspace diags does not invalidate document diags."""
        doc_diags = [{"message": "doc error", "severity": 1}]
        ws_diags1 = [{"message": "first ws error", "severity": 2}]
        ws_diags2 = [{"message": "second ws error", "severity": 3}]

        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags1)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags2)

        # Document diagnostics should be unchanged
        result = await diagnostic_cache.get_document_diagnostics(sample_uri)
        assert result == doc_diags


# =============================================================================
# Section 1.5: DiagnosticCache -- get_all_workspace_diagnostics
# =============================================================================


class TestGetAllWorkspaceDiagnostics:
    """Tests for get_all_workspace_diagnostics method."""

    @pytest.mark.asyncio
    async def test_ca01_returns_workspace_diagnostics_not_document(
        self, diagnostic_cache: DiagnosticCache, temp_workspace_path: Path
    ) -> None:
        """CA-01: Returns workspace_diagnostics field, not document_diagnostics."""
        # Create file in workspace
        test_file = temp_workspace_path / "test.py"
        test_file.touch()
        sample_uri = test_file.as_uri()

        doc_diags = [{
            "message": "doc error",
            "severity": 1,
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
        }]
        ws_diags = [{
            "message": "ws error",
            "severity": 2,
            "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 5}},
        }]

        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)

        result = await diagnostic_cache.get_all_workspace_diagnostics()

        # Should return workspace diagnostics, not document diagnostics
        assert len(result) == 1
        assert len(result[0].diagnostics) == 1
        assert result[0].diagnostics[0].message == "ws error"

    @pytest.mark.asyncio
    async def test_ca02_file_with_only_document_diagnostics_excluded(
        self, diagnostic_cache: DiagnosticCache, temp_workspace_path: Path
    ) -> None:
        """CA-02: File with only document diagnostics (no workspace) excluded from result."""
        test_file = temp_workspace_path / "test.py"
        test_file.touch()
        sample_uri = test_file.as_uri()

        # Only set document diagnostics, not workspace
        doc_diags = [{
            "message": "doc error",
            "severity": 1,
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
        }]
        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)

        result = await diagnostic_cache.get_all_workspace_diagnostics()

        # Should not include file that has no workspace diagnostics
        uris = [item.uri for item in result]
        assert sample_uri not in uris

    @pytest.mark.asyncio
    async def test_ca03_file_with_both_sources_uses_workspace(
        self, diagnostic_cache: DiagnosticCache, temp_workspace_path: Path
    ) -> None:
        """CA-03: File with both sources: workspace diags used in output."""
        test_file = temp_workspace_path / "test.py"
        test_file.touch()
        sample_uri = test_file.as_uri()

        doc_diags = [{
            "message": "doc error",
            "severity": 1,
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
        }]
        ws_diags = [{
            "message": "ws error",
            "severity": 2,
            "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 5}},
        }]

        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)

        result = await diagnostic_cache.get_all_workspace_diagnostics()

        # Output should match workspace diags
        assert len(result) == 1
        assert len(result[0].diagnostics) == 1
        assert result[0].diagnostics[0].message == "ws error"

    @pytest.mark.asyncio
    async def test_ca04_empty_workspace_diagnostics_included_if_written(
        self, diagnostic_cache: DiagnosticCache, temp_workspace_path: Path
    ) -> None:
        """CA-04: Empty workspace diagnostics list: file still included if workspace source wrote to it."""
        test_file = temp_workspace_path / "test.py"
        test_file.touch()
        sample_uri = test_file.as_uri()

        # Write empty workspace diagnostics (file has no errors)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, [])

        result = await diagnostic_cache.get_all_workspace_diagnostics()

        # File should be present with empty diagnostics
        uris = [item.uri for item in result]
        assert sample_uri in uris
        for item in result:
            if item.uri == sample_uri:
                assert item.diagnostics == []

    @pytest.mark.asyncio
    async def test_ca05_workspace_diagnostic_item_shape_preserved(
        self, diagnostic_cache: DiagnosticCache, temp_workspace_path: Path
    ) -> None:
        """CA-05: Backward compat: WorkspaceDiagnosticItem shape preserved."""
        test_file = temp_workspace_path / "test.py"
        test_file.touch()
        sample_uri = test_file.as_uri()

        ws_diags = [{
            "message": "ws error",
            "severity": 2,
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
        }]
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)

        result = await diagnostic_cache.get_all_workspace_diagnostics()

        assert len(result) == 1
        item = result[0]
        # Check model structure
        assert isinstance(item, WorkspaceDiagnosticItem)
        assert hasattr(item, "uri")
        assert hasattr(item, "version")
        assert hasattr(item, "diagnostics")


# =============================================================================
# Section 1.6: DiagnosticCache -- get_diagnostics (Backward Compat)
# =============================================================================


class TestGetDiagnosticsBackwardCompat:
    """Tests for get_diagnostics backward compatibility."""

    @pytest.mark.asyncio
    async def test_cb01_get_diagnostics_returns_document_diagnostics(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CB-01: get_diagnostics(uri) returns document_diagnostics (existing callers)."""
        doc_diags = [{"message": "doc error", "severity": 1}]
        ws_diags = [{"message": "ws error", "severity": 2}]

        await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)
        await diagnostic_cache.update_workspace_diagnostics(sample_uri, ws_diags)

        # get_diagnostics should return document diagnostics, not workspace
        result = await diagnostic_cache.get_diagnostics(sample_uri)
        assert result == doc_diags

    def test_cb02_get_cached_returns_document_diagnostics(
        self, diagnostic_cache: DiagnosticCache, sample_uri: str
    ) -> None:
        """CB-02: get_cached(uri) returns document_diagnostics (sync path also uses doc diags)."""
        doc_diags = [{"message": "doc error", "severity": 1}]

        # Use sync path - need to manually set cache for sync test
        # First update via async then read via sync
        import asyncio

        async def setup() -> None:
            await diagnostic_cache.update_document_diagnostics(sample_uri, doc_diags)

        asyncio.run(setup())

        result = diagnostic_cache.get_cached(sample_uri)
        assert result == doc_diags
