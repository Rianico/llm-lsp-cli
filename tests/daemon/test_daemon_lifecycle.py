"""Unit tests for daemon LSP lifecycle shutdown behavior.

These tests verify that the daemon properly shuts down LSP servers
before stopping the socket server.

Bug Reference: daemon stop leaves LSP server processes orphaned
Root Cause: run_daemon() never calls ServerRegistry.shutdown_all() during shutdown
Fix Location: src/llm_lsp_cli/daemon.py, function run_daemon(), finally block
"""

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.daemon import RequestHandler, run_daemon


@pytest.fixture
def temp_socket_path(tmp_path: Path) -> Path:
    """Create a temporary socket path."""
    return tmp_path / "test.sock"


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock ServerRegistry with async shutdown_all."""
    registry = MagicMock()
    registry.shutdown_all = AsyncMock()
    registry._workspaces: dict[str, MagicMock] = {}
    return registry


@pytest.fixture
def mock_unix_server() -> MagicMock:
    """Create a mock UNIXServer."""
    server = MagicMock()
    server.start = AsyncMock()
    server.stop = AsyncMock()
    return server


@pytest.fixture
def mock_handler(mock_registry: MagicMock) -> MagicMock:
    """Create a mock RequestHandler with mock registry."""
    handler = MagicMock(spec=RequestHandler)
    handler._registry = mock_registry
    handler.handle = AsyncMock()
    # Wire shutdown_servers to call registry's shutdown_all
    handler.shutdown_servers = mock_registry.shutdown_all
    return handler


class TestShutdownAllCalled:
    """TS1: Verify shutdown_all is called during daemon shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_all_called_on_daemon_stop(
        self,
        temp_socket_path: Path,
        tmp_path: Path,
        mock_registry: MagicMock,
        mock_unix_server: MagicMock,
        mock_handler: MagicMock,
    ) -> None:
        """Verify ServerRegistry.shutdown_all() is invoked when daemon shuts down."""
        workspace_path = str(tmp_path / "workspace")
        workspace_path_obj = Path(workspace_path)
        workspace_path_obj.mkdir(parents=True, exist_ok=True)

        with (
            patch("llm_lsp_cli.daemon.RequestHandler", return_value=mock_handler),
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_unix_server),
        ):
            # Start daemon task
            daemon_task = asyncio.create_task(
                run_daemon(
                    socket_path=str(temp_socket_path),
                    workspace_path=workspace_path,
                    language="python",
                )
            )

            # Wait a bit for daemon to start
            await asyncio.sleep(0.1)

            # Trigger shutdown by cancelling the task (simulates signal)
            daemon_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await daemon_task

            # Verify shutdown_all was called
            mock_registry.shutdown_all.assert_awaited_once()
            # Verify server.stop was also called
            mock_unix_server.stop.assert_awaited_once()


class TestShutdownOrderEnforcement:
    """TS2: Verify LSP servers shutdown BEFORE UNIX socket server stops."""

    @pytest.mark.asyncio
    async def test_shutdown_all_called_before_server_stop(
        self,
        temp_socket_path: Path,
        tmp_path: Path,
        mock_registry: MagicMock,
        mock_unix_server: MagicMock,
        mock_handler: MagicMock,
    ) -> None:
        """Verify LSP servers shutdown BEFORE socket server stops."""
        workspace_path = str(tmp_path / "workspace")
        workspace_path_obj = Path(workspace_path)
        workspace_path_obj.mkdir(parents=True, exist_ok=True)

        # Track call order
        call_order: list[str] = []

        async def track_shutdown_all() -> None:
            call_order.append("shutdown_all")

        async def track_stop() -> None:
            call_order.append("server.stop")

        mock_registry.shutdown_all.side_effect = track_shutdown_all
        mock_unix_server.stop.side_effect = track_stop

        with (
            patch("llm_lsp_cli.daemon.RequestHandler", return_value=mock_handler),
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_unix_server),
        ):
            # Start daemon task
            daemon_task = asyncio.create_task(
                run_daemon(
                    socket_path=str(temp_socket_path),
                    workspace_path=workspace_path,
                    language="python",
                )
            )

            # Wait a bit for daemon to start
            await asyncio.sleep(0.1)

            # Trigger shutdown
            daemon_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await daemon_task

            # Verify call order: shutdown_all must come before server.stop
            assert "shutdown_all" in call_order, "shutdown_all should have been called"
            assert "server.stop" in call_order, "server.stop should have been called"
            assert call_order.index("shutdown_all") < call_order.index(
                "server.stop"
            ), "shutdown_all must be called before server.stop"


