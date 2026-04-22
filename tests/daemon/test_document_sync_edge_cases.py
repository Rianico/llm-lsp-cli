"""Edge case tests for document synchronization."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from llm_lsp_cli.daemon import DocumentSyncContext, RequestHandler


class TestDocumentSyncEdgeCases:
    """Edge case tests for DocumentSyncContext."""

    @pytest.fixture
    def mock_lsp_client(self) -> AsyncMock:
        """Create a mock LSP client."""
        client = AsyncMock()
        client.open_document = AsyncMock(return_value="file:///test/file.py")
        client.close_document = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_document_sync_with_unicode_content(
        self,
        mock_lsp_client: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test document sync with Unicode content."""
        content = """
def hello_世界() -> str:
    return "Hello, 世界！🌍"

class Émoji:
    def greet(self) -> str:
        return "👋 Hello"
"""
        filepath = tmp_path / "unicode.py"
        filepath.write_text(content, encoding="utf-8")

        async with DocumentSyncContext(mock_lsp_client, filepath):
            pass

        # Verify open_document was called
        mock_lsp_client.open_document.assert_called_once()
        call_args = mock_lsp_client.open_document.call_args
        # Verify content was read correctly with Unicode
        assert "世界" in call_args[0][1]
        assert "🌍" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_document_sync_with_empty_file(
        self,
        mock_lsp_client: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test document sync with empty file."""
        filepath = tmp_path / "empty.py"
        filepath.write_text("")

        async with DocumentSyncContext(mock_lsp_client, filepath) as uri:
            assert uri is not None

        # Verify open_document was called with empty content
        mock_lsp_client.open_document.assert_called_once()
        call_args = mock_lsp_client.open_document.call_args
        assert call_args[0][1] == ""

    @pytest.mark.asyncio
    async def test_document_sync_with_large_file(
        self,
        mock_lsp_client: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test document sync with large file."""
        filepath = tmp_path / "large.py"
        # Create a file with ~10KB content
        content = "x" * 10000 + "\n"
        filepath.write_text(content)

        async with DocumentSyncContext(mock_lsp_client, filepath):
            pass

        # Verify open_document was called with full content
        mock_lsp_client.open_document.assert_called_once()
        call_args = mock_lsp_client.open_document.call_args
        assert len(call_args[0][1]) > 10000

    @pytest.mark.asyncio
    async def test_document_sync_with_special_characters_in_path(
        self,
        mock_lsp_client: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test document sync with special characters in file path."""
        # Create directory with special characters
        special_dir = tmp_path / "test-dir_name"
        special_dir.mkdir()
        filepath = special_dir / "file with spaces.py"
        filepath.write_text("content")

        async with DocumentSyncContext(mock_lsp_client, filepath) as uri:
            # URI should be properly encoded
            assert uri.startswith("file://")

        mock_lsp_client.open_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_document_called_with_correct_uri(
        self,
        mock_lsp_client: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test that close_document receives the same URI from open_document."""
        filepath = tmp_path / "test.py"
        filepath.write_text("content")

        # Set up mock to return specific URI
        expected_uri = "file:///specific/path/test.py"
        mock_lsp_client.open_document = AsyncMock(return_value=expected_uri)

        async with DocumentSyncContext(mock_lsp_client, filepath):
            pass

        # Verify close_document was called with the same URI
        mock_lsp_client.close_document.assert_called_once()
        assert mock_lsp_client.close_document.call_args[0][0] == expected_uri

    @pytest.mark.asyncio
    async def test_document_sync_nested_contexts(
        self,
        mock_lsp_client: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test nested document sync contexts for different files."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")

        # Set up mock to return different URIs
        uris = ["file:///file1.py", "file:///file2.py"]
        call_count = 0

        def open_side_effect(*args, **kwargs):
            nonlocal call_count
            result = uris[call_count % len(uris)]
            call_count += 1
            return result

        mock_lsp_client.open_document = AsyncMock(side_effect=open_side_effect)

        async with DocumentSyncContext(mock_lsp_client, file1) as uri1:
            assert uri1 == "file:///file1.py"
            async with DocumentSyncContext(mock_lsp_client, file2) as uri2:
                assert uri2 == "file:///file2.py"
            # Inner context exited - close_document should have been called once
            assert mock_lsp_client.close_document.call_count == 1
        # Outer context exited - close_document should have been called twice
        assert mock_lsp_client.close_document.call_count == 2


class TestPerFileLockEdgeCases:
    """Edge case tests for per-file locking."""

    @pytest.fixture
    def request_handler(self) -> "RequestHandler":
        """Create RequestHandler instance."""
        from llm_lsp_cli.daemon import RequestHandler

        return RequestHandler(workspace_path=".", language="python")

    @pytest.mark.asyncio
    async def test_lock_released_after_exception(
        self,
        request_handler: "RequestHandler",
        tmp_path: Path,
    ) -> None:
        """Test that lock is released after exception in critical section."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        lock = request_handler._get_file_lock(test_file)

        async def failing_task() -> None:
            async with lock:
                raise ValueError("Simulated failure")

        # Run failing task
        with pytest.raises(ValueError):
            await failing_task()

        # Lock should be released and available for next acquisition
        async with lock:
            pass  # Should not deadlock

    @pytest.mark.asyncio
    async def test_multiple_sequential_lock_acquisitions(
        self,
        request_handler: "RequestHandler",
        tmp_path: Path,
    ) -> None:
        """Test multiple sequential lock acquisitions for same file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        lock = request_handler._get_file_lock(test_file)

        # Acquire and release lock multiple times
        for _ in range(5):
            async with lock:
                await asyncio.sleep(0.001)  # Small delay

        # Should complete without deadlock
        assert True

    @pytest.mark.asyncio
    async def test_lock_registry_growth(
        self,
        request_handler: "RequestHandler",
        tmp_path: Path,
    ) -> None:
        """Test that lock registry grows with new files."""
        # Create many files
        files = [tmp_path / f"file_{i}.py" for i in range(10)]
        for f in files:
            f.write_text("content")

        # Get locks for all files
        locks = []
        for f in files:
            lock = request_handler._get_file_lock(f)
            locks.append(lock)

        # Verify all locks are unique
        assert len(set(id(lock) for lock in locks)) == 10
        assert len(request_handler._file_locks) == 10


class TestDocumentSyncCleanup:
    """Tests for cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_context_closes_document_on_keyboard_interrupt(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that document is closed on KeyboardInterrupt."""
        from llm_lsp_cli.daemon import DocumentSyncContext

        mock_client = AsyncMock()
        mock_client.open_document = AsyncMock(return_value="file:///test/file.py")
        mock_client.close_document = AsyncMock()

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        try:
            async with DocumentSyncContext(mock_client, test_file):
                raise KeyboardInterrupt("Simulated interrupt")
        except KeyboardInterrupt:
            pass

        # Verify cleanup happened despite interrupt
        mock_client.open_document.assert_called_once()
        mock_client.close_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_closes_document_on_base_exception(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that document is closed on BaseException."""
        from llm_lsp_cli.daemon import DocumentSyncContext

        mock_client = AsyncMock()
        mock_client.open_document = AsyncMock(return_value="file:///test/file.py")
        mock_client.close_document = AsyncMock()

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        try:
            async with DocumentSyncContext(mock_client, test_file):
                raise SystemExit("Simulated exit")
        except SystemExit:
            pass

        # Verify cleanup happened
        mock_client.close_document.assert_called_once()
