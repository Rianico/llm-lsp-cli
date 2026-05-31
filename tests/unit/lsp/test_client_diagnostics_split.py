"""Tests for LSPClient diagnostic handlers with split diagnostics.

Test scenarios from spec sections 1.7-1.10:
- LSPClient._handle_diagnostics (publishDiagnostics notification)
- LSPClient._handle_workspace_diagnostic_progress ($/progress)
- LSPClient.request_diagnostics
- LSPClient.request_workspace_diagnostics
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp import types as lsp
from llm_lsp_cli.lsp.client import LSPClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def lsp_client(temp_dir: Path) -> LSPClient:
    """Create LSPClient with mocked transport."""
    client = LSPClient(
        workspace_path=str(temp_dir),
        server_command="pyright-langserver",
        server_args=["--stdio"],
        language_id="python",
    )

    # Create a mock StdioTransport
    mock_transport = MagicMock()
    mock_transport.start = AsyncMock()
    mock_transport.stop = AsyncMock()
    mock_transport.send_notification = AsyncMock()
    mock_transport.send_request_fire_and_forget = AsyncMock()
    mock_transport.send_request = AsyncMock()
    mock_transport.on_notification = MagicMock()
    mock_transport.on_request = MagicMock()
    mock_transport.send_request.return_value = {
        "capabilities": lsp.ServerCapabilities().model_dump(mode="json", by_alias=True),
    }

    # Patch StdioTransport to return our mock
    with patch("llm_lsp_cli.lsp.client.StdioTransport", return_value=mock_transport):
        await client.initialize()
        client._mock_transport = mock_transport  # type: ignore
        yield client


@pytest.fixture
def doc_diagnostics() -> list[dict[str, object]]:
    """Document diagnostics fixture."""
    return [
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 5},
            },
            "severity": 1,
            "message": "Doc error",
            "source": "pyright",
        }
    ]


@pytest.fixture
def ws_diagnostics() -> list[dict[str, object]]:
    """Workspace diagnostics fixture."""
    return [
        {
            "range": {
                "start": {"line": 5, "character": 0},
                "end": {"line": 5, "character": 10},
            },
            "severity": 2,
            "message": "WS warning",
            "source": "pyright",
        }
    ]


# =============================================================================
# Section 1.7: LSPClient -- _handle_diagnostics
# =============================================================================


class TestHandleDiagnostics:
    """Tests for _handle_diagnostics handler (publishDiagnostics notification)."""

    @pytest.mark.asyncio
    async def test_hd01_publish_diagnostics_calls_update_document_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path, doc_diagnostics: list[dict[str, object]]
    ) -> None:
        """HD-01: publishDiagnostics notification calls update_document_diagnostics."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Simulate publishDiagnostics notification
        params = {
            "uri": test_uri,
            "diagnostics": doc_diagnostics,
        }

        lsp_client._handle_diagnostics(params)
        await asyncio.sleep(0.01)  # Let async task complete

        # Verify document_diagnostics was updated
        result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        assert len(result) == 1
        assert result[0]["message"] == "Doc error"

    @pytest.mark.asyncio
    async def test_hd02_publish_diagnostics_does_not_touch_workspace_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path,
        doc_diagnostics: list[dict[str, object]],
        ws_diagnostics: list[dict[str, object]]
    ) -> None:
        """HD-02: publishDiagnostics does not touch workspace_diagnostics."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Pre-populate workspace diagnostics
        await lsp_client._diagnostic_cache.update_workspace_diagnostics(test_uri, ws_diagnostics)

        # Simulate publishDiagnostics notification (clearing document diags)
        params = {
            "uri": test_uri,
            "diagnostics": [],  # User fixed the error
        }

        lsp_client._handle_diagnostics(params)
        await asyncio.sleep(0.01)

        # Workspace diagnostics should be unchanged
        result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert len(result) == 1
        assert result[0]["message"] == "WS warning"


# =============================================================================
# Section 1.8: LSPClient -- _handle_workspace_diagnostic_progress
# =============================================================================


class TestHandleWorkspaceDiagnosticProgress:
    """Tests for _handle_workspace_diagnostic_progress handler ($/progress)."""

    @pytest.mark.asyncio
    async def test_hp01_progress_calls_update_workspace_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path, ws_diagnostics: list[dict[str, object]]
    ) -> None:
        """HP-01: $/progress with items calls update_workspace_diagnostics."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Get the workspace diagnostic token
        token = lsp_client.get_workspace_diagnostic_token()

        # Create progress params
        params = {
            "token": token,
            "value": {
                "items": [
                    {
                        "uri": test_uri,
                        "diagnostics": ws_diagnostics,
                    }
                ],
            },
        }

        lsp_client._handle_progress(params)
        await asyncio.sleep(0.01)

        # Verify workspace_diagnostics was updated
        result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert len(result) == 1
        assert result[0]["message"] == "WS warning"

    @pytest.mark.asyncio
    async def test_hp02_progress_does_not_touch_document_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path,
        doc_diagnostics: list[dict[str, object]],
        ws_diagnostics: list[dict[str, object]]
    ) -> None:
        """HP-02: $/progress items do not touch document_diagnostics."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Pre-populate document diagnostics
        await lsp_client._diagnostic_cache.update_document_diagnostics(test_uri, doc_diagnostics)

        # Get the workspace diagnostic token
        token = lsp_client.get_workspace_diagnostic_token()

        # Create progress params
        params = {
            "token": token,
            "value": {
                "items": [
                    {
                        "uri": test_uri,
                        "diagnostics": ws_diagnostics,
                    }
                ],
            },
        }

        lsp_client._handle_progress(params)
        await asyncio.sleep(0.01)

        # Document diagnostics should be unchanged
        result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        assert len(result) == 1
        assert result[0]["message"] == "Doc error"


# =============================================================================
# Section 1.9: LSPClient -- request_diagnostics
# =============================================================================


class TestRequestDiagnostics:
    """Tests for request_diagnostics method."""

    @pytest.mark.asyncio
    async def test_rd01_cache_hit_returns_document_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path, doc_diagnostics: list[dict[str, object]]
    ) -> None:
        """RD-01: Cache hit returns document_diagnostics."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Set up document diagnostics and result_id for cache hit
        await lsp_client._diagnostic_cache.update_document_diagnostics(
            test_uri, doc_diagnostics, result_id="result-1"
        )
        await lsp_client._diagnostic_cache.set_mtime(test_uri, 100.0)

        # Request diagnostics with same mtime (cache hit)
        result = await lsp_client.request_diagnostics(
            str(test_file), uri=test_uri, mtime=100.0
        )

        # Should return document diagnostics
        assert len(result) == 1
        assert result[0]["message"] == "Doc error"

    @pytest.mark.asyncio
    async def test_rd02_fresh_response_stores_to_document_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path,
        ws_diagnostics: list[dict[str, object]]
    ) -> None:
        """RD-02: Fresh response stores into document_diagnostics via update_document_diagnostics."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Pre-populate workspace diagnostics (should not be affected)
        await lsp_client._diagnostic_cache.update_workspace_diagnostics(test_uri, ws_diagnostics)

        # Mock transport response for fresh diagnostics
        fresh_diags = [{"message": "fresh error", "severity": 1, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}}}]
        lsp_client._mock_transport.send_request = AsyncMock(
            return_value={"items": fresh_diags, "resultId": "new-result"}
        )

        # Request diagnostics (cache miss, fresh response)
        result = await lsp_client.request_diagnostics(
            str(test_file), uri=test_uri, mtime=200.0
        )

        # Document diagnostics should be updated
        doc_result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        assert len(doc_result) == 1
        assert doc_result[0]["message"] == "fresh error"

        # Workspace diagnostics should be unchanged
        ws_result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert len(ws_result) == 1
        assert ws_result[0]["message"] == "WS warning"


# =============================================================================
# Section 1.10: LSPClient -- request_workspace_diagnostics
# =============================================================================


class TestRequestWorkspaceDiagnostics:
    """Tests for request_workspace_diagnostics method."""

    @pytest.mark.asyncio
    async def test_rw01_returns_items_from_workspace_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path, ws_diagnostics: list[dict[str, object]]
    ) -> None:
        """RW-01: Returns items from workspace_diagnostics field."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # Set workspace diagnostics
        await lsp_client._diagnostic_cache.update_workspace_diagnostics(test_uri, ws_diagnostics)

        # Mark workspace as indexed
        lsp_client._workspace_indexed.set()

        result = await lsp_client.request_workspace_diagnostics()

        # Should return workspace diagnostics
        assert len(result) >= 1
        # Find our file
        for item in result:
            if item.uri == test_uri:
                assert len(item.diagnostics) == 1
                assert item.diagnostics[0].message == "WS warning"
                break
        else:
            pytest.fail(f"File {test_uri} not found in workspace diagnostics")

    @pytest.mark.asyncio
    async def test_rw02_resolving_via_publish_diagnostics_does_not_affect_workspace_output(
        self, lsp_client: LSPClient, temp_dir: Path,
        doc_diagnostics: list[dict[str, object]],
        ws_diagnostics: list[dict[str, object]]
    ) -> None:
        """RW-02: Resolving a diagnostic via publishDiagnostics does not affect workspace output."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        # 1. Workspace diag reports error on file
        await lsp_client._diagnostic_cache.update_workspace_diagnostics(test_uri, ws_diagnostics)

        # 2. User fixes error, publishDiagnostics pushes empty list
        lsp_client._handle_diagnostics({"uri": test_uri, "diagnostics": []})
        await asyncio.sleep(0.01)

        # 3. lsp diagnostics A returns empty
        doc_result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        assert doc_result == []

        # 4. lsp workspace-diagnostics still shows error until next $/progress
        ws_result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert len(ws_result) == 1
        assert ws_result[0]["message"] == "WS warning"
