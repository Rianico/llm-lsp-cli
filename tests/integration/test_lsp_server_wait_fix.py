"""Integration tests for LSP server wait fix.

This module tests the full initialization chain from daemon client to LSP transport.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.daemon_client import DaemonClient
from llm_lsp_cli.exceptions import DaemonError
from llm_lsp_cli.lsp.transport import StdioTransport
from llm_lsp_cli.server.workspace import WorkspaceManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_workspace(temp_dir: Path) -> Path:
    """Create a temporary workspace directory."""
    workspace = temp_dir / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def temp_python_file(temp_workspace: Path) -> Path:
    """Create a sample Python file in the workspace."""
    content = """
class MyClass:
    def my_method(self):
        pass
"""
    file_path = temp_workspace / "sample.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def mock_lsp_server_script(temp_dir: Path) -> Path:
    """Create a script that simulates a slow-starting LSP server."""
    script = temp_dir / "slow_lsp.py"
    script.write_text("""
import asyncio
import sys
import json

async def main():
    # Simulate slow startup
    await asyncio.sleep(0.5)

    # Read Content-Length from stdin
    while True:
        line = await sys.stdin.readline()
        if not line:
            break
        if line.strip() == "":
            break

    # Send a minimal initialize response
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "capabilities": {
                "textDocumentSync": 1,
                "documentSymbolProvider": True
            }
        }
    }
    body = json.dumps(response)
    print(f"Content-Length: {len(body)}\\r\\n\\r\\n{body}", flush=True)

    # Keep running to handle shutdown
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
""")
    return script


# =============================================================================
# Integration Tests: Full Initialization Chain
# =============================================================================


class TestLSPServerWaitIntegration:
    """Integration tests for the LSP server wait fix."""

    @pytest.mark.asyncio
    async def test_workspace_manager_with_mock_transport(self, temp_workspace: Path):
        """Happy path: WorkspaceManager waits for LSP initialization successfully."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            # Setup mock LSP client that succeeds after a delay
            mock_client = AsyncMock()

            async def delayed_initialize():
                await asyncio.sleep(0.1)  # Simulate 100ms delay
                return {"capabilities": {}}

            mock_client.initialize = delayed_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(temp_workspace),
                server_command="pyright-langserver",
                timeout=5.0,
            )

            # Should succeed and return the mock client
            client = await manager.ensure_initialized()
            assert client is mock_client
            assert manager.is_initialized is True

    @pytest.mark.asyncio
    async def test_workspace_manager_timeout_integration(self, temp_workspace: Path):
        """Integration test: Timeout properly enforced when LSP hangs."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            # Setup mock LSP client that hangs
            mock_client = AsyncMock()

            async def hanging_initialize():
                await asyncio.Event().wait()  # Never completes

            mock_client.initialize = hanging_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(temp_workspace),
                server_command="pyright-langserver",
                timeout=0.2,  # Short timeout for test
            )

            # Should raise TimeoutError
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    manager.ensure_initialized(),
                    timeout=1.0,  # Outer timeout to prevent test hang
                )

    @pytest.mark.asyncio
    async def test_transport_startup_success(self):
        """Integration test: Transport starts successfully with valid command."""
        with (
            patch("asyncio.create_subprocess_exec") as mock_exec,
            patch("asyncio.create_task"),
        ):
            # Mock successful process
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="valid-command")
            await transport.start()

            assert transport._process is mock_process
            assert transport._running is True

    @pytest.mark.asyncio
    async def test_transport_startup_command_not_found(self):
        """Integration test: Transport handles command not found error."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("Command not found")

            transport = StdioTransport(command="nonexistent-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            assert "command not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_transport_startup_permission_denied(self):
        """Integration test: Transport handles permission denied error."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = PermissionError("Permission denied")

            transport = StdioTransport(command="restricted-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            assert "permission denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_transport_startup_process_crash(self):
        """Integration test: Transport detects immediate process crash."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Mock process that crashes immediately
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.stderr = AsyncMock()
            mock_process.stderr.read = AsyncMock(return_value=b"Error: invalid configuration\n")
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="crashing-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            assert "invalid configuration" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("llm_lsp_cli.daemon_client.ConfigManager")
    @patch("llm_lsp_cli.daemon_client.DaemonManager")
    @patch("llm_lsp_cli.daemon_client.UNIXClient")
    async def test_daemon_client_request_with_timeout(
        self,
        mock_unix_client: MagicMock,
        mock_daemon_manager: MagicMock,
        mock_config_manager: MagicMock,
    ):
        """Integration test: DaemonClient request timeout includes context."""
        # Setup mock socket path
        mock_socket = MagicMock(spec=Path)
        mock_socket.exists.return_value = True
        mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
        mock_config_manager.build_socket_path.return_value = mock_socket

        # Setup daemon manager
        mock_manager_instance = MagicMock()
        mock_manager_instance.is_running.return_value = True
        mock_daemon_manager.return_value = mock_manager_instance

        # Mock UNIXClient to raise TimeoutError
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = asyncio.TimeoutError()
        mock_client_instance.close = AsyncMock()
        mock_unix_client.return_value = mock_client_instance

        client = DaemonClient("/workspace", "python", connection_timeout=30.0)

        # Should raise DaemonError with enhanced message
        with pytest.raises(DaemonError) as exc_info:
            await client.request("textDocument/definition", {"filePath": "/test.py"})

        # Verify enhanced error message includes LSP initialization context
        error_msg = str(exc_info.value)
        assert "LSP initialization" in error_msg or "timed out" in error_msg.lower()
        assert "/workspace" in error_msg
        assert "python" in error_msg


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestLSPEdgeCases:
    """Edge case tests for LSP server wait scenarios."""

    @pytest.mark.asyncio
    async def test_workspace_manager_reentrant_call(self, temp_workspace: Path):
        """Test: ensure_initialized() is idempotent after first call."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={"capabilities": {}})
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(temp_workspace),
                server_command="pyright-langserver",
                timeout=5.0,
            )

            # First call - initializes
            client1 = await manager.ensure_initialized()
            assert manager.is_initialized is True

            # Second call - should return same client without re-initializing
            client2 = await manager.ensure_initialized()
            assert client1 is client2
            assert mock_client.initialize.call_count == 1

    @pytest.mark.asyncio
    async def test_transport_stabilization_delay(self):
        """Test: Transport includes stabilization delay after process start."""
        with (
            patch("asyncio.create_subprocess_exec") as mock_exec,
            patch("asyncio.create_task"),
            patch("asyncio.sleep") as mock_sleep,
        ):
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="valid-command")
            await transport.start()

            # Verify stabilization delay was called
            assert mock_sleep.called
            # Check for 50ms delay
            mock_sleep.assert_called_with(0.05)

    @pytest.mark.asyncio
    async def test_workspace_manager_concurrent_calls(self, temp_workspace: Path):
        """Test: Concurrent calls to ensure_initialized() use lock."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = AsyncMock()
            initialize_call_count = 0

            async def track_initialize():
                nonlocal initialize_call_count
                initialize_call_count += 1
                await asyncio.sleep(0.1)
                return {"capabilities": {}}

            mock_client.initialize = track_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(temp_workspace),
                server_command="pyright-langserver",
                timeout=5.0,
            )

            # Fire off multiple concurrent calls
            tasks = [manager.ensure_initialized() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # All results should be the same client
            assert all(r is results[0] for r in results)
            # Initialize should only be called once due to lock
            assert initialize_call_count == 1

    @pytest.mark.asyncio
    async def test_transport_stderr_captured_on_crash(self):
        """Test: Stderr output captured when process crashes."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.stderr = AsyncMock()
            mock_process.stderr.read = AsyncMock(
                return_value=b"Specific error: missing config file\n"
            )
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="failing-command")

            with pytest.raises(RuntimeError) as exc_info:
                await transport.start()

            # Verify stderr was captured
            mock_process.stderr.read.assert_called_once()
            # Verify stderr content in error message
            error_msg = str(exc_info.value)
            assert "missing config file" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_daemon_client_socket_wait_success(self, temp_workspace: Path):
        """Test: DaemonClient waits for socket with exponential backoff."""
        with (
            patch("llm_lsp_cli.daemon_client.ConfigManager") as mock_config,
            patch("llm_lsp_cli.daemon_client.DaemonManager") as mock_manager,
            patch("llm_lsp_cli.daemon_client.UNIXClient") as mock_client,
            patch("llm_lsp_cli.daemon_client.asyncio.sleep") as mock_sleep,
        ):
            # Socket appears after 2 checks
            call_count = [0]
            mock_socket = MagicMock(spec=Path)

            def socket_exists():
                call_count[0] += 1
                return call_count[0] > 2

            mock_socket.exists.side_effect = socket_exists
            mock_socket.__str__ = MagicMock(return_value="/tmp/test.sock")
            mock_config.build_socket_path.return_value = mock_socket

            mock_manager_instance = MagicMock()
            mock_manager_instance.is_running.return_value = True
            mock_manager.return_value = mock_manager_instance

            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value={"result": "ok"})
            mock_client_instance.close = AsyncMock()
            mock_client.return_value = mock_client_instance

            client = DaemonClient(str(temp_workspace), "python")
            await client.request("textDocument/definition", {"filePath": "/test.py"})

            # Verify exponential backoff: 0.05, 0.1, then 0.01 final delay
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert 0.05 in delays
            assert 0.1 in delays
            assert 0.01 in delays  # Final delay after socket found


# =============================================================================
# Performance Tests
# =============================================================================


class TestLSPInitializationPerformance:
    """Performance tests for LSP initialization timing."""

    @pytest.mark.asyncio
    async def test_workspace_initialization_time(self, temp_workspace: Path):
        """Test: LSP initialization completes within expected time."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={"capabilities": {}})
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(temp_workspace),
                server_command="pyright-langserver",
                timeout=5.0,
            )

            import time

            start = time.monotonic()
            await manager.ensure_initialized()
            elapsed = time.monotonic() - start

            # Should complete in well under timeout
            assert elapsed < 1.0, f"Initialization took {elapsed}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_transport_startup_time(self):
        """Test: Transport starts within expected time."""
        with (
            patch("asyncio.create_subprocess_exec") as mock_exec,
            patch("asyncio.create_task"),
        ):
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdin = MagicMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_exec.return_value = mock_process

            transport = StdioTransport(command="valid-command")

            import time

            start = time.monotonic()
            await transport.start()
            elapsed = time.monotonic() - start

            # Should include 50ms stabilization delay
            assert elapsed >= 0.04, "Transport startup too fast (missing stabilization delay)"
            assert elapsed < 1.0, f"Transport startup took {elapsed}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_timeout_error_timing(self, temp_workspace: Path):
        """Test: Timeout error raised close to configured timeout value."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = AsyncMock()

            async def hanging_initialize():
                await asyncio.Event().wait()

            mock_client.initialize = hanging_initialize
            mock_lsp_class.return_value = mock_client

            timeout_value = 0.3
            manager = WorkspaceManager(
                workspace_path=str(temp_workspace),
                server_command="pyright-langserver",
                timeout=timeout_value,
            )

            import time

            start = time.monotonic()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    manager.ensure_initialized(),
                    timeout=1.0,
                )
            elapsed = time.monotonic() - start

            # Timeout should fire close to configured value (with some tolerance)
            assert abs(elapsed - timeout_value) < 0.15, (
                f"Timeout fired at {elapsed}s, expected ~{timeout_value}s"
            )
