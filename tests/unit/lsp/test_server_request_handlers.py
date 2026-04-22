"""Tests for LSPClient server request handlers."""

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
