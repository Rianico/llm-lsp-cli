"""Regression tests for the workspace diagnostics stale data bug.

Test scenario from spec section 1.11:
- The original bug: workspace-diagnostics returns stale data after publishDiagnostics resolves a diagnostic
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.lsp import types as lsp
from llm_lsp_cli.lsp.client import LSPClient


@pytest.fixture
async def lsp_client(temp_dir: Path) -> LSPClient:
    """Create LSPClient with mocked transport."""
    client = LSPClient(
        workspace_path=str(temp_dir),
        server_command="pyright-langserver",
        server_args=["--stdio"],
        language_id="python",
    )

    mock_typed_transport = MagicMock()
    mock_typed_transport.start = AsyncMock()
    mock_typed_transport.stop = AsyncMock()
    mock_typed_transport.send_notification = AsyncMock()
    mock_typed_transport.send_request_fire_and_forget = AsyncMock()
    mock_typed_transport.send_request = AsyncMock()
    mock_typed_transport.on_notification = MagicMock()
    mock_typed_transport.on_request = MagicMock()
    mock_typed_transport.send_initialize = AsyncMock(
        return_value=lsp.InitializeResult(capabilities=lsp.ServerCapabilities())
    )

    with patch("llm_lsp_cli.lsp.client.TypedLSPTransport", return_value=mock_typed_transport):
        await client.initialize()
        client._mock_transport = mock_typed_transport  # type: ignore
        yield client


# =============================================================================
# Section 1.11: Regression -- The Bug Scenario
# =============================================================================


class TestDiagnosticsIsolationRegression:
    """Regression tests for the stale workspace diagnostics bug."""

    @pytest.mark.asyncio
    async def test_rg01_bug_scenario_full_flow(self, lsp_client: LSPClient, temp_dir: Path) -> None:
        """RG-01: Full bug scenario - doc and ws outputs are independent and correct.

        Scenario:
        1. Workspace diag reports error on file A.
        2. User fixes error, publishDiagnostics pushes empty list.
        3. lsp diagnostics A returns empty.
        4. lsp workspace-diagnostics still shows error until next $/progress.
        """
        # Setup
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        error_diag = [{
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
            "severity": 1,
            "message": "Unresolved import",
            "source": "pyright",
        }]

        # 1. Workspace diag reports error on file A (via $/progress)
        token = lsp_client.get_workspace_diagnostic_token()
        lsp_client._handle_progress({
            "token": token,
            "value": {
                "items": [{"uri": test_uri, "diagnostics": error_diag}]
            },
        })
        await asyncio.sleep(0.01)

        # Verify workspace has the error
        ws_result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert len(ws_result) == 1
        assert ws_result[0]["message"] == "Unresolved import"

        # 2. User fixes error, publishDiagnostics pushes empty list
        lsp_client._handle_diagnostics({"uri": test_uri, "diagnostics": []})
        await asyncio.sleep(0.01)

        # 3. lsp diagnostics A returns empty (correct - document diags are empty)
        doc_result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        assert doc_result == []

        # 4. lsp workspace-diagnostics still shows error (correct - workspace diags unchanged)
        ws_result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert len(ws_result) == 1
        assert ws_result[0]["message"] == "Unresolved import"

    @pytest.mark.asyncio
    async def test_rg02_workspace_progress_updates_only_workspace(
        self, lsp_client: LSPClient, temp_dir: Path
    ) -> None:
        """RG-02: Each source updates only its own field.

        Scenario:
        1. Workspace diag reports error on file A.
        2. Next $/progress reports no errors on file A.
        3. lsp workspace-diagnostics now shows no errors.
        4. lsp diagnostics A still shows whatever document diags were last pushed.
        """
        # Setup
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        error_diag = [{
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
            "severity": 1,
            "message": "Type error",
            "source": "pyright",
        }]

        doc_diag = [{
            "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 5}},
            "severity": 2,
            "message": "Unused variable",
            "source": "pyright",
        }]

        # 1. Workspace diag reports error on file A
        token = lsp_client.get_workspace_diagnostic_token()
        lsp_client._handle_progress({
            "token": token,
            "value": {
                "items": [{"uri": test_uri, "diagnostics": error_diag}]
            },
        })
        await asyncio.sleep(0.01)

        # Also set some document diagnostics (simulating previous publishDiagnostics)
        await lsp_client._diagnostic_cache.update_document_diagnostics(test_uri, doc_diag)

        # 2. Next $/progress reports no errors on file A
        lsp_client._handle_progress({
            "token": token,
            "value": {
                "items": [{"uri": test_uri, "diagnostics": []}]
            },
        })
        await asyncio.sleep(0.01)

        # 3. lsp workspace-diagnostics now shows no errors
        ws_result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)
        assert ws_result == []

        # 4. lsp diagnostics A still shows document diags (unchanged)
        doc_result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        assert len(doc_result) == 1
        assert doc_result[0]["message"] == "Unused variable"

    @pytest.mark.asyncio
    async def test_rg03_both_sources_can_report_different_diagnostics(
        self, lsp_client: LSPClient, temp_dir: Path
    ) -> None:
        """RG-03: Document and workspace can report different diagnostics simultaneously.

        This tests the independence of the two sources.
        """
        # Setup
        test_file = temp_dir / "test.py"
        test_file.write_text("# test")
        test_uri = test_file.as_uri()

        doc_diags = [{
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}},
            "severity": 1,
            "message": "Document error",
            "source": "pyright",
        }]

        ws_diags = [{
            "range": {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 10}},
            "severity": 2,
            "message": "Workspace warning",
            "source": "pyright",
        }]

        # Set both independently
        await lsp_client._diagnostic_cache.update_document_diagnostics(test_uri, doc_diags)
        token = lsp_client.get_workspace_diagnostic_token()
        lsp_client._handle_progress({
            "token": token,
            "value": {
                "items": [{"uri": test_uri, "diagnostics": ws_diags}]
            },
        })
        await asyncio.sleep(0.01)

        # Both should be preserved independently
        doc_result = await lsp_client._diagnostic_cache.get_document_diagnostics(test_uri)
        ws_result = await lsp_client._diagnostic_cache.get_workspace_diagnostics_for_uri(test_uri)

        assert len(doc_result) == 1
        assert doc_result[0]["message"] == "Document error"

        assert len(ws_result) == 1
        assert ws_result[0]["message"] == "Workspace warning"
