"""Integration tests for type-safe architecture."""

from llm_lsp_cli.domain import (
    LspMethodRouter,
    LspMethodConfig,
)
from llm_lsp_cli.lsp.constants import LSPConstants


class TestTypeSafeArchitecture:
    """Integration tests verifying type-safe components work together."""

    def test_lsp_method_router_type_safety(self):
        """Verify LspMethodRouter returns typed configurations."""
        router = LspMethodRouter()

        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None
        assert isinstance(config, LspMethodConfig)
        assert isinstance(config.registry_method, str)
        assert isinstance(config.required_params, list)
        assert isinstance(config.param_mapping, dict)

    def test_method_config_has_required_params(self):
        """Verify method configs have required parameter definitions."""
        router = LspMethodRouter()

        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None

        # Definition requires textDocument and position
        assert "textDocument" in config.required_params
        assert "position" in config.required_params

    def test_method_router_diagnostic_config(self):
        """Verify LspMethodRouter has diagnostic method configs."""
        router = LspMethodRouter()

        # Test textDocument/diagnostic
        diag_config = router.get_config(LSPConstants.DIAGNOSTIC)
        assert diag_config is not None
        assert diag_config.registry_method == "request_diagnostics"

        # Test workspace/diagnostic
        ws_diag_config = router.get_config(LSPConstants.WORKSPACE_DIAGNOSTIC)
        assert ws_diag_config is not None
        assert ws_diag_config.registry_method == "request_workspace_diagnostics"
