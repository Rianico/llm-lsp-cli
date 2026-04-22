"""End-to-End tests for daemon lifecycle and LSP features.
Run with:
    uv run pytest tests/test_e2e_daemon_lifecycle.py
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.config.manager import ConfigManager
from llm_lsp_cli.daemon import RequestHandler
from llm_lsp_cli.ipc.unix_client import UNIXClient
from llm_lsp_cli.ipc.unix_server import UNIXServer

from .conftest import is_pyright_langserver_installed

# Check if pyright-langserver is available for tests
# Note: Even when installed, integration tests may fail due to LSP communication issues
PYRIGHT_AVAILABLE = is_pyright_langserver_installed()

# Tests requiring working pyright-langserver integration
# Currently skipped - pyright is installed but LSP requests timeout
REQUIRES_WORKING_PYRIGHT = pytest.mark.skip(
    reason="Requires functional pyright-langserver integration - LSP requests currently timeout"
)


class TestE2EIPCCommunication:
    """End-to-end tests for IPC communication."""

    @pytest.fixture
    def temp_base_dir(self):  # type: ignore
        """Create a short base directory for UNIX socket paths."""
        import uuid

        base_dir = Path("/tmp") / f"llm-{uuid.uuid4().hex[:6]}"
        base_dir.mkdir(parents=True, exist_ok=True)
        yield base_dir
        import shutil

        shutil.rmtree(base_dir, ignore_errors=True)

    @pytest.fixture
    def temp_workspace(self):  # type: ignore
        """Create a temporary workspace with short path for UNIX socket compatibility.

        UNIX socket paths are limited to 108 characters on macOS/Linux.
        Using /tmp directly ensures we stay within this limit.
        """
        import uuid

        workspace = Path("/tmp") / f"ws-{uuid.uuid4().hex[:6]}"
        workspace.mkdir(parents=True, exist_ok=True)
        yield workspace
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_client_server_communication(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Test UNIX client can communicate with server."""
        # Build socket path with short base directory
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )

        # Ensure parent directory exists
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Create handler
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            # Connect client
            client = UNIXClient(str(socket_path))

            # Test ping
            result = await client.request("ping", {})
            assert result == {"status": "pong"}

            # Test status
            result = await client.request("status", {})
            assert result["running"] is True
            assert "socket" in result
            assert result["workspace"] == str(temp_workspace)
            assert result["language"] == "python"

            # Close client
            await client.close()

        finally:
            # Stop server
            await server.stop()

    @pytest.mark.asyncio
    async def test_lsp_feature_request_flow(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Test LSP feature requests through IPC."""
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            client = UNIXClient(str(socket_path))

            # Create test file first
            test_file = temp_workspace / "test.py"
            test_file.write_text("def hello(): pass")

            # Test definition request
            result = await client.request(
                "textDocument/definition",
                {
                    "workspacePath": str(temp_workspace),
                    "filePath": str(test_file),
                    "line": 0,
                    "column": 5,
                },
            )
            # Should return locations (might be empty)
            assert "locations" in result

            # Test references request
            result = await client.request(
                "textDocument/references",
                {
                    "workspacePath": str(temp_workspace),
                    "filePath": str(test_file),
                    "line": 0,
                    "column": 5,
                },
            )
            assert "locations" in result

            # Test hover request
            result = await client.request(
                "textDocument/hover",
                {
                    "workspacePath": str(temp_workspace),
                    "filePath": str(test_file),
                    "line": 0,
                    "column": 5,
                },
            )
            # Hover returns dict (might be empty if no info)
            assert isinstance(result, dict)

            await client.close()

        finally:
            await server.stop()


class TestE2EWorkspaceIsolation:
    """End-to-end tests for workspace isolation."""

    @pytest.fixture
    def temp_workspaces(self):  # type: ignore
        """Create multiple temporary workspaces with short paths."""
        import uuid

        base = Path("/tmp") / f"llm-lsp-test-{uuid.uuid4().hex[:8]}"
        base.mkdir(parents=True, exist_ok=True)

        workspace_a = base / "project_a"
        workspace_b = base / "project_b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        # Create different files in each workspace
        (workspace_a / "module_a.py").write_text("def func_a(): pass")
        (workspace_b / "module_b.py").write_text("def func_b(): pass")

        yield workspace_a, workspace_b

        # Cleanup
        import shutil

        shutil.rmtree(base, ignore_errors=True)

    def test_different_workspaces_different_sockets(self, temp_workspaces) -> None:  # type: ignore
        """Test different workspaces get different socket paths."""
        workspace_a, workspace_b = temp_workspaces

        socket_a = ConfigManager.build_socket_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        socket_b = ConfigManager.build_socket_path(
            workspace_path=str(workspace_b),
            language="python",
        )

        assert socket_a != socket_b

    def test_same_workspace_same_socket(self, temp_workspaces) -> None:  # type: ignore
        """Test same workspace gets same socket path."""
        workspace_a, _ = temp_workspaces

        socket1 = ConfigManager.build_socket_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        socket2 = ConfigManager.build_socket_path(
            workspace_path=str(workspace_a),
            language="python",
        )

        assert socket1 == socket2

    def test_different_languages_different_sockets(self, temp_workspaces) -> None:  # type: ignore
        """Test same workspace with different languages produces different paths."""
        workspace_a, _ = temp_workspaces

        python_socket = ConfigManager.build_socket_path(
            workspace_path=str(workspace_a),
            language="python",
        )
        typescript_socket = ConfigManager.build_socket_path(
            workspace_path=str(workspace_a),
            language="typescript",
        )

        assert python_socket != typescript_socket

    @pytest.mark.asyncio
    async def test_request_handler_uses_correct_workspace(self, temp_workspaces) -> None:  # type: ignore
        """Test request handler uses correct workspace path."""
        workspace_a, workspace_b = temp_workspaces

        handler_a = RequestHandler(
            workspace_path=str(workspace_a),
            language="python",
        )
        handler_b = RequestHandler(
            workspace_path=str(workspace_b),
            language="python",
        )

        # Verify handlers have different workspace paths
        assert handler_a._workspace_path == str(workspace_a)
        assert handler_b._workspace_path == str(workspace_b)

        # Verify status includes correct workspace info
        status_a = await handler_a.handle("status", {})
        status_b = await handler_b.handle("status", {})

        assert status_a["workspace"] == str(workspace_a)
        assert status_b["workspace"] == str(workspace_b)


class TestE2EConfigManagement:
    """End-to-end tests for configuration management."""

    @pytest.fixture
    def temp_config_dir(self):  # type: ignore
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            yield config_dir

    @patch("llm_lsp_cli.config.manager.ConfigManager._get_xdg_paths")
    def test_config_init_creates_file(
        self, mock_get_paths: MagicMock, temp_config_dir: Path
    ) -> None:
        """Test config init creates configuration file."""
        import yaml

        config_file = temp_config_dir / "config.yaml"

        mock_paths = MagicMock()
        mock_paths.config_dir = temp_config_dir
        mock_get_paths.return_value = mock_paths

        result = ConfigManager.init_config()
        assert result is True
        assert config_file.exists()

        # Verify content has expected structure
        data = yaml.safe_load(config_file.read_text())
        assert "languages" in data
        assert "python" in data["languages"]

    @patch("llm_lsp_cli.config.manager.ConfigManager._get_xdg_paths")
    def test_config_load_after_init(self, mock_get_paths: MagicMock, temp_config_dir: Path) -> None:
        """Test config loads after initialization."""
        mock_paths = MagicMock()
        mock_paths.config_dir = temp_config_dir
        mock_get_paths.return_value = mock_paths

        # Initialize
        ConfigManager.init_config()

        # Load
        config = ConfigManager.load()
        assert config is not None
        assert "languages" in config.model_dump()

    @patch("llm_lsp_cli.config.manager.ConfigManager._get_xdg_paths")
    def test_config_init_returns_false_if_exists(
        self, mock_get_paths: MagicMock, temp_config_dir: Path
    ) -> None:
        """Test config init returns False if config exists."""
        config_file = temp_config_dir / "config.yaml"
        config_file.write_text("{}")

        mock_paths = MagicMock()
        mock_paths.config_dir = temp_config_dir
        mock_get_paths.return_value = mock_paths

        result = ConfigManager.init_config()
        assert result is False


class TestE2EErrorHandling:
    """End-to-end tests for error handling."""

    @pytest.fixture
    def temp_base_dir(self):  # type: ignore
        """Create a short base directory for UNIX socket paths."""
        import uuid

        base_dir = Path("/tmp") / f"llm-err-{uuid.uuid4().hex[:6]}"
        base_dir.mkdir(parents=True, exist_ok=True)
        yield base_dir
        import shutil

        shutil.rmtree(base_dir, ignore_errors=True)

    @pytest.fixture
    def temp_workspace(self):  # type: ignore
        """Create a temporary workspace with short path for UNIX socket compatibility."""
        import uuid

        workspace = Path("/tmp") / f"ws-{uuid.uuid4().hex[:6]}"
        workspace.mkdir(parents=True, exist_ok=True)
        yield workspace
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_unknown_method_error(self, temp_workspace: Path, temp_base_dir: Path) -> None:
        """Test unknown method returns error."""
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            client = UNIXClient(str(socket_path))

            # Unknown method should raise error
            from llm_lsp_cli.ipc.unix_client import RPCError

            with pytest.raises(RPCError):
                await client.request("unknown_method_xyz", {})

            await client.close()

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_missing_filepath_error(self, temp_workspace: Path, temp_base_dir: Path) -> None:
        """Test missing filePath returns error."""
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            client = UNIXClient(str(socket_path))

            # Missing required params should raise error
            from llm_lsp_cli.ipc.unix_client import RPCError

            with pytest.raises(RPCError):
                await client.request(
                    "textDocument/definition",
                    {
                        "workspacePath": str(temp_workspace),
                        # Missing filePath, line, column
                    },
                )

            await client.close()

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_shutdown_request(self, temp_workspace: Path, temp_base_dir: Path) -> None:
        """Test shutdown request."""
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            client = UNIXClient(str(socket_path))

            # Shutdown request
            result = await client.request("shutdown", {})
            assert result == {"status": "shutting_down"}

            await client.close()

        finally:
            await server.stop()


class TestE2EConcurrentRequests:
    """End-to-end tests for concurrent request handling."""

    @pytest.fixture
    def temp_base_dir(self):  # type: ignore
        """Create a short base directory for UNIX socket paths."""
        import uuid

        base_dir = Path("/tmp") / f"llm-conc-{uuid.uuid4().hex[:6]}"
        base_dir.mkdir(parents=True, exist_ok=True)
        yield base_dir
        import shutil

        shutil.rmtree(base_dir, ignore_errors=True)

    @pytest.fixture
    def temp_workspace(self):  # type: ignore
        """Create a temporary workspace with short path for UNIX socket compatibility."""
        import uuid

        workspace = Path("/tmp") / f"ws-{uuid.uuid4().hex[:6]}"
        workspace.mkdir(parents=True, exist_ok=True)
        yield workspace
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_concurrent_ping_requests(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Test multiple concurrent ping requests."""
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            client = UNIXClient(str(socket_path))

            # Send multiple concurrent ping requests
            tasks = [client.request("ping", {}) for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # All should succeed
            for result in results:
                assert result == {"status": "pong"}

            await client.close()

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_mixed_concurrent_requests(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Test multiple concurrent different requests."""
        socket_path = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        async def request_handler(method: str, params: dict[str, Any]):  # type: ignore
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        try:
            client = UNIXClient(str(socket_path))

            # Create test file first
            test_file = temp_workspace / "test.py"
            test_file.write_text("def hello(): pass")

            # Send mixed concurrent requests
            tasks = [
                client.request("ping", {}),
                client.request("status", {}),
                client.request(
                    "textDocument/definition",
                    {
                        "workspacePath": str(temp_workspace),
                        "filePath": str(test_file),
                        "line": 0,
                        "column": 5,
                    },
                ),
                client.request(
                    "textDocument/references",
                    {
                        "workspacePath": str(temp_workspace),
                        "filePath": str(test_file),
                        "line": 0,
                        "column": 5,
                    },
                ),
            ]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert results[0] == {"status": "pong"}
            assert results[1]["running"] is True
            assert "locations" in results[2]
            assert "locations" in results[3]

            await client.close()

        finally:
            await server.stop()


class TestE2ERequestHandlerFeatures:
    """End-to-end tests for RequestHandler feature methods."""

    @pytest.fixture
    def temp_workspace(self):  # type: ignore
        """Create a temporary workspace with short path for UNIX socket compatibility."""
        import uuid

        workspace = Path("/tmp") / f"llm-lsp-feat-{uuid.uuid4().hex[:8]}"
        workspace.mkdir(parents=True, exist_ok=True)
        yield workspace
        # Cleanup
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_ping(self, temp_workspace: Path) -> None:
        """Test ping request."""
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )
        result = await handler.handle("ping", {})
        assert result == {"status": "pong"}

    @pytest.mark.asyncio
    async def test_status(self, temp_workspace: Path) -> None:
        """Test status request."""
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )
        result = await handler.handle("status", {})
        assert result["running"] is True
        assert result["workspace"] == str(temp_workspace)
        assert result["language"] == "python"
        assert "socket" in result
        assert "pid" in result

    @pytest.mark.asyncio
    async def test_shutdown(self, temp_workspace: Path) -> None:
        """Test shutdown request."""
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )
        result = await handler.handle("shutdown", {})
        assert result == {"status": "shutting_down"}

    @pytest.mark.asyncio
    async def test_document_symbol(self, temp_workspace: Path) -> None:
        """Test document symbol request."""
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Create a test file
        test_file = temp_workspace / "test.py"
        test_file.write_text("def foo(): pass")

        result = await handler.handle(
            "textDocument/documentSymbol",
            {
                "workspacePath": str(temp_workspace),
                "filePath": str(test_file),
            },
        )
        assert "symbols" in result

    @pytest.mark.asyncio
    async def test_workspace_symbol(self, temp_workspace: Path) -> None:
        """Test workspace symbol request.

        Note: workspace/symbol may not be supported by all LSP servers.
        This test verifies the request is handled gracefully.
        """
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Create a test file with some symbols
        test_file = temp_workspace / "test.py"
        test_file.write_text("""
class MyClass:
    def my_method(self):
        pass

def my_function():
    pass
""")

        try:
            result = await handler.handle(
                "workspace/symbol",
                {
                    "workspacePath": str(temp_workspace),
                    "query": "my",
                },
            )
            # If successful, should return symbols list
            assert "symbols" in result
        except Exception as e:
            # workspace/symbol is not supported by all servers
            # The error should be an LSP error, not a crash
            assert "symbol" in str(e).lower() or "method" in str(e).lower()

    @pytest.mark.asyncio
    async def test_completion(self, temp_workspace: Path) -> None:
        """Test completion request."""
        handler = RequestHandler(
            workspace_path=str(temp_workspace),
            language="python",
        )

        # Create a test file first
        test_file = temp_workspace / "test.py"
        test_file.write_text("def hello(): pass\n")

        result = await handler.handle(
            "textDocument/completion",
            {
                "workspacePath": str(temp_workspace),
                "filePath": str(test_file),
                "line": 0,
                "column": 5,
            },
        )
        assert "items" in result
