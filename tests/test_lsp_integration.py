"""Integration tests for LSP client with real pyright-langserver server.

These tests require pyright-langserver to be installed:
    pip install pyright
    # or
    npm install -g pyright

Run with:
    uv run pytest tests/test_lsp_integration.py -v

Note: These tests are currently skipped due to pyright initialization timeout issues.
"""

import asyncio
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from llm_lsp_cli.lsp.client import LSPClient

from .conftest import is_pyright_langserver_installed


class TestLSPClientIntegration:
    """Integration tests with real LSP server.

    Note: These tests require pyright-langserver to be installed.
    Skip if pyright-langserver is not available.
    """

    @pytest.fixture
    def test_workspace(self) -> Generator[Path, None, None]:
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def test_python_file(self, test_workspace: Path) -> Path:
        """Create a test Python file."""
        file_path = test_workspace / "test_module.py"
        file_path.write_text("""
def hello(name):
    '''Say hello to someone.'''
    return f"Hello, {name}!"

class Greeter:
    '''A greeter class.'''

    def __init__(self, greeting="Hello"):
        self.greeting = greeting

    def greet(self, name):
        return f"{self.greeting}, {name}!"

# Main execution
if __name__ == "__main__":
    print(hello("World"))
""")
        return file_path

    @pytest.mark.asyncio
    async def test_lsp_client_initialize(self, test_workspace) -> None:  # type: ignore
        """Test LSP client initialization with real server."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        client = LSPClient(
            workspace_path=str(test_workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
            timeout=5.0,
            trace=True,
        )

        try:
            result = await client.initialize()
            assert result is not None
            assert "capabilities" in result
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_lsp_client_definition(self, test_workspace, test_python_file) -> None:  # type: ignore
        """Test definition lookup with real server."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        client = LSPClient(
            workspace_path=str(test_workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
            timeout=5.0,
            trace=True,
        )

        try:
            await client.initialize()

            # Request definition of 'hello' function (defined at line 1, used at line 17)
            # Position is 0-based, so line 16 (print statement), character where 'hello' starts
            locations = await client.request_definition(str(test_python_file), 16, 10)

            # Should find the definition
            assert isinstance(locations, list)
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_lsp_client_references(self, test_workspace, test_python_file) -> None:  # type: ignore
        """Test references lookup with real server."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        client = LSPClient(
            workspace_path=str(test_workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
            timeout=5.0,
            trace=True,
        )

        try:
            await client.initialize()

            # Request references to 'hello' function (defined at line 1)
            locations = await client.request_references(str(test_python_file), 1, 4)

            # Should find references
            assert isinstance(locations, list)
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_lsp_client_hover(self, test_workspace, test_python_file) -> None:  # type: ignore
        """Test hover information with real server."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        client = LSPClient(
            workspace_path=str(test_workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
            timeout=5.0,
            trace=True,
        )

        try:
            await client.initialize()

            # Request hover for 'hello' function
            hover = await client.request_hover(str(test_python_file), 1, 4)

            # Should get hover information
            assert hover is not None
            assert "contents" in hover
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_lsp_client_completions(self, test_workspace, test_python_file) -> None:  # type: ignore
        """Test completions with real server."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        client = LSPClient(
            workspace_path=str(test_workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
            timeout=5.0,
            trace=True,
        )

        try:
            await client.initialize()

            # Request completions at end of line 1 (inside function definition)
            items = await client.request_completions(str(test_python_file), 1, 10)

            # Should get some completions
            assert isinstance(items, list)
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_lsp_client_document_symbols(self, test_workspace, test_python_file) -> None:  # type: ignore
        """Test document symbols with real server."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        client = LSPClient(
            workspace_path=str(test_workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
            language_id="python",
            timeout=5.0,
            trace=True,
        )

        try:
            await client.initialize()

            symbols = await client.request_document_symbols(str(test_python_file))

            # Should find hello function, Greeter class, etc.
            assert isinstance(symbols, list)
            assert len(symbols) > 0

            # Check for expected symbols
            symbol_names = [s.get("name") for s in symbols]
            assert "hello" in symbol_names
            assert "Greeter" in symbol_names
        finally:
            await client.shutdown()


class TestLSPClientMultipleWorkspaces:
    """Test multiple workspace management."""

    @pytest.mark.asyncio
    async def test_multiple_workspace_isolation(self) -> None:
        """Test that multiple workspaces are isolated."""
        # Skip if pyright-langserver is not installed
        if not is_pyright_langserver_installed():
            pytest.skip("pyright-langserver not installed")

        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:

            workspace1 = Path(tmpdir1)
            workspace2 = Path(tmpdir2)

            # Create different files in each workspace
            (workspace1 / "file1.py").write_text("def func1(): pass")
            (workspace2 / "file2.py").write_text("def func2(): pass")

            # Create clients for each workspace
            client1 = LSPClient(
                workspace_path=str(workspace1),
                server_command="pyright-langserver",
                server_args=["--stdio"],
                language_id="python",
            )
            client2 = LSPClient(
                workspace_path=str(workspace2),
                server_command="pyright-langserver",
                server_args=["--stdio"],
                language_id="python",
            )

            try:
                await client1.initialize()
                await client2.initialize()

                # Each client should only see its own workspace symbols
                symbols1 = await client1.request_document_symbols(str(workspace1 / "file1.py"))
                symbols2 = await client2.request_document_symbols(str(workspace2 / "file2.py"))

                symbol_names_1 = [s.get("name") for s in symbols1]
                symbol_names_2 = [s.get("name") for s in symbols2]

                assert "func1" in symbol_names_1
                assert "func2" in symbol_names_2
                assert "func1" not in symbol_names_2
                assert "func2" not in symbol_names_1

            finally:
                await client1.shutdown()
                await client2.shutdown()