class TestShutdownAllErrorsDoNotPreventCleanup:
    """TS3: Verify daemon cleanup is resilient to LSP shutdown failures."""

    @pytest.mark.asyncio
    async def test_shutdown_all_error_does_not_prevent_server_stop(
        self,
        temp_socket_path: Path,
        tmp_path: Path,
        mock_registry: MagicMock,
        mock_unix_server: MagicMock,
        mock_handler: MagicMock,
    ) -> None:
        """Verify socket cleanup happens even if shutdown_all raises an exception."""
        workspace_path = str(tmp_path / "workspace")
        workspace_path_obj = Path(workspace_path)
        workspace_path_obj.mkdir(parents=True, exist_ok=True)

        # Make shutdown_all raise an exception
        mock_registry.shutdown_all.side_effect = Exception("LSP shutdown failed")

        with (
            patch("llm_lsp_cli.daemon.RequestHandler", return_value=mock_handler),
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_unix_server),
        ):
            # Start daemon task
            daemon_task = asyncio.create_task(
                run_daemon(
                    socket_path=str(temp_socket_path),
                    workspace_path=workspace_path,
                    language="python",
                )
            )

            # Wait a bit for daemon to start
            await asyncio.sleep(0.1)

            # Trigger shutdown
            daemon_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await daemon_task

            # Verify server.stop was still called despite shutdown_all error
            mock_unix_server.stop.assert_awaited_once()


class TestMultipleWorkspacesAllShutdown:
    """TS4: Verify all workspace LSP servers are shutdown, not just one."""

    @pytest.mark.asyncio
    async def test_shutdown_all_clears_all_workspaces(
        self,
        temp_socket_path: Path,
        tmp_path: Path,
        mock_unix_server: MagicMock,
    ) -> None:
        """Verify shutdown_all is called when registry has multiple workspaces."""
        workspace_path = str(tmp_path / "workspace")
        workspace_path_obj = Path(workspace_path)
        workspace_path_obj.mkdir(parents=True, exist_ok=True)

        # Create a real registry with mocked workspaces that have async shutdown
        from llm_lsp_cli.server import ServerRegistry

        ws1 = MagicMock()
        ws1.shutdown = AsyncMock()
        ws2 = MagicMock()
        ws2.shutdown = AsyncMock()

        registry = ServerRegistry()
        registry._workspaces = {
            "ws1": ws1,
            "ws2": ws2,
        }

        # Mock the shutdown_all to track it
        original_shutdown_all = registry.shutdown_all
        shutdown_called = False

        async def tracked_shutdown_all() -> None:
            nonlocal shutdown_called
            shutdown_called = True
            await original_shutdown_all()

        registry.shutdown_all = tracked_shutdown_all  # type: ignore[method-assign]

        # Create handler with registry
        handler = MagicMock(spec=RequestHandler)
        handler._registry = registry
        handler.handle = AsyncMock()
        # Wire shutdown_servers to call registry's shutdown_all
        handler.shutdown_servers = registry.shutdown_all

        with (
            patch("llm_lsp_cli.daemon.RequestHandler", return_value=handler),
            patch("llm_lsp_cli.daemon.UNIXServer", return_value=mock_unix_server),
        ):
            # Start daemon task
            daemon_task = asyncio.create_task(
                run_daemon(
                    socket_path=str(temp_socket_path),
                    workspace_path=workspace_path,
                    language="python",
                )
            )

            # Wait a bit for daemon to start
            await asyncio.sleep(0.1)

            # Trigger shutdown
            daemon_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await daemon_task

            # Verify shutdown_all was called
            assert shutdown_called, "shutdown_all should have been called"
            # Verify workspaces were cleared
            assert len(registry._workspaces) == 0, "All workspaces should be cleared"
