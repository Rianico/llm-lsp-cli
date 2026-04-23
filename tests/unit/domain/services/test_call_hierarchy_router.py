"""Tests for LspMethodRouter call hierarchy method configurations."""

import pytest

from llm_lsp_cli.lsp.constants import LSPConstants


class TestLspMethodRouterCallHierarchy:
    """Tests for LspMethodRouter call hierarchy configurations."""

    @pytest.fixture
    def router(self) -> pytest.fixture:
        """Create an LspMethodRouter for testing."""
        from llm_lsp_cli.domain.services import LspMethodRouter

        return LspMethodRouter()

    def test_router_has_incoming_calls_config(self, router: pytest.fixture) -> None:
        """Router should have config for callHierarchy/incomingCalls."""
        # First check the constant exists
        assert hasattr(LSPConstants, "CALL_HIERARCHY_INCOMING_CALLS")

        config = router.get_config(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS)
        assert config is not None

    def test_router_has_outgoing_calls_config(self, router: pytest.fixture) -> None:
        """Router should have config for callHierarchy/outgoingCalls."""
        # First check the constant exists
        assert hasattr(LSPConstants, "CALL_HIERARCHY_OUTGOING_CALLS")

        config = router.get_config(LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS)
        assert config is not None

    def test_incoming_calls_registry_method(self, router: pytest.fixture) -> None:
        """Incoming calls config should map to request_call_hierarchy_incoming."""
        config = router.get_config(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS)
        assert config is not None
        assert config.registry_method == "request_call_hierarchy_incoming"

    def test_outgoing_calls_registry_method(self, router: pytest.fixture) -> None:
        """Outgoing calls config should map to request_call_hierarchy_outgoing."""
        config = router.get_config(LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS)
        assert config is not None
        assert config.registry_method == "request_call_hierarchy_outgoing"

    def test_incoming_calls_required_params(self, router: pytest.fixture) -> None:
        """Incoming calls config should have required params."""
        config = router.get_config(LSPConstants.CALL_HIERARCHY_INCOMING_CALLS)
        assert config is not None
        # Should require textDocument and position for prepareCallHierarchy
        required = config.required_params
        assert "textDocument" in required
        assert "position" in required

    def test_outgoing_calls_required_params(self, router: pytest.fixture) -> None:
        """Outgoing calls config should have required params."""
        config = router.get_config(LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS)
        assert config is not None
        # Should require textDocument and position for prepareCallHierarchy
        required = config.required_params
        assert "textDocument" in required
        assert "position" in required


class TestLSPConstantsCallHierarchy:
    """Tests for LSPConstants call hierarchy method names."""

    def test_call_hierarchy_incoming_calls_constant(self) -> None:
        """LSPConstants should have CALL_HIERARCHY_INCOMING_CALLS."""
        assert hasattr(LSPConstants, "CALL_HIERARCHY_INCOMING_CALLS")
        assert LSPConstants.CALL_HIERARCHY_INCOMING_CALLS == "callHierarchy/incomingCalls"

    def test_call_hierarchy_outgoing_calls_constant(self) -> None:
        """LSPConstants should have CALL_HIERARCHY_OUTGOING_CALLS."""
        assert hasattr(LSPConstants, "CALL_HIERARCHY_OUTGOING_CALLS")
        assert LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS == "callHierarchy/outgoingCalls"

    def test_prepare_call_hierarchy_constant_exists(self) -> None:
        """LSPConstants should already have PREPARE_CALL_HIERARCHY."""
        assert hasattr(LSPConstants, "PREPARE_CALL_HIERARCHY")
        assert LSPConstants.PREPARE_CALL_HIERARCHY == "textDocument/prepareCallHierarchy"
