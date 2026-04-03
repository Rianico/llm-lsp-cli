"""Tests for server registry and workspace manager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_lsp_cli.server.registry import ServerRegistry
from llm_lsp_cli.server.workspace import WorkspaceManager


class TestWorkspaceManager:
    """Tests for WorkspaceManager."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_creates_client(self) -> None:
        """Test that ensure_initialized creates LSP client."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_client_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path="/tmp/test",
                server_command="pylsp",
                server_args=[],
                language_id="python",
            )

            result = await manager.ensure_initialized()

            assert result is mock_client
            assert manager.is_initialized
            mock_client_class.assert_called_once()
            mock_client.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_initialized_returns_existing(self) -> None:
        """Test that ensure_initialized returns existing client."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_client_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path="/tmp/test",
                server_command="pylsp",
                server_args=[],
                language_id="python",
            )

            # First call
            result1 = await manager.ensure_initialized()
            # Second call
            result2 = await manager.ensure_initialized()

            assert result1 is result2
            assert manager.is_initialized
            # Should only initialize once
            mock_client.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        """Test workspace shutdown."""
        with patch("llm_lsp_cli.server.workspace.LSPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock()
            mock_client.shutdown = AsyncMock()
            mock_client_class.return_value = mock_client

            manager = WorkspaceManager(
                workspace_path="/tmp/test",
                server_command="pylsp",
                server_args=[],
                language_id="python",
            )

            await manager.ensure_initialized()
            await manager.shutdown()

            assert not manager.is_initialized
            mock_client.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_without_init(self) -> None:
        """Test shutdown without initialization."""
        manager = WorkspaceManager(
            workspace_path="/tmp/test",
            server_command="pylsp",
            server_args=[],
            language_id="python",
        )

        # Should not raise
        await manager.shutdown()
        assert not manager.is_initialized


class TestServerRegistry:
    """Tests for ServerRegistry."""

    @pytest.mark.asyncio
    async def test_get_or_create_workspace_new(self) -> None:
        """Test creating a new workspace."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            # Mock config to return pylsp config
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            with patch("llm_lsp_cli.server.registry.shutil.which", return_value="/usr/bin/pylsp"):
                registry = ServerRegistry()

                with patch("llm_lsp_cli.server.registry.WorkspaceManager") as mock_wm_class:
                    mock_wm = MagicMock()
                    mock_wm_class.return_value = mock_wm

                    result = await registry.get_or_create_workspace("/tmp/test", "python")

                    assert result is mock_wm
                    assert "/tmp/test" in str(list(registry._workspaces.keys()))

    @pytest.mark.asyncio
    async def test_get_or_create_workspace_existing(self) -> None:
        """Test getting an existing workspace."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            with patch("llm_lsp_cli.server.registry.shutil.which", return_value="/usr/bin/pylsp"):
                registry = ServerRegistry()

                with patch("llm_lsp_cli.server.registry.WorkspaceManager") as mock_wm_class:
                    mock_wm = MagicMock()
                    mock_wm_class.return_value = mock_wm

                    # First call
                    result1 = await registry.get_or_create_workspace("/tmp/test", "python")
                    # Second call (should return same instance)
                    result2 = await registry.get_or_create_workspace("/tmp/test", "python")

                    assert result1 is result2
                    # Should only create once
                    assert mock_wm_class.call_count == 1

    @pytest.mark.asyncio
    async def test_request_definition(self) -> None:
        """Test definition request routing."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            registry = ServerRegistry()

            with patch.object(registry, "get_or_create_workspace") as mock_get:
                mock_workspace = MagicMock()
                mock_workspace.ensure_initialized = AsyncMock()
                mock_client = MagicMock()
                mock_client.request_definition = AsyncMock(return_value=[{"uri": "file://test.py"}])
                mock_workspace.ensure_initialized.return_value = mock_client
                mock_get.return_value = mock_workspace

                result = await registry.request_definition("/tmp/test", "/tmp/test.py", 10, 5)

                assert result == [{"uri": "file://test.py"}]
                mock_client.request_definition.assert_awaited_once_with("/tmp/test.py", 10, 5)

    @pytest.mark.asyncio
    async def test_request_references(self) -> None:
        """Test references request routing."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            registry = ServerRegistry()

            with patch.object(registry, "get_or_create_workspace") as mock_get:
                mock_workspace = MagicMock()
                mock_workspace.ensure_initialized = AsyncMock()
                mock_client = MagicMock()
                mock_client.request_references = AsyncMock(return_value=[{"uri": "file://test.py"}])
                mock_workspace.ensure_initialized.return_value = mock_client
                mock_get.return_value = mock_workspace

                result = await registry.request_references("/tmp/test", "/tmp/test.py", 10, 5)

                assert result == [{"uri": "file://test.py"}]
                mock_client.request_references.assert_awaited_once_with("/tmp/test.py", 10, 5)

    @pytest.mark.asyncio
    async def test_request_completions(self) -> None:
        """Test completions request routing."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            registry = ServerRegistry()

            with patch.object(registry, "get_or_create_workspace") as mock_get:
                mock_workspace = MagicMock()
                mock_workspace.ensure_initialized = AsyncMock()
                mock_client = MagicMock()
                mock_client.request_completions = AsyncMock(return_value=[{"label": "test"}])
                mock_workspace.ensure_initialized.return_value = mock_client
                mock_get.return_value = mock_workspace

                result = await registry.request_completions("/tmp/test", "/tmp/test.py", 10, 5)

                assert result == [{"label": "test"}]

    @pytest.mark.asyncio
    async def test_request_hover(self) -> None:
        """Test hover request routing."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            registry = ServerRegistry()

            with patch.object(registry, "get_or_create_workspace") as mock_get:
                mock_workspace = MagicMock()
                mock_workspace.ensure_initialized = AsyncMock()
                mock_client = MagicMock()
                mock_client.request_hover = AsyncMock(return_value={"contents": {"value": "test"}})
                mock_workspace.ensure_initialized.return_value = mock_client
                mock_get.return_value = mock_workspace

                result = await registry.request_hover("/tmp/test", "/tmp/test.py", 10, 5)

                assert result == {"contents": {"value": "test"}}

    @pytest.mark.asyncio
    async def test_request_document_symbols(self) -> None:
        """Test document symbols request routing."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            registry = ServerRegistry()

            with patch.object(registry, "get_or_create_workspace") as mock_get:
                mock_workspace = MagicMock()
                mock_workspace.ensure_initialized = AsyncMock()
                mock_client = MagicMock()
                mock_client.request_document_symbols = AsyncMock(return_value=[{"name": "test"}])
                mock_workspace.ensure_initialized.return_value = mock_client
                mock_get.return_value = mock_workspace

                result = await registry.request_document_symbols("/tmp/test", "/tmp/test.py")

                assert result == [{"name": "test"}]

    @pytest.mark.asyncio
    async def test_request_workspace_symbols(self) -> None:
        """Test workspace symbols request routing."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            registry = ServerRegistry()

            with patch.object(registry, "get_or_create_workspace") as mock_get:
                mock_workspace = MagicMock()
                mock_workspace.ensure_initialized = AsyncMock()
                mock_client = MagicMock()
                mock_client.request_workspace_symbols = AsyncMock(return_value=[{"name": "test"}])
                mock_workspace.ensure_initialized.return_value = mock_client
                mock_get.return_value = mock_workspace

                result = await registry.request_workspace_symbols("/tmp/test", "test")

            assert result == [{"name": "test"}]

    @pytest.mark.asyncio
    async def test_shutdown_all(self) -> None:
        """Test shutdown all workspaces."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            with patch("llm_lsp_cli.server.registry.shutil.which", return_value="/usr/bin/pylsp"):
                registry = ServerRegistry()

                with patch("llm_lsp_cli.server.registry.WorkspaceManager") as mock_wm_class:
                    mock_wm = MagicMock()
                    mock_wm.shutdown = AsyncMock()
                    mock_wm_class.return_value = mock_wm

                    # Create two workspaces
                    await registry.get_or_create_workspace("/tmp/test1", "python")
                    await registry.get_or_create_workspace("/tmp/test2", "python")

                    await registry.shutdown_all()

                    assert len(registry._workspaces) == 0
                    assert mock_wm.shutdown.call_count == 2

    @pytest.mark.asyncio
    async def test_default_language(self) -> None:
        """Test that default language is python."""
        with patch("llm_lsp_cli.server.registry.ConfigManager") as mock_config_manager:
            mock_config_data = MagicMock()
            mock_config_data.model_dump.return_value = {
                "languages": {
                    "python": {"command": "pylsp", "args": []}
                }
            }
            mock_config_manager.load.return_value = mock_config_data

            with patch("llm_lsp_cli.server.registry.shutil.which", return_value="/usr/bin/pylsp"):
                registry = ServerRegistry()

                with patch("llm_lsp_cli.server.registry.WorkspaceManager") as mock_wm_class:
                    await registry.get_or_create_workspace("/tmp/test")

                    # Check that WorkspaceManager was called with language_id="python"
                    call_args = mock_wm_class.call_args
                    assert call_args.kwargs["language_id"] == "python"
