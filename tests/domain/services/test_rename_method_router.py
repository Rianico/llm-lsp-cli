"""Tests for LspMethodRouter rename method configurations.

This module tests that the router has configurations for PREPARE_RENAME and RENAME methods.

Key behaviors tested:
1. Router has PREPARE_RENAME config mapping to request_prepare_rename
2. Router has RENAME config mapping to request_rename
3. Configs have correct required_params
"""

import pytest

from llm_lsp_cli.domain.services.lsp_method_router import LspMethodRouter
from llm_lsp_cli.lsp.constants import LSPConstants


@pytest.fixture
def router() -> LspMethodRouter:
    """Create a fresh LspMethodRouter instance."""
    return LspMethodRouter()


class TestRouterHasPrepareRenameConfig:
    """Router configured for PREPARE_RENAME method."""

    def test_router_has_prepare_rename_config(self, router: LspMethodRouter) -> None:
        """Router configured for PREPARE_RENAME method."""
        config = router.get_config(LSPConstants.PREPARE_RENAME)
        assert config is not None, f"Missing config for {LSPConstants.PREPARE_RENAME}"

    def test_prepare_rename_config_has_correct_registry_method(
        self, router: LspMethodRouter
    ) -> None:
        """PREPARE_RENAME config maps to request_prepare_rename."""
        config = router.get_config(LSPConstants.PREPARE_RENAME)
        assert config is not None
        assert config.registry_method == "request_prepare_rename"

    def test_prepare_rename_config_has_required_params(
        self, router: LspMethodRouter
    ) -> None:
        """PREPARE_RENAME config has textDocument and position params."""
        config = router.get_config(LSPConstants.PREPARE_RENAME)
        assert config is not None
        assert "textDocument" in config.required_params
        assert "position" in config.required_params


class TestRouterHasRenameConfig:
    """Router configured for RENAME method."""

    def test_router_has_rename_config(self, router: LspMethodRouter) -> None:
        """Router configured for RENAME method."""
        config = router.get_config(LSPConstants.RENAME)
        assert config is not None, f"Missing config for {LSPConstants.RENAME}"

    def test_rename_config_has_correct_registry_method(
        self, router: LspMethodRouter
    ) -> None:
        """RENAME config maps to request_rename."""
        config = router.get_config(LSPConstants.RENAME)
        assert config is not None
        assert config.registry_method == "request_rename"

    def test_rename_config_has_required_params(
        self, router: LspMethodRouter
    ) -> None:
        """RENAME config has textDocument, position, and newName params."""
        config = router.get_config(LSPConstants.RENAME)
        assert config is not None
        assert "textDocument" in config.required_params
        assert "position" in config.required_params
        assert "newName" in config.required_params


class TestRouterRenameConfigsFollowPattern:
    """Rename configs follow the same pattern as other methods."""

    def test_prepare_rename_config_has_uri_mapping(
        self, router: LspMethodRouter
    ) -> None:
        """PREPARE_RENAME config has URI mapping like other textDocument methods."""
        config = router.get_config(LSPConstants.PREPARE_RENAME)
        assert config is not None
        assert "uri" in config.param_mapping

    def test_rename_config_has_uri_mapping(
        self, router: LspMethodRouter
    ) -> None:
        """RENAME config has URI mapping like other textDocument methods."""
        config = router.get_config(LSPConstants.RENAME)
        assert config is not None
        assert "uri" in config.param_mapping