class TestDocumentSynchronization:
    """Test document readiness synchronization mechanism."""

    @pytest.mark.asyncio
    async def test_diagnostics_handler_sets_ready_event(self) -> None:
        """Test that diagnostics handler sets the ready event."""
        import asyncio

        from llm_lsp_cli.lsp.client import LSPClient

        with tempfile.TemporaryDirectory() as tmpdir:
            client = LSPClient(
                workspace_path=tmpdir,
                server_command="pyright-langserver",
                server_args=["--stdio"],
            )

            # Create a ready event and put it in _open_files
            uri = "file:///test.py"
            ready_event = asyncio.Event()
            client._open_files[uri] = ("content", 0, ready_event)

            # Simulate receiving diagnostics
            client._handle_diagnostics({"uri": uri, "diagnostics": []})

            # Event should be set
            assert ready_event.is_set()

    @pytest.mark.asyncio
    async def test_diagnostics_handler_only_sets_once(self) -> None:
        """Test that ready event is only set once."""
        import asyncio

        from llm_lsp_cli.lsp.client import LSPClient

        with tempfile.TemporaryDirectory() as tmpdir:
            client = LSPClient(
                workspace_path=tmpdir,
                server_command="pyright-langserver",
                server_args=["--stdio"],
            )

            # Create a ready event and put it in _open_files
            uri = "file:///test.py"
            ready_event = asyncio.Event()
            client._open_files[uri] = ("content", 0, ready_event)

            # Simulate receiving diagnostics multiple times
            client._handle_diagnostics({"uri": uri, "diagnostics": []})
            client._handle_diagnostics({"uri": uri, "diagnostics": []})
            client._handle_diagnostics({"uri": uri, "diagnostics": []})

            # Event should still be set (only once)
            assert ready_event.is_set()

    @pytest.mark.asyncio
    async def test_diagnostics_handler_ignores_unknown_uri(self) -> None:
        """Test that diagnostics for unknown URI don't crash."""
        from llm_lsp_cli.lsp.client import LSPClient

        with tempfile.TemporaryDirectory() as tmpdir:
            client = LSPClient(
                workspace_path=tmpdir,
                server_command="pyright-langserver",
                server_args=["--stdio"],
            )

            # Simulate receiving diagnostics for unknown URI
            # Should not raise any exception
            client._handle_diagnostics({"uri": "file:///unknown.py", "diagnostics": []})

            # _open_files should still be empty
            assert len(client._open_files) == 0

    @pytest.mark.asyncio
    async def test_ensure_open_waits_for_ready_event(self) -> None:
        """Test that _ensure_open waits for the ready event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"
            test_file.write_text("def hello(): pass")

            client = LSPClient(
                workspace_path=tmpdir,
                server_command="pyright-langserver",
                server_args=["--stdio"],
            )

            # Mock the transport
            mock_transport = AsyncMock()
            mock_transport.send_notification = AsyncMock()
            client._transport = mock_transport

            # Mock _handle_diagnostics to simulate receiving diagnostics
            async def simulate_diagnostics():  # type: ignore
                await asyncio.sleep(0.1)  # Small delay
                client._handle_diagnostics({
                    "uri": test_file.resolve().as_uri(),  # Use resolved path
                    "diagnostics": []
                })

            # Start task to simulate diagnostics arriving
            asyncio.create_task(simulate_diagnostics())  # type: ignore

            # Call _ensure_open - should wait for diagnostics
            uri = await client._ensure_open(str(test_file))

            # Verify didOpen was sent
            mock_transport.send_notification.assert_called_once()
            call_args = mock_transport.send_notification.call_args
            assert call_args[0][0] == "textDocument/didOpen"

            # URI should match (using resolved path)
            assert uri == test_file.resolve().as_uri()

    @pytest.mark.asyncio
    async def test_ensure_open_timeout_continues_anyway(self) -> None:
        """Test that _ensure_open continues even if timeout occurs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.py"
            test_file.write_text("def hello(): pass")

            client = LSPClient(
                workspace_path=tmpdir,
                server_command="pyright-langserver",
                server_args=["--stdio"],
                timeout=0.5,  # Short timeout for testing
            )

            # Mock the transport - don't send any diagnostics
            mock_transport = AsyncMock()
            mock_transport.send_notification = AsyncMock()
            client._transport = mock_transport

            # Call _ensure_open - should timeout but continue
            uri = await client._ensure_open(str(test_file))

            # Verify didOpen was sent
            mock_transport.send_notification.assert_called_once()

            # Should still return the URI
            assert uri == test_file.resolve().as_uri()
