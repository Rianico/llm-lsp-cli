"""Tests for daemon LSP startup behavior.

This module tests the lazy startup behavior of LSP servers in the daemon,
particularly around daemon restart scenarios.

Key scenarios:
- TS1: Lazy startup on first request after daemon start
- TS2: LSP startup after daemon restart
- TS3: Workspace manager re-initialization after shutdown
- TS4: ServerRegistry workspace clearing on shutdown
- TS5: No "already initialized" false positive
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.server.registry import ServerRegistry
from llm_lsp_cli.server.workspace import WorkspaceManager

# --- Helper functions for test setup ---


def create_mock_lsp_client(*, with_shutdown: bool = True) -> AsyncMock:
    """Create a mock LSP client with standard method setup.

    Args:
        with_shutdown: If True, include shutdown method (default: True).

    Returns:
        AsyncMock configured as an LSP client.
    """
    mock_client = AsyncMock(spec=["initialize", "shutdown"] if with_shutdown else ["initialize"])
    mock_client.initialize = AsyncMock(return_value=MagicMock())
    if with_shutdown:
        mock_client.shutdown = AsyncMock()
    return mock_client


def create_test_workspace(tmp_path: Path, name: str = "workspace") -> Path:
    """Create a test workspace directory with an optional Python file.

    Args:
        tmp_path: Pytest tmp_path fixture.
        name: Workspace directory name.

    Returns:
        Path to the created workspace.
    """
    workspace = tmp_path / name
    workspace.mkdir()
    return workspace


class TestTS1LazyStartupOnFirstRequest:
    """TS1: Verify LSP server starts when first request is made after daemon start."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_creates_lsp_client(self, tmp_path: Path) -> None:
        """WorkspaceManager.ensure_initialized() creates LSPClient on first call."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
            server_args=["--stdio"],
        )

        # Before initialization
        assert not manager.is_initialized
        assert manager._client is None

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = create_mock_lsp_client(with_shutdown=False)
            mock_lsp_class.return_value = mock_client

            # First call should trigger initialization
            client = await manager.ensure_initialized()

            # Verify LSPClient was created
            mock_lsp_class.assert_called_once()
            mock_client.initialize.assert_called_once()
            assert manager.is_initialized
            assert client is mock_client

    @pytest.mark.asyncio
    async def test_ensure_initialized_uses_cached_client(self, tmp_path: Path) -> None:
        """WorkspaceManager.ensure_initialized() returns cached client on subsequent calls."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
        )

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = create_mock_lsp_client(with_shutdown=False)
            mock_lsp_class.return_value = mock_client

            # First call
            client1 = await manager.ensure_initialized()

            # Reset mock to verify it's not called again
            mock_lsp_class.reset_mock()
            mock_client.initialize.reset_mock()

            # Second call should use cached client
            client2 = await manager.ensure_initialized()

            # Should NOT create new client
            mock_lsp_class.assert_not_called()
            mock_client.initialize.assert_not_called()
            assert client1 is client2


