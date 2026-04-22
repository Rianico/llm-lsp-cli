"""Integration tests for auto-start daemon functionality.

These tests verify the auto-start behavior of the CLI when invoking LSP commands
without manually starting the daemon first.

Run with:
    uv run pytest tests/test_auto_start_integration.py -v
"""

import asyncio
import shutil
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.daemon import RequestHandler
from llm_lsp_cli.daemon_client import DaemonClient
from llm_lsp_cli.exceptions import (
    DaemonCrashedError,
    DaemonError,
    DaemonStartupError,
    DaemonStartupTimeoutError,
)
from llm_lsp_cli.ipc import UNIXClient, UNIXServer

from .conftest import is_pyright_langserver_installed

runner = CliRunner()
PYRIGHT_AVAILABLE = is_pyright_langserver_installed()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_base_dir() -> Generator[Path, None, None]:
    """Create a short base directory for UNIX socket paths."""
    import uuid

    base_dir = Path("/tmp") / f"llm-auto-{uuid.uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    yield base_dir
    shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace with short path for UNIX socket compatibility."""
    import uuid

    workspace = Path("/tmp") / f"ws-{uuid.uuid4().hex[:6]}"
    workspace.mkdir(parents=True, exist_ok=True)
    # Create a minimal Python file for LSP operations
    (workspace / "test_module.py").write_text(
        """
def add(a: int, b: int) -> int:
    return a + b


class Calculator:
    def multiply(self, x: int, y: int) -> int:
        return x * y
"""
    )
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def mock_socket_path(temp_workspace: Path, temp_base_dir: Path) -> Path:
    """Create a mock socket path that doesn't actually exist."""
    socket_path = ConfigManager.build_socket_path(
        workspace_path=str(temp_workspace),
        language="python",
        base_dir=temp_base_dir,
    )
    # Don't create the socket file - just return the path
    socket_path.unlink(missing_ok=True)
    return socket_path


def make_mock_unix_client(request_return: Any = None, notify_return: Any = None) -> AsyncMock:
    """Create a mock UNIXClient instance."""
    mock_client = AsyncMock()
    if request_return is not None:
        mock_client.request = AsyncMock(return_value=request_return)
    if notify_return is not None:
        mock_client.notify = AsyncMock(return_value=notify_return)
    mock_client.close = AsyncMock()
    return mock_client


# =============================================================================
# Unit Tests for Auto-Start Logic (Fully Mocked)
# =============================================================================


class TestAutoStartLogic:
    """Tests for auto-start logic with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_request_auto_starts_when_daemon_not_running(
        self, mock_socket_path: Path
    ) -> None:
        """DaemonClient.request() triggers auto-start when daemon not running."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
            startup_timeout=10.0,
        )
        client.socket_path = mock_socket_path

        # Mock _ensure_daemon_ready to track if it was called
        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            # Mock UNIXClient at the module level
            mock_client_obj = make_mock_unix_client({"result": "success"})
            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client_obj):
                result = await client.request("ping", {})

                # Verify auto-start was triggered
                mock_ensure.assert_called_once()
                assert result == {"result": "success"}

        await client.close()

    @pytest.mark.asyncio
    async def test_request_reuses_existing_daemon(self, mock_socket_path: Path) -> None:
        """DaemonClient.request() skips start when daemon already running."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        # Mock _ensure_daemon_ready to just return (simulating daemon already running)
        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = None

            mock_client_obj = make_mock_unix_client({"result": "success"})
            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client_obj):
                result = await client.request("ping", {})

                # Auto-start check was called but daemon was already running
                mock_ensure.assert_called_once()
                assert result == {"result": "success"}

        await client.close()

    @pytest.mark.asyncio
    async def test_notify_auto_starts_daemon(self, mock_socket_path: Path) -> None:
        """DaemonClient.notify() triggers auto-start."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            mock_client_obj = make_mock_unix_client()
            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client_obj):
                await client.notify("textDocument/didOpen", {"filePath": "/test.py"})

                mock_ensure.assert_called_once()
                mock_client_obj.notify.assert_called_once()

        await client.close()


# =============================================================================
# Socket Waiting and Backoff Tests
# =============================================================================


