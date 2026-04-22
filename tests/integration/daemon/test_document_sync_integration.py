"""Integration tests for document synchronization in daemon layer.

These tests verify the didOpen lifecycle for file-specific LSP requests.
Per ADR-001, files remain open for the session lifetime - no didClose is sent.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.daemon import DocumentSyncContext, RequestHandler
from llm_lsp_cli.lsp.cache import DiagnosticCache
from llm_lsp_cli.lsp.client import LSPClient


class TestDocumentSyncIntegration:
    """Integration tests for document sync context with daemon request handling."""

    @pytest.fixture
    def mock_lsp_client(self) -> AsyncMock:
        """Create a mock LSP client."""
        client = AsyncMock(spec=LSPClient)
        client.open_document = AsyncMock(return_value="file:///test/file.py")
        client.close_document = AsyncMock()
        client._diagnostic_cache = DiagnosticCache(Path("/workspace"))
        return client

    @pytest.fixture
    def sample_python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file."""
        content = """
def hello(name: str) -> str:
    return f"Hello, {name}!"

class Greeter:
    def greet(self, name: str) -> str:
        return hello(name)
"""
        filepath = tmp_path / "sample.py"
        filepath.write_text(content)
        return filepath

    @pytest.mark.asyncio
    async def test_document_sync_context_full_lifecycle(
        self,
        mock_lsp_client: AsyncMock,
        sample_python_file: Path,
    ) -> None:
        """Test didOpen lifecycle - file stays open per ADR-001."""
        # Simulate a request within the sync context
        async with DocumentSyncContext(mock_lsp_client, sample_python_file) as uri:
            # Verify file was opened
            mock_lsp_client.open_document.assert_called_once()
            assert uri == "file:///test/file.py"

            # Simulate a request (e.g., diagnostics)
            # In real code, this would be: await lsp_client.request_diagnostics(uri)

        # Verify file was NOT closed after exiting context (ADR-001)
        mock_lsp_client.close_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_sync_exception_safety(
        self,
        mock_lsp_client: AsyncMock,
        sample_python_file: Path,
    ) -> None:
        """Test that didClose is NOT sent even when request fails (ADR-001)."""
        request_failed = False

        try:
            async with DocumentSyncContext(mock_lsp_client, sample_python_file):
                # Simulate a failed request
                request_failed = True
                raise ValueError("Simulated request failure")
        except ValueError:
            pass

        assert request_failed, "Request should have failed"
        # Verify didOpen was sent
        mock_lsp_client.open_document.assert_called_once()
        # Verify didClose was NOT sent despite exception (ADR-001)
        mock_lsp_client.close_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_handler_has_file_locks(self) -> None:
        """Test that RequestHandler has file lock infrastructure."""
        handler = RequestHandler(
            workspace_path=".",
            language="python",
        )

        # Verify _file_locks dict exists
        assert hasattr(handler, "_file_locks")
        assert isinstance(handler._file_locks, dict)

        # Verify _get_file_lock method exists
        assert hasattr(handler, "_get_file_lock")
        assert callable(handler._get_file_lock)

    @pytest.mark.asyncio
    async def test_request_handler_get_file_lock_creates_lock(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that _get_file_lock creates locks on demand."""
        handler = RequestHandler(
            workspace_path=".",
            language="python",
        )

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        # Get lock for file
        lock1 = handler._get_file_lock(test_file)

        # Verify lock was created and stored
        assert isinstance(lock1, asyncio.Lock)
        assert str(test_file) in handler._file_locks
        assert handler._file_locks[str(test_file)] is lock1

        # Getting lock again should return same lock
        lock2 = handler._get_file_lock(test_file)
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_different_files_get_different_locks(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that different files get different lock objects."""
        handler = RequestHandler(
            workspace_path=".",
            language="python",
        )

        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")

        lock1 = handler._get_file_lock(file1)
        lock2 = handler._get_file_lock(file2)

        # Different files should have different locks
        assert lock1 is not lock2


class TestDocumentSyncWithMockedDaemon:
    """Integration tests with mocked daemon request handling."""

    @pytest.fixture
    def mock_server_registry(self) -> MagicMock:
        """Mock ServerRegistry."""
        registry = MagicMock()
        workspace = MagicMock()
        workspace.client = AsyncMock()
        workspace.client.open_document = AsyncMock(return_value="file:///test/file.py")
        workspace.client.close_document = AsyncMock()
        registry.get_or_create_workspace = AsyncMock(return_value=workspace)
        return registry

    @pytest.mark.asyncio
    async def test_request_handler_integration_with_document_sync(
        self,
        mock_server_registry: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test RequestHandler with document sync context."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        handler = RequestHandler(
            workspace_path=str(tmp_path),
            language="python",
        )
        # Replace registry with mock
        handler._registry = mock_server_registry  # type: ignore[assignment]

        # Verify handler has lock infrastructure
        lock = handler._get_file_lock(test_file)
        assert isinstance(lock, asyncio.Lock)

        # The actual integration of DocumentSyncContext into _handle_lsp_method
        # will be tested in end-to-end tests when the wiring is complete
