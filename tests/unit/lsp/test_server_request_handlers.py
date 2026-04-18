"""Tests for LSPClient server request handlers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.client import LSPClient


class TestConfigurationRequestHandler:
    """Test the _handle_configuration_request handler."""

    def test_handle_configuration_request_returns_diagnostic_mode(
        self,
        lsp_client: LSPClient,
    ) -> None:
        """Test configuration handler returns diagnostic mode."""
        params = {
            "items": [
                {"section": "basedpyright.analysis"},
                {"section": "python.analysis"},
            ]
        }

        result = lsp_client._handle_configuration_request(params)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["diagnosticMode"] == "workspace"
        assert result[1]["diagnosticMode"] == "workspace"

    def test_handle_configuration_request_empty_section(
        self,
        lsp_client: LSPClient,
    ) -> None:
        """Test configuration with empty section returns empty dict."""
        params = {"items": [{"section": ""}]}

        result = lsp_client._handle_configuration_request(params)

        assert len(result) == 1
        assert result[0] == {}


class TestRegisterCapabilityHandler:
    """Test the _handle_register_capability_request handler."""

    async def test_handle_register_capability_workspace_diagnostics(
        self,
        lsp_client: LSPClient,
    ) -> None:
        """Test capability registration triggers diagnostic."""
        lsp_client._diagnostic_manager = AsyncMock()
        lsp_client._diagnostic_manager.request = AsyncMock()
        lsp_client._diagnostic_manager.set_pull_mode_supported = MagicMock()

        params = {
            "registrations": [
                {
                    "id": "1",
                    "method": "textDocument/diagnostic",
                    "registerOptions": {"workspaceDiagnostics": True},
                }
            ]
        }

        result = await lsp_client._handle_register_capability_request(params)

        assert result == {}
        # Verify diagnostic was triggered (may need small delay for asyncio.create_task)
        await asyncio.sleep(0.1)
        assert lsp_client._diagnostic_manager.request.called

    async def test_handle_register_capability_other_method(
        self,
        lsp_client: LSPClient,
    ) -> None:
        """Test capability registration for other methods."""
        lsp_client._diagnostic_manager = None

        params = {
            "registrations": [
                {
                    "id": "1",
                    "method": "workspace/fileOperations",
                    "registerOptions": {},
                }
            ]
        }

        result = await lsp_client._handle_register_capability_request(params)

        assert result == {}


class TestDiagnosticRefreshHandler:
    """Test the _handle_diagnostic_refresh_request handler."""

    async def test_handle_diagnostic_refresh_triggers_request(
        self,
        lsp_client: LSPClient,
    ) -> None:
        """Test diagnostic refresh triggers collection."""
        lsp_client._diagnostic_manager = AsyncMock()
        lsp_client._diagnostic_manager.request = AsyncMock()

        params = {}

        result = lsp_client._handle_diagnostic_refresh_request(params)

        assert result == {}
        await asyncio.sleep(0.1)
        assert lsp_client._diagnostic_manager.request.called

    def test_handle_diagnostic_refresh_no_manager(
        self,
        lsp_client: LSPClient,
    ) -> None:
        """Test diagnostic refresh with no manager doesn't crash."""
        lsp_client._diagnostic_manager = None

        result = lsp_client._handle_diagnostic_refresh_request({})

        assert result == {}
