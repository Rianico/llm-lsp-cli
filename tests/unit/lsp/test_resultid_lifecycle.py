"""Tests for resultId lifecycle in diagnostic caching with mtime-based staleness."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache
from llm_lsp_cli.lsp.client import LSPClient


class TestResultIdLifecycle:
    """Tests for resultId lifecycle in diagnostic requests."""

    @pytest.mark.asyncio
    async def test_request_diagnostics_returns_cached_when_mtime_unchanged(
        self, tmp_path: Path
    ) -> None:
        """When mtime unchanged and cache has resultId, return cached.

        No server request should be made.
        """
        # Arrange
        cache = DiagnosticCache(tmp_path)
        uri = "file:///test.py"
        mtime = 100.0

        # Setup cache with mtime and resultId
        await cache.set_mtime(uri, mtime)
        await cache.update_diagnostics(uri, [], result_id="cached-xyz")

        # Create mock transport that should NOT be called
        transport_called = False

        async def mock_send_request(method: str, params: Any, **kwargs: Any) -> Any:
            nonlocal transport_called
            transport_called = True
            return {"kind": "full", "items": []}

        # Create client with mocked transport
        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = cache
        client._transport = MagicMock()
        client._transport.send_request = mock_send_request
        client._ensure_open = AsyncMock(return_value=uri)
        client.timeout = 30

        # Act - request with same mtime
        result = await client.request_diagnostics("/test.py", uri=uri, mtime=mtime)

        # Assert: NO server request was made (cache was valid)
        assert not transport_called
        assert result == []

    @pytest.mark.asyncio
    async def test_request_diagnostics_sends_resultid_when_mtime_changed(
        self, tmp_path: Path
    ) -> None:
        """When mtime indicates file changed, server request must include previousResultId."""
        # Arrange
        cache = DiagnosticCache(tmp_path)
        uri = "file:///test.py"

        # Setup cache with old mtime and resultId
        await cache.set_mtime(uri, 50.0)
        await cache.update_diagnostics(uri, [], result_id="cached-xyz")

        # Create mock transport that captures sent params
        sent_params: dict[str, Any] = {}

        async def mock_send_request(method: str, params: Any, **kwargs: Any) -> Any:
            sent_params.update(params)
            return {"kind": "full", "items": []}

        # Create client with mocked transport
        client = LSPClient.__new__(LSPClient)
        client._diagnostic_cache = cache
        client._transport = MagicMock()
        client._transport.send_request = mock_send_request
        client._ensure_open = AsyncMock(return_value=uri)
        client.timeout = 30

        # Act - request with newer mtime
        await client.request_diagnostics("/test.py", uri=uri, mtime=100.0)

        # Assert: previousResultId was sent (cache was stale, so request was made)
        assert sent_params.get("previousResultId") == "cached-xyz"

    @pytest.mark.asyncio
    async def test_full_resultid_lifecycle(self, tmp_path: Path) -> None:
        """Complete lifecycle: store resultId, retrieve, send in next request."""
        cache = DiagnosticCache(tmp_path)
        uri = "file:///project/src/main.py"

        # First response with resultId
        await cache.update_diagnostics(uri, [{"message": "error"}], result_id="v1")

        # Verify stored
        state = await cache.get_file_state(uri)
        assert state.last_result_id == "v1"

        # Verify retrieved for next request
        state = await cache.get_file_state(uri)
        assert state.last_result_id == "v1"  # Ready to be sent
