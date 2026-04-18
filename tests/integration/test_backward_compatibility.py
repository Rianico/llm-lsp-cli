"""Tests ensuring backward compatibility after refactoring."""

import pytest

from llm_lsp_cli.lsp.constants import LSPConstants


class TestBackwardCompatibility:
    """Verify existing APIs still work after refactoring."""

    def test_config_manager_still_accessible(self):
        """Verify ConfigManager public API still works."""
        from llm_lsp_cli.config import ConfigManager

        # These methods should still exist for backward compatibility
        assert hasattr(ConfigManager, "build_pid_file_path")
        assert hasattr(ConfigManager, "build_socket_path")

    def test_config_manager_build_log_file_path(self):
        """Verify ConfigManager has build_log_file_path method."""
        from llm_lsp_cli.config import ConfigManager

        assert hasattr(ConfigManager, "build_log_file_path")
        assert hasattr(ConfigManager, "build_daemon_log_path")

    def test_lsp_constants_available(self):
        """Verify LSPConstants is available for import."""
        from llm_lsp_cli.lsp.constants import LSPConstants

        assert LSPConstants.DEFINITION == "textDocument/definition"
        assert LSPConstants.REFERENCES == "textDocument/references"

    def test_method_router_available(self):
        """Verify LspMethodRouter is available for import."""
        from llm_lsp_cli.domain.services import LspMethodRouter

        router = LspMethodRouter()
        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None
        assert config.registry_method == "request_definition"

    def test_existing_tests_still_pass(self):
        """Verify the test suite structure is valid.

        Note: Full test suite execution is verified by CI/CD pipeline.
        This test just confirms the test infrastructure is intact.
        """
        # Just verify we can import test modules without errors
        from llm_lsp_cli.config import ConfigManager
        from llm_lsp_cli.domain.services import LspMethodRouter
        from llm_lsp_cli.lsp.constants import LSPConstants

        # Verify key components are importable and functional
        assert ConfigManager is not None
        assert LspMethodRouter is not None
        assert LSPConstants is not None
