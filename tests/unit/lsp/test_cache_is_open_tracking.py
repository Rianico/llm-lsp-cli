"""Tests verifying DiagnosticCache.is_open tracking.

Per ADR-001, FileState.is_open tracks whether a file is open in the LSP server.
The on_did_open method must set is_open to True.
"""

from pathlib import Path

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache


class TestDiagnosticCacheIsOpenTracking:
    """Tests for is_open tracking in DiagnosticCache."""

    @pytest.mark.asyncio
    async def test_on_did_open_sets_is_open_true(self) -> None:
        """on_did_open should set is_open to True."""
        cache = DiagnosticCache(Path("/workspace"))
        uri = Path("/workspace/src/module.py").as_uri()

        # Pre-condition: file not tracked as open
        state = await cache.get_file_state(uri)
        assert state.is_open is False

        # Act
        await cache.on_did_open(uri)

        # Assert
        state = await cache.get_file_state(uri)
        assert state.is_open is True

    @pytest.mark.asyncio
    async def test_on_did_open_is_idempotent(self) -> None:
        """Calling on_did_open multiple times should keep is_open True."""
        cache = DiagnosticCache(Path("/workspace"))
        uri = Path("/workspace/src/module.py").as_uri()

        await cache.on_did_open(uri)
        state_after_first = await cache.get_file_state(uri)
        first_version = state_after_first.document_version

        await cache.on_did_open(uri)  # Second call
        state_after_second = await cache.get_file_state(uri)

        assert state_after_second.is_open is True
        # document_version should increment on each call
        assert state_after_second.document_version > first_version

    @pytest.mark.asyncio
    async def test_file_state_defaults_to_not_open(self) -> None:
        """FileState for untracked file should default is_open to False."""
        cache = DiagnosticCache(Path("/workspace"))
        uri = Path("/workspace/src/new_file.py").as_uri()

        state = await cache.get_file_state(uri)

        assert state.is_open is False