class TestTS2LSPStartupAfterDaemonRestart:
    """TS2: Verify LSP server starts correctly after daemon stop + start cycle."""

    @pytest.mark.asyncio
    async def test_new_workspace_after_registry_shutdown(self, tmp_path: Path) -> None:
        """After shutdown_all(), new workspace is created on next request."""
        workspace = create_test_workspace(tmp_path)

        with patch("llm_lsp_cli.server.registry.ServerRegistry._get_server_command") as mock_cmd:
            mock_cmd.return_value = ("pyright-langserver", ["--stdio"])

            registry = ServerRegistry()

            # First request - creates workspace
            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
                mock_client = create_mock_lsp_client()  # Needs shutdown for shutdown_all()
                mock_lsp_class.return_value = mock_client

                ws1 = await registry.get_or_create_workspace(str(workspace))
                client1 = await ws1.ensure_initialized()
                first_client_id = id(client1)

            # Simulate daemon shutdown
            await registry.shutdown_all()

            # Verify workspaces are cleared
            assert len(registry._workspaces) == 0

            # Simulate daemon restart - new registry instance
            # (In real scenario, this would be a new process with fresh state)
            registry2 = ServerRegistry()

            # Second request after restart
            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class2:
                mock_client2 = create_mock_lsp_client(with_shutdown=False)
                mock_lsp_class2.return_value = mock_client2

                ws2 = await registry2.get_or_create_workspace(str(workspace))
                client2 = await ws2.ensure_initialized()
                second_client_id = id(client2)

            # Verify new client was created (not reused)
            assert second_client_id != first_client_id

    @pytest.mark.asyncio
    async def test_same_registry_reused_after_shutdown(self, tmp_path: Path) -> None:
        """Same ServerRegistry can create new workspace after shutdown_all().

        This tests the scenario where the daemon process doesn't fully restart
        but the registry state is cleared and needs to work with new requests.
        """
        workspace = create_test_workspace(tmp_path)

        with patch("llm_lsp_cli.server.registry.ServerRegistry._get_server_command") as mock_cmd:
            mock_cmd.return_value = ("pyright-langserver", ["--stdio"])

            registry = ServerRegistry()

            # First request - creates workspace
            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
                mock_client = create_mock_lsp_client()
                mock_lsp_class.return_value = mock_client

                ws1 = await registry.get_or_create_workspace(str(workspace))
                await ws1.ensure_initialized()
                assert ws1.is_initialized

            # Simulate daemon shutdown (clears state)
            await registry.shutdown_all()

            # Verify workspaces are cleared
            assert len(registry._workspaces) == 0

            # REUSE SAME REGISTRY - this is the key test
            # A new request on the same registry should create fresh workspace
            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class2:
                mock_client2 = create_mock_lsp_client(with_shutdown=False)
                mock_lsp_class2.return_value = mock_client2

                ws2 = await registry.get_or_create_workspace(str(workspace))

                # Verify this is a NEW workspace (not the old one)
                assert ws2 is not ws1
                assert not ws2.is_initialized  # New workspace starts uninitialized

                await ws2.ensure_initialized()

                # Verify initialization was called on new client
                mock_client2.initialize.assert_called_once()
                assert ws2.is_initialized


class TestTS3WorkspaceManagerReinitialization:
    """TS3: Verify WorkspaceManager properly re-initializes after shutdown()."""

    @pytest.mark.asyncio
    async def test_shutdown_resets_initialized_flag(self, tmp_path: Path) -> None:
        """shutdown() sets _initialized = False."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
        )

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = create_mock_lsp_client()
            mock_lsp_class.return_value = mock_client

            # Initialize
            await manager.ensure_initialized()
            assert manager.is_initialized

            # Shutdown
            await manager.shutdown()

            # Verify state is reset
            assert not manager.is_initialized
            assert manager._client is None

    @pytest.mark.asyncio
    async def test_reinitialize_creates_new_client_after_shutdown(self, tmp_path: Path) -> None:
        """ensure_initialized() creates NEW client after shutdown()."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
        )

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client1 = create_mock_lsp_client()
            mock_lsp_class.return_value = mock_client1

            # First initialization
            client1 = await manager.ensure_initialized()
            first_client_id = id(client1)

            # Shutdown
            await manager.shutdown()

        # Second initialization (after shutdown)
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class2:
            mock_client2 = create_mock_lsp_client(with_shutdown=False)
            mock_lsp_class2.return_value = mock_client2

            client2 = await manager.ensure_initialized()
            second_client_id = id(client2)

            # Verify new client was created
            mock_client2.initialize.assert_called_once()
            assert second_client_id != first_client_id


