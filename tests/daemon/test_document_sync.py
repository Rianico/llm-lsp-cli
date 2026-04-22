"""Unit tests for DocumentSyncContext async context manager."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.daemon import DocumentSyncContext


@pytest.fixture
def mock_lsp_client() -> AsyncMock:
    """Mock LSPClient with async open_document and close_document methods."""
    from llm_lsp_cli.lsp.cache import DiagnosticCache

    client = AsyncMock()
    client.open_document = AsyncMock(return_value="file:///test/file.py")
    client.close_document = AsyncMock()
    client._diagnostic_cache = DiagnosticCache(Path("/workspace"))
    return client


@pytest.fixture
def temp_python_file(tmp_path: Path) -> Path:
    """Create a temporary Python file with sample content."""
    filepath = tmp_path / "test_file.py"
    filepath.write_text("def hello():\n    pass\n")
    return filepath


class TestDocumentSyncContext:
    """Tests for DocumentSyncContext async context manager.

    Per ADR-001, files remain open for the session lifetime.
    DocumentSyncContext sends didOpen on enter, but does NOT send didClose on exit.
    """

    @pytest.mark.asyncio
    async def test_document_sync_context_opens_but_does_not_close(
        self,
        mock_lsp_client: AsyncMock,
        temp_python_file: Path,
    ) -> None:
        """Verify didOpen sent on __aenter__, but NO didClose on __aexit__.

        Per ADR-001, files remain open for the session lifetime.
        """
        async with DocumentSyncContext(mock_lsp_client, temp_python_file) as uri:
            # Verify open_document was called
            mock_lsp_client.open_document.assert_called_once()
            assert uri == "file:///test/file.py"

        # Verify close_document was NOT called after exiting context
        # This is the key ADR-001 compliance: files stay open
        mock_lsp_client.close_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_sync_context_does_not_close_on_exception(
        self,
        mock_lsp_client: AsyncMock,
        temp_python_file: Path,
    ) -> None:
        """Verify NO didClose sent even if exception raised in context.

        Per ADR-001, files remain open for the session lifetime regardless of exceptions.
        """
        try:
            async with DocumentSyncContext(mock_lsp_client, temp_python_file) as uri:
                _ = uri  # Intentionally unused, just verifying context works
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        # Verify open_document was called
        mock_lsp_client.open_document.assert_called_once()
        # Verify close_document was NOT called despite exception
        mock_lsp_client.close_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_sync_context_returns_uri(
        self,
        mock_lsp_client: AsyncMock,
        temp_python_file: Path,
    ) -> None:
        """Verify __aenter__ returns the file URI."""
        async with DocumentSyncContext(mock_lsp_client, temp_python_file) as uri:
            assert uri is not None
            assert isinstance(uri, str)
            assert uri.startswith("file://")

    @pytest.mark.asyncio
    async def test_document_sync_reads_file_content(
        self,
        mock_lsp_client: AsyncMock,
        temp_python_file: Path,
    ) -> None:
        """Verify file content is read and passed to open_document."""
        async with DocumentSyncContext(mock_lsp_client, temp_python_file):
            pass

        # Verify open_document was called with the file path and content
        mock_lsp_client.open_document.assert_called_once()
        call_args = mock_lsp_client.open_document.call_args
        assert call_args[0][0] == temp_python_file  # First arg is file_path
        # Second arg should be the file content
        assert "def hello():" in call_args[0][1]


class TestPerFileLocking:
    """Tests for per-file locking mechanism."""

    @pytest.fixture
    def request_handler_with_locks(self) -> MagicMock:
        """Create a RequestHandler with file locks."""
        from llm_lsp_cli.daemon import RequestHandler

        handler = MagicMock(spec=RequestHandler)
        handler._file_locks: dict[str, asyncio.Lock] = {}  # type: ignore[assignment]

        def get_file_lock(file_path: Path) -> asyncio.Lock:
            path_str = str(file_path)
            if path_str not in handler._file_locks:
                handler._file_locks[path_str] = asyncio.Lock()
            return handler._file_locks[path_str]

        handler._get_file_lock = get_file_lock
        return handler

    @pytest.mark.asyncio
    async def test_per_file_lock_serializes_concurrent_requests(
        self,
        request_handler_with_locks: MagicMock,
        temp_python_file: Path,
    ) -> None:
        """Verify two concurrent requests for same file are serialized."""
        lock = request_handler_with_locks._get_file_lock(temp_python_file)
        execution_order = []

        async def task1() -> None:
            async with lock:
                execution_order.append("task1_start")
                await asyncio.sleep(0.1)
                execution_order.append("task1_end")

        async def task2() -> None:
            async with lock:
                execution_order.append("task2_start")
                await asyncio.sleep(0.05)
                execution_order.append("task2_end")

        # Run both tasks concurrently
        await asyncio.gather(task1(), task2())

        # Verify serialization: one task must complete before the other starts
        # Either task1 completes before task2, or task2 completes before task1
        t1_start = execution_order.index("task1_start")
        t1_end = execution_order.index("task1_end")
        t2_start = execution_order.index("task2_start")
        t2_end = execution_order.index("task2_end")

        # One task should complete before the other starts
        assert (t1_end < t2_start) or (t2_end < t1_start)

    @pytest.mark.asyncio
    async def test_per_file_lock_allows_different_files(
        self,
        request_handler_with_locks: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify requests for different files run concurrently."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")

        lock1 = request_handler_with_locks._get_file_lock(file1)
        lock2 = request_handler_with_locks._get_file_lock(file2)

        concurrent_execution = False

        async def task1() -> None:
            nonlocal concurrent_execution
            async with lock1:
                concurrent_execution = True
                await asyncio.sleep(0.1)

        async def task2() -> None:
            async with lock2:
                # Task2 should be able to acquire its lock while task1 holds lock1
                assert concurrent_execution, "Tasks should run concurrently for different files"

        await asyncio.gather(task1(), task2())

    @pytest.mark.asyncio
    async def test_lock_cleanup_after_use(
        self,
        request_handler_with_locks: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify locks can be cleaned up after use."""
        file1 = tmp_path / "file1.py"
        file1.write_text("content")

        lock = request_handler_with_locks._get_file_lock(file1)

        # Use the lock
        async with lock:
            pass

        # Verify lock exists in registry
        assert str(file1) in request_handler_with_locks._file_locks

        # Clean up the lock (implementation detail for future cleanup logic)
        del request_handler_with_locks._file_locks[str(file1)]
        assert str(file1) not in request_handler_with_locks._file_locks
