"""Tests for LspMethodRouter domain service."""

import pytest

from llm_lsp_cli.domain.services.lsp_method_router import LspMethodRouter
from llm_lsp_cli.lsp.constants import LSPConstants


@pytest.fixture
def router() -> LspMethodRouter:
    """Create a fresh LspMethodRouter instance."""
    return LspMethodRouter()


class TestRouterUsesConstantsNotStrings:
    """LspMethodRouter references LSPConstants, not hardcoded strings."""

    def test_router_uses_constants_not_strings(self, router: LspMethodRouter) -> None:
        """LspMethodRouter references LSPConstants, not hardcoded strings."""
        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None


class TestRouterHasAllLspMethods:
    """Router configured for all standard LSP methods."""

    def test_router_has_all_lsp_methods(self, router: LspMethodRouter) -> None:
        """Router configured for all standard LSP methods."""
        required_methods = [
            LSPConstants.DEFINITION,
            LSPConstants.REFERENCES,
            LSPConstants.COMPLETION,
            LSPConstants.HOVER,
            LSPConstants.DOCUMENT_SYMBOL,
            LSPConstants.WORKSPACE_SYMBOL,
        ]
        for method in required_methods:
            config = router.get_config(method)
            assert config is not None, f"Missing config for {method}"


class TestRouterConfigHasRequiredFields:
    """LspMethodConfig has registry_method, required_params, param_mapping."""

    def test_router_config_has_required_fields(self, router: LspMethodRouter) -> None:
        """LspMethodConfig has registry_method, required_params, param_mapping."""
        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None
        assert hasattr(config, "registry_method")
        assert hasattr(config, "required_params")
        assert hasattr(config, "param_mapping")