class TestSocketWaiting:
    """Tests for socket waiting behavior."""

    @pytest.mark.asyncio
    async def test_wait_for_socket_immediate_success(self, mock_socket_path: Path) -> None:
        """_wait_for_socket returns immediately when socket exists."""
        mock_socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Create socket file
        mock_socket_path.touch()

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
            startup_timeout=10.0,
        )
        client.socket_path = mock_socket_path

        try:
            # Should return quickly
            start = time.perf_counter()
            await client._wait_for_socket()
            elapsed = time.perf_counter() - start

            # Should be very fast (just the 10ms final delay)
            assert elapsed < 0.1
        finally:
            mock_socket_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_wait_for_socket_timeout_raises_error(self, mock_socket_path: Path) -> None:
        """_wait_for_socket raises DaemonStartupTimeoutError when socket never appears."""
        # Ensure socket doesn't exist
        mock_socket_path.unlink(missing_ok=True)

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
            startup_timeout=0.15,  # Short timeout for test
        )
        client.socket_path = mock_socket_path

        with pytest.raises(DaemonStartupTimeoutError) as exc_info:
            await client._wait_for_socket()

        error_msg = str(exc_info.value)
        assert "timed out" in error_msg.lower()
        assert str(mock_socket_path) in error_msg
        assert "workspace=" in error_msg
        assert "language=" in error_msg

    @pytest.mark.asyncio
    async def test_exponential_backoff_pattern(self, mock_socket_path: Path) -> None:
        """Verify exponential backoff follows 50ms, 100ms, 200ms, 400ms pattern."""
        # Ensure socket doesn't exist
        mock_socket_path.unlink(missing_ok=True)

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
            startup_timeout=0.5,
        )
        client.socket_path = mock_socket_path

        # Track sleep calls
        sleep_delays = []
        original_sleep = asyncio.sleep

        async def track_sleep(delay: float) -> None:
            sleep_delays.append(delay)
            await original_sleep(delay)

        with patch("asyncio.sleep", side_effect=track_sleep):
            with pytest.raises(DaemonStartupTimeoutError):
                await client._wait_for_socket()

        # Verify exponential backoff pattern (before hitting the 1s cap)
        # Expected: 0.05, 0.1, 0.2, 0.4 (then timeout at 0.5s)
        assert len(sleep_delays) >= 4
        assert abs(sleep_delays[0] - 0.05) < 0.01  # 50ms initial
        assert abs(sleep_delays[1] - 0.10) < 0.01  # 100ms
        assert abs(sleep_delays[2] - 0.20) < 0.02  # 200ms


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestAutoStartErrorHandling:
    """Tests for auto-start error handling."""

    @pytest.mark.asyncio
    async def test_daemon_startup_failure_wraps_exception(self, mock_socket_path: Path) -> None:
        """DaemonStartupError raised when daemon subprocess spawn fails."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        # Mock _ensure_daemon_ready to raise DaemonStartupError directly
        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.side_effect = DaemonStartupError(
                "Failed to start daemon: Spawn failed",
                workspace="/test/workspace",
                language="python",
            )

            with pytest.raises(DaemonStartupError) as exc_info:
                await client.request("ping", {})

            error_msg = str(exc_info.value)
            assert "Failed to start daemon" in error_msg
            assert "workspace='/test/workspace'" in error_msg
            assert "language='python'" in error_msg

        await client.close()

    @pytest.mark.asyncio
    async def test_daemon_crashed_on_connection_failure(self, mock_socket_path: Path) -> None:
        """DaemonCrashedError raised when socket exists but connection fails."""
        # Create socket file to simulate existing daemon
        mock_socket_path.parent.mkdir(parents=True, exist_ok=True)
        mock_socket_path.touch()

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        # Mock _ensure_daemon_ready to succeed (socket exists)
        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = None

            # Mock UNIXClient to raise FileNotFoundError (simulating crashed daemon)
            mock_client_obj = AsyncMock()
            mock_client_obj.request.side_effect = FileNotFoundError()
            mock_client_obj.close = AsyncMock()

            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client_obj):
                with pytest.raises(DaemonCrashedError) as exc_info:
                    await client.request("ping", {})

            error_msg = str(exc_info.value)
            assert "crashed" in error_msg.lower()
            assert str(mock_socket_path) in error_msg

        await client.close()
        mock_socket_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_connection_timeout_wrapped(self, mock_socket_path: Path) -> None:
        """DaemonError raised when request times out."""
        mock_socket_path.parent.mkdir(parents=True, exist_ok=True)
        mock_socket_path.touch()

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = None

            mock_client_obj = AsyncMock()
            mock_client_obj.request.side_effect = asyncio.TimeoutError()
            mock_client_obj.close = AsyncMock()

            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client_obj):
                with pytest.raises(DaemonError) as exc_info:
                    await client.request("ping", {})

            error_msg = str(exc_info.value)
            assert "timed out" in error_msg.lower()

        await client.close()
        mock_socket_path.unlink(missing_ok=True)


# =============================================================================
# CLI Command Tests
# =============================================================================


class TestCLICommandsAutoStart:
    """Tests for CLI commands with auto-start behavior."""

    def test_version_command_works_without_daemon(self) -> None:
        """Version command works without any daemon."""
        from llm_lsp_cli.cli import app

        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "llm-lsp-cli version" in result.output

    @patch("llm_lsp_cli.daemon.DaemonManager.is_running")
    def test_status_command_reports_not_running(self, mock_is_running: MagicMock) -> None:
        """Status command reports daemon not running."""
        from llm_lsp_cli.cli import app

        # Mock daemon as not running
        mock_is_running.return_value = False

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        # Status shows "not running" when daemon is not running
        assert "not running" in result.output.lower()

    @patch("llm_lsp_cli.daemon_client.DaemonClient")
    def test_definition_command_uses_daemon_client(
        self, mock_daemon_client_class: MagicMock, temp_workspace: Path
    ) -> None:
        """Definition command uses DaemonClient (which handles auto-start)."""
        from llm_lsp_cli.cli import app

        test_file = temp_workspace / "test.py"
        test_file.write_text("def hello(): pass")

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(
            return_value={
                "locations": [
                    {
                        "uri": "test.py",
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 0, "character": 5},
                        },
                    }
                ]
            }
        )
        mock_client.close = AsyncMock()
        mock_daemon_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "definition",
                str(test_file),
                "0",
                "5",
                "--workspace",
                str(temp_workspace),
                "--language",
                "python",
            ],
        )

        # Verify DaemonClient was used (auto-start is internal to DaemonClient)
        mock_daemon_client_class.assert_called_once()
        mock_client.request.assert_called_once()
        assert result.exit_code == 0


# =============================================================================
# Performance Tests
# =============================================================================


class TestAutoStartPerformance:
    """Performance tests for auto-start behavior."""

    @pytest.mark.asyncio
    async def test_socket_wait_fast_path_when_exists(self, mock_socket_path: Path) -> None:
        """Socket wait returns quickly when socket already exists."""
        mock_socket_path.parent.mkdir(parents=True, exist_ok=True)
        mock_socket_path.touch()

        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        try:
            start = time.perf_counter()
            await client._wait_for_socket()
            elapsed = time.perf_counter() - start

            # Should be under 50ms (just the 10ms final delay)
            assert elapsed < 0.05
        finally:
            mock_socket_path.unlink(missing_ok=True)
            await client.close()

    @pytest.mark.asyncio
    async def test_multiple_requests_no_additional_startup(self, mock_socket_path: Path) -> None:
        """Multiple requests don't trigger multiple daemon starts."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = None  # Daemon already running

            # Make multiple requests
            for i in range(5):
                mock_client_obj = make_mock_unix_client({"result": i})
                with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client_obj):
                    await client.request("ping", {})

            # _ensure_daemon_ready called for each request (it checks is_running internally)
            assert mock_ensure.call_count == 5

        await client.close()


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestAutoStartEdgeCases:
    """Edge case tests for auto-start behavior."""

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, mock_socket_path: Path) -> None:
        """Multiple close() calls are safe."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        # Multiple closes should not raise
        await client.close()
        await client.close()
        await client.close()

        # Should still be safe to use
        assert client._client is None

    @pytest.mark.asyncio
    async def test_request_after_close(self, mock_socket_path: Path) -> None:
        """New request after explicit close works correctly."""
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
        )
        client.socket_path = mock_socket_path

        with patch.object(client, "_ensure_daemon_ready", new_callable=AsyncMock) as mock_ensure:
            # First request
            mock_client1 = make_mock_unix_client({"result": "first"})
            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client1):
                result1 = await client.request("ping", {})
                assert result1 == {"result": "first"}

            # Explicit close
            await client.close()
            assert client._client is None

            # Second request after close
            mock_client2 = make_mock_unix_client({"result": "second"})
            with patch("llm_lsp_cli.daemon_client.UNIXClient", return_value=mock_client2):
                result2 = await client.request("ping", {})
                assert result2 == {"result": "second"}

            # Auto-start was called for both requests
            assert mock_ensure.call_count == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_different_workspaces_different_sockets(self, temp_base_dir: Path) -> None:
        """Different workspaces produce different socket paths."""
        import uuid

        workspace_a = Path("/tmp") / f"ws-a-{uuid.uuid4().hex[:6]}"
        workspace_b = Path("/tmp") / f"ws-b-{uuid.uuid4().hex[:6]}"

        try:
            workspace_a.mkdir(parents=True, exist_ok=True)
            workspace_b.mkdir(parents=True, exist_ok=True)

            # With flat structure, each workspace has its own .llm-lsp-cli directory
            # Don't override base_dir - let each workspace use its own
            socket_a = ConfigManager.build_socket_path(
                workspace_path=str(workspace_a),
                language="python",
            )
            socket_b = ConfigManager.build_socket_path(
                workspace_path=str(workspace_b),
                language="python",
            )

            assert socket_a != socket_b
            # Each workspace should have its own .llm-lsp-cli directory
            assert str(workspace_a) in str(socket_a)
            assert str(workspace_b) in str(socket_b)
        finally:
            shutil.rmtree(workspace_a, ignore_errors=True)
            shutil.rmtree(workspace_b, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_different_languages_different_sockets(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Different languages produce different socket paths for same workspace."""
        python_socket = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="python",
            base_dir=temp_base_dir,
        )
        typescript_socket = ConfigManager.build_socket_path(
            workspace_path=str(temp_workspace),
            language="typescript",
            base_dir=temp_base_dir,
        )

        assert python_socket != typescript_socket