class TestTS4ServerRegistryWorkspaceClearing:
    """TS4: Verify shutdown_all() properly clears workspaces."""

    @pytest.mark.asyncio
    async def test_shutdown_all_clears_workspaces_dict(self, tmp_path: Path) -> None:
        """shutdown_all() clears _workspaces dict."""
        workspace1 = create_test_workspace(tmp_path, "workspace1")
        workspace2 = create_test_workspace(tmp_path, "workspace2")

        with patch("llm_lsp_cli.server.registry.ServerRegistry._get_server_command") as mock_cmd:
            mock_cmd.return_value = ("pyright-langserver", ["--stdio"])

            registry = ServerRegistry()

            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
                mock_client = create_mock_lsp_client()
                mock_lsp_class.return_value = mock_client

                # Create two workspaces
                await registry.get_or_create_workspace(str(workspace1))
                await registry.get_or_create_workspace(str(workspace2))

                assert len(registry._workspaces) == 2

            # Shutdown
            await registry.shutdown_all()

            # Verify workspaces are cleared
            assert len(registry._workspaces) == 0

    @pytest.mark.asyncio
    async def test_shutdown_all_calls_shutdown_on_each_workspace(self, tmp_path: Path) -> None:
        """shutdown_all() calls shutdown() on each workspace."""
        workspace = create_test_workspace(tmp_path)

        with patch("llm_lsp_cli.server.registry.ServerRegistry._get_server_command") as mock_cmd:
            mock_cmd.return_value = ("pyright-langserver", ["--stdio"])

            registry = ServerRegistry()

            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
                mock_client = create_mock_lsp_client()
                mock_lsp_class.return_value = mock_client

                ws = await registry.get_or_create_workspace(str(workspace))
                await ws.ensure_initialized()

            # Track shutdown calls
            with patch.object(ws, "shutdown", new=AsyncMock()) as mock_shutdown:
                await registry.shutdown_all()
                mock_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new_workspace_after_clear(self, tmp_path: Path) -> None:
        """After shutdown_all(), get_or_create_workspace() creates NEW workspace."""
        workspace = create_test_workspace(tmp_path)

        with patch("llm_lsp_cli.server.registry.ServerRegistry._get_server_command") as mock_cmd:
            mock_cmd.return_value = ("pyright-langserver", ["--stdio"])

            registry = ServerRegistry()

            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
                mock_client = create_mock_lsp_client()
                mock_lsp_class.return_value = mock_client

                ws1 = await registry.get_or_create_workspace(str(workspace))
                first_ws_id = id(ws1)

            # Shutdown and clear
            await registry.shutdown_all()

            with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class2:
                mock_client2 = create_mock_lsp_client(with_shutdown=False)
                mock_lsp_class2.return_value = mock_client2

                ws2 = await registry.get_or_create_workspace(str(workspace))
                second_ws_id = id(ws2)

                # Verify NEW workspace was created (different object)
                assert second_ws_id != first_ws_id


class TestTS5NoAlreadyInitializedFalsePositive:
    """TS5: Verify ensure_initialized() doesn't incorrectly return cached client."""

    @pytest.mark.asyncio
    async def test_shutdown_clears_client_reference(self, tmp_path: Path) -> None:
        """shutdown() clears _client reference, not just _initialized flag."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
        )

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = create_mock_lsp_client()
            mock_lsp_class.return_value = mock_client

            # Initialize
            await manager.ensure_initialized()
            assert manager._client is not None

        # Shutdown
        await manager.shutdown()

        # Verify client reference is cleared
        assert manager._client is None
        assert not manager.is_initialized

    @pytest.mark.asyncio
    async def test_ensure_initialized_after_shutdown_uses_new_client(self, tmp_path: Path) -> None:
        """ensure_initialized() after shutdown creates NEW LSPClient instance."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
        )

        # First initialization
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client1 = create_mock_lsp_client()
            mock_lsp_class.return_value = mock_client1

            client1 = await manager.ensure_initialized()
            assert client1 is mock_client1

        # Shutdown
        await manager.shutdown()

        # Second initialization
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class2:
            mock_client2 = create_mock_lsp_client(with_shutdown=False)
            mock_lsp_class2.return_value = mock_client2

            client2 = await manager.ensure_initialized()

            # Verify NEW mock client was used
            assert client2 is mock_client2
            assert client2 is not mock_client1


class TestTS6ConcurrentInitialization:
    """Additional tests for async safety and concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_ensure_initialized_calls_single_client(self, tmp_path: Path) -> None:
        """Concurrent ensure_initialized() calls only create one client."""
        workspace = create_test_workspace(tmp_path)

        manager = WorkspaceManager(
            workspace_path=str(workspace),
            server_command="pyright-langserver",
        )

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = create_mock_lsp_client(with_shutdown=False)
            mock_lsp_class.return_value = mock_client

            # Launch multiple concurrent ensure_initialized calls
            results = await asyncio.gather(
                manager.ensure_initialized(),
                manager.ensure_initialized(),
                manager.ensure_initialized(),
            )

            # All calls should return same client
            assert results[0] is results[1] is results[2]

            # LSPClient should only be created once
            mock_lsp_class.assert_called_once()
            mock_client.initialize.assert_called_once()
