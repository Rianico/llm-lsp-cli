"""End-to-end integration tests for document synchronization (P1+P3)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.daemon import RequestHandler
from llm_lsp_cli.lsp.constants import LSPConstants


class TestEndToEndDocumentSync:
    """End-to-end tests for complete document sync lifecycle."""

    @pytest.mark.asyncio
    async def test_end_to_end_diagnostic_with_document_sync(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify complete didOpen -> diagnostic -> didClose sequence."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        handler = RequestHandler(workspace_path=str(tmp_path), language="python")

        # Mock transport to capture LSP messages
        sent_notifications = []
        sent_requests = []

        async def mock_send_notification(method: str, params: dict) -> None:
            sent_notifications.append((method, params))

        async def mock_send_request(method: str, params: dict, timeout: float) -> dict:
            sent_requests.append((method, params))
            return {"items": []}  # Empty diagnostics

        # Patch the LSP client's transport
        workspace = await handler._registry.get_or_create_workspace(str(tmp_path))
        client = await workspace.ensure_initialized()
        client._transport = AsyncMock()
        client._transport.send_notification = AsyncMock(side_effect=mock_send_notification)
        client._transport.send_request = AsyncMock(side_effect=mock_send_request)
        client._transport.on_notification = MagicMock()
        client._transport.on_request = MagicMock()
        client._transport.send_request_fire_and_forget = AsyncMock()

        # Mock the router
        handler._router = MagicMock()
        handler._router.get_config = lambda m: MagicMock(
            registry_method="request_diagnostics"
        )

        # Execute diagnostic request
        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
        }
        result = await handler._handle_lsp_method(LSPConstants.DIAGNOSTIC, params)

        # Verify sequence: didOpen -> diagnostic -> didClose
        # This test will fail until P1 is implemented
        assert len(sent_notifications) >= 2, (
            f"Expected at least 2 notifications (didOpen, didClose), got {len(sent_notifications)}"
        )
        notification_methods = [n[0] for n in sent_notifications]
        assert LSPConstants.TEXT_DOCUMENT_DID_OPEN in notification_methods, (
            f"didOpen not found in {notification_methods}"
        )
        assert LSPConstants.TEXT_DOCUMENT_DID_CLOSE in notification_methods, (
            f"didClose not found in {notification_methods}"
        )

        # Verify diagnostic request was sent
        assert any(msg[0] == LSPConstants.DIAGNOSTIC for msg in sent_requests), (
            f"Diagnostic request not found in {sent_requests}"
        )

    @pytest.mark.asyncio
    async def test_end_to_end_document_symbol_with_document_sync(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify complete didOpen -> documentSymbol -> didClose sequence."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        handler = RequestHandler(workspace_path=str(tmp_path), language="python")

        sent_notifications = []
        sent_requests = []

        async def mock_send_notification(method: str, params: dict) -> None:
            sent_notifications.append((method, params))

        async def mock_send_request(method: str, params: dict, timeout: float) -> list:
            sent_requests.append((method, params))
            return []  # Empty symbols

        workspace = await handler._registry.get_or_create_workspace(str(tmp_path))
        client = await workspace.ensure_initialized()
        client._transport = AsyncMock()
        client._transport.send_notification = AsyncMock(side_effect=mock_send_notification)
        client._transport.send_request = AsyncMock(side_effect=mock_send_request)
        client._transport.on_notification = MagicMock()
        client._transport.on_request = MagicMock()
        client._transport.send_request_fire_and_forget = AsyncMock()

        handler._router = MagicMock()
        handler._router.get_config = lambda m: MagicMock(
            registry_method="request_document_symbols"
        )

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
        }
        result = await handler._handle_lsp_method(LSPConstants.DOCUMENT_SYMBOL, params)

        # Verify sequence
        assert len(sent_notifications) >= 2
        notification_methods = [n[0] for n in sent_notifications]
        assert LSPConstants.TEXT_DOCUMENT_DID_OPEN in notification_methods
        assert LSPConstants.TEXT_DOCUMENT_DID_CLOSE in notification_methods

        assert any(msg[0] == LSPConstants.DOCUMENT_SYMBOL for msg in sent_requests)

    @pytest.mark.asyncio
    async def test_concurrent_diagnostics_for_different_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify concurrent requests for different files run in parallel."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")

        handler = RequestHandler(workspace_path=str(tmp_path), language="python")

        # Track concurrent execution
        concurrent_count = 0
        max_concurrent = 0

        async def track_concurrency(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return []

        # Mock workspace and client
        mock_workspace = MagicMock()
        mock_client = AsyncMock()
        mock_client.request_diagnostics = track_concurrency
        mock_client.open_document = AsyncMock(side_effect=lambda fp, content: fp.as_uri())
        mock_client.close_document = AsyncMock()
        mock_workspace.ensure_initialized = AsyncMock(return_value=mock_client)

        handler._registry.get_or_create_workspace = AsyncMock(return_value=mock_workspace)
        handler._router = MagicMock()
        handler._router.get_config = lambda m: MagicMock(
            registry_method="request_diagnostics"
        )

        # Run concurrent requests for different files
        await asyncio.gather(
            handler._handle_lsp_method(
                LSPConstants.DIAGNOSTIC,
                {"workspacePath": str(tmp_path), "filePath": str(file1)},
            ),
            handler._handle_lsp_method(
                LSPConstants.DIAGNOSTIC,
                {"workspacePath": str(tmp_path), "filePath": str(file2)},
            ),
        )

        # Different files should run concurrently (max_concurrent == 2)
        assert max_concurrent == 2, f"Expected 2 concurrent, got {max_concurrent}"


class TestDocumentSyncEdgeCases:
    """Edge case tests for document synchronization."""

    @pytest.mark.asyncio
    async def test_document_sync_with_unicode_content(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify document sync handles Unicode content correctly."""
        test_file = tmp_path / "unicode.py"
        content = "def hello_世界():\n    return 'Hello, 世界！🌍'"
        test_file.write_text(content, encoding="utf-8")

        handler = RequestHandler(workspace_path=str(tmp_path), language="python")

        sent_notifications = []

        async def mock_send_notification(method: str, params: dict) -> None:
            sent_notifications.append((method, params))

        async def mock_send_request(method: str, params: dict, timeout: float) -> dict:
            return {"items": []}

        workspace = await handler._registry.get_or_create_workspace(str(tmp_path))
        client = await workspace.ensure_initialized()
        client._transport = AsyncMock()
        client._transport.send_notification = AsyncMock(side_effect=mock_send_notification)
        client._transport.send_request = AsyncMock(side_effect=mock_send_request)
        client._transport.on_notification = MagicMock()
        client._transport.on_request = MagicMock()
        client._transport.send_request_fire_and_forget = AsyncMock()

        handler._router = MagicMock()
        handler._router.get_config = lambda m: MagicMock(
            registry_method="request_diagnostics"
        )

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
        }
        await handler._handle_lsp_method(LSPConstants.DIAGNOSTIC, params)

        # Verify didOpen was sent with Unicode content
        did_open_notifications = [
            n for n in sent_notifications if n[0] == LSPConstants.TEXT_DOCUMENT_DID_OPEN
        ]
        assert len(did_open_notifications) == 1
        did_open_params = did_open_notifications[0][1]
        assert "世界" in did_open_params["textDocument"]["text"]
        assert "🌍" in did_open_params["textDocument"]["text"]

    @pytest.mark.asyncio
    async def test_document_sync_with_empty_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify document sync handles empty files."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        handler = RequestHandler(workspace_path=str(tmp_path), language="python")

        sent_notifications = []

        async def mock_send_notification(method: str, params: dict) -> None:
            sent_notifications.append((method, params))

        async def mock_send_request(method: str, params: dict, timeout: float) -> dict:
            return {"items": []}

        workspace = await handler._registry.get_or_create_workspace(str(tmp_path))
        client = await workspace.ensure_initialized()
        client._transport = AsyncMock()
        client._transport.send_notification = AsyncMock(side_effect=mock_send_notification)
        client._transport.send_request = AsyncMock(side_effect=mock_send_request)
        client._transport.on_notification = MagicMock()
        client._transport.on_request = MagicMock()
        client._transport.send_request_fire_and_forget = AsyncMock()

        handler._router = MagicMock()
        handler._router.get_config = lambda m: MagicMock(
            registry_method="request_diagnostics"
        )

        params = {
            "workspacePath": str(tmp_path),
            "filePath": str(test_file),
        }
        await handler._handle_lsp_method(LSPConstants.DIAGNOSTIC, params)

        # Verify didOpen was sent
        did_open_notifications = [
            n for n in sent_notifications if n[0] == LSPConstants.TEXT_DOCUMENT_DID_OPEN
        ]
        assert len(did_open_notifications) == 1