# =============================================================================
# Configuration Tests
# =============================================================================


class TestAutoStartConfiguration:
    """Tests for auto-start configuration options."""

    @pytest.mark.asyncio
    async def test_custom_startup_timeout(self, mock_socket_path: Path) -> None:
        """Custom startup_timeout is stored correctly."""
        custom_timeout = 5.0
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
            startup_timeout=custom_timeout,
        )
        client.socket_path = mock_socket_path

        assert client.startup_timeout == custom_timeout

        await client.close()

    @pytest.mark.asyncio
    async def test_custom_connection_timeout(self, mock_socket_path: Path) -> None:
        """Custom connection_timeout is stored correctly."""
        custom_timeout = 15.0
        client = DaemonClient(
            workspace_path="/test/workspace",
            language="python",
            connection_timeout=custom_timeout,
        )
        client.socket_path = mock_socket_path

        assert client.connection_timeout == custom_timeout

        await client.close()


# =============================================================================
# Real Server Integration (Optional - requires working LSP)
# =============================================================================


@pytest.mark.skipif(
    not PYRIGHT_AVAILABLE,
    reason="Requires pyright-langserver to be installed",
)
class TestRealServerIntegration:
    """Integration tests with real LSP server (skipped if pyright not available)."""

    @pytest.mark.asyncio
    async def test_ipc_server_responds_to_ping(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Real IPC server responds to ping requests."""
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

        async def request_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        # Run client request while server is running
        async def run_client() -> dict[str, Any]:
            client = UNIXClient(str(socket_path))
            try:
                result = await client.request("ping", {})
                return result
            finally:
                await client.close()

        try:
            # Give server time to start
            await asyncio.sleep(0.1)

            # Run client request
            result = await asyncio.wait_for(run_client(), timeout=5.0)
            assert result == {"status": "pong"}
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_ipc_server_status_response(
        self, temp_workspace: Path, temp_base_dir: Path
    ) -> None:
        """Real IPC server returns status information."""
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

        async def request_handler(method: str, params: dict[str, Any]) -> dict[str, Any]:
            return await handler.handle(method, params)

        server = UNIXServer(str(socket_path), request_handler)
        await server.start()

        async def run_client() -> dict[str, Any]:
            client = UNIXClient(str(socket_path))
            try:
                result = await client.request("status", {})
                return result
            finally:
                await client.close()

        try:
            await asyncio.sleep(0.1)

            result = await asyncio.wait_for(run_client(), timeout=5.0)
            assert result["running"] is True
            assert result["workspace"] == str(temp_workspace)
            assert result["language"] == "python"
            assert "socket" in result
            assert "pid" in result
        finally:
            await server.stop()
