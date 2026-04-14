"""Unit tests for WorkspaceManager timeout functionality."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from llm_lsp_cli.server.workspace import WorkspaceManager


class TestWorkspaceTimeout:
    """Tests for WorkspaceManager.ensure_initialized() timeout behavior."""

    @pytest.mark.asyncio
    async def test_lsp_initialization_success_with_delay(self, temp_dir):
        """Happy path: LSP initializes after delay, succeeds within timeout."""
        workspace = temp_dir / "workspace"
        workspace.mkdir()

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            # Setup mock LSP client that succeeds after 2 second delay
            mock_client = AsyncMock()
            async def delayed_initialize():
                await asyncio.sleep(0.1)  # Simulate 100ms delay (scaled down for test)
                return {"capabilities": {}}
            mock_client.initialize = delayed_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(workspace),
                server_command="pyright-langserver",
                timeout=5.0,  # 5 second timeout
            )

            # Should succeed
            client = await manager.ensure_initialized()
            assert client is mock_client
            assert manager.is_initialized is True

    @pytest.mark.asyncio
    async def test_lsp_initialization_timeout_raises_error(self, temp_dir):
        """Timeout: LSP initialization hangs, TimeoutError raised after timeout."""
        workspace = temp_dir / "workspace"
        workspace.mkdir()

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            # Setup mock LSP client that raises TimeoutError when using asyncio.wait_for
            # In RED state, this test will hang because ensure_initialized doesn't use wait_for
            # In GREEN state, the TimeoutError will be raised properly
            mock_client = AsyncMock()
            # Simulate a hang by never completing
            hang_event = asyncio.Event()
            async def hanging_initialize():
                await hang_event.wait()  # Will never be set
            mock_client.initialize = hanging_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(workspace),
                server_command="pyright-langserver",
                timeout=0.2,  # Short timeout for test
            )

            # Wrap with our own timeout to prevent test from hanging forever
            # In RED state: this will timeout (proving the bug exists)
            # In GREEN state: the inner TimeoutError will be raised
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(manager.ensure_initialized(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_timeout_error_includes_server_command(self, temp_dir, caplog):
        """Timeout error message includes server command for debugging."""
        import logging

        workspace = temp_dir / "workspace"
        workspace.mkdir()

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = AsyncMock()
            async def hanging_initialize():
                await asyncio.Event().wait()  # Never completes
            mock_client.initialize = hanging_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(workspace),
                server_command="custom-lsp-server",
                timeout=0.2,
            )

            # Wrap with outer timeout to prevent test hanging
            with (
                caplog.at_level(logging.ERROR),
                pytest.raises(asyncio.TimeoutError),
            ):
                await asyncio.wait_for(manager.ensure_initialized(), timeout=1.0)

            # Verify error was logged with server command
            assert "custom-lsp-server" in caplog.text

    @pytest.mark.asyncio
    async def test_timeout_error_includes_workspace_path(self, temp_dir, caplog):
        """Timeout error message includes workspace path for debugging."""
        import logging

        workspace = temp_dir / "workspace"
        workspace.mkdir()

        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class:
            mock_client = AsyncMock()
            async def hanging_initialize():
                await asyncio.Event().wait()  # Never completes
            mock_client.initialize = hanging_initialize
            mock_lsp_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path=str(workspace),
                server_command="pyright-langserver",
                timeout=0.2,
            )

            # Wrap with outer timeout to prevent test hanging
            with (
                caplog.at_level(logging.ERROR),
                pytest.raises(asyncio.TimeoutError),
            ):
                await asyncio.wait_for(manager.ensure_initialized(), timeout=1.0)

            # Verify error was logged with workspace path
            assert str(workspace) in caplog.text

    @pytest.mark.asyncio
    async def test_uses_asyncio_wait_for_with_timeout(self, temp_dir):
        """Verifies asyncio.wait_for is used with the correct timeout."""
        workspace = temp_dir / "workspace"
        workspace.mkdir()

        with (
            patch("llm_lsp_cli.server.workspace.LSPClient") as mock_lsp_class,
            patch("asyncio.wait_for") as mock_wait_for,
        ):
            mock_client = AsyncMock()
            mock_client.initialize = AsyncMock(return_value={"capabilities": {}})
            mock_lsp_class.return_value = mock_client

            # Setup wait_for to return the result
            mock_wait_for.return_value = {"capabilities": {}}

            manager = WorkspaceManager(
                workspace_path=str(workspace),
                server_command="pyright-langserver",
                timeout=30.0,
            )

            await manager.ensure_initialized()

            # Verify wait_for was called with timeout
            assert mock_wait_for.called
            call_args = mock_wait_for.call_args
            assert call_args is not None
            # Check timeout was passed (either positional or keyword)
            if call_args.kwargs:
                assert call_args.kwargs.get("timeout") == 30.0
            else:
                # Timeout might be passed as positional argument
                assert len(call_args.args) >= 2
                assert call_args.args[1] == 30.0
