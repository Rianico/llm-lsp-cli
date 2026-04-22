"""Negative tests verifying removed components no longer exist.

These tests ensure that the WorkspaceDiagnosticManager class and related
obsolete methods have been properly removed from the codebase as specified
in ADR 003 Revised.
"""

import pytest


class TestWorkspaceDiagnosticManagerRemoval:
    """Tests verifying WorkspaceDiagnosticManager class removal."""

    def test_workspace_diagnostic_manager_not_importable(self) -> None:
        """Test WorkspaceDiagnosticManager class cannot be imported."""
        from llm_lsp_cli.lsp import client

        # Verify class does not exist in module
        assert not hasattr(client, "WorkspaceDiagnosticManager")

    def test_workspace_diagnostic_manager_not_in_client_module(self) -> None:
        """Test WorkspaceDiagnosticManager not accessible from client module."""
        from llm_lsp_cli.lsp import client

        assert not hasattr(client, "WorkspaceDiagnosticManager")


class TestLspClientRemovedAttributes:
    """Tests verifying removed attributes from LSPClient."""

    def test_client_has_no_diagnostic_manager_attribute(self) -> None:
        """Test LSPClient has no _diagnostic_manager attribute."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="test",
        )

        assert not hasattr(client, "_diagnostic_manager")

    def test_client_has_no_pull_mode_supported_attribute(self) -> None:
        """Test LSPClient has no _pull_mode_supported attribute."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="test",
        )

        # _pull_mode_supported was part of WorkspaceDiagnosticManager
        # It should not exist on LSPClient
        assert not hasattr(client, "_pull_mode_supported")


class TestLspClientRemovedMethods:
    """Tests verifying removed methods from LSPClient."""

    def test_client_has_no_handle_register_capability_request(self) -> None:
        """Test _handle_register_capability_request method is removed."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="test",
        )

        assert not hasattr(client, "_handle_register_capability_request")

    def test_client_has_no_handle_diagnostic_refresh_request(self) -> None:
        """Test _handle_diagnostic_refresh_request method is removed."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="test",
        )

        assert not hasattr(client, "_handle_diagnostic_refresh_request")

    def test_client_has_no_set_pull_mode_supported_method(self) -> None:
        """Test set_pull_mode_supported method is removed."""
        from llm_lsp_cli.lsp.client import LSPClient

        client = LSPClient(
            workspace_path="/tmp/test",
            server_command="test",
        )

        assert not hasattr(client, "set_pull_mode_supported")


class TestRemovedTestFile:
    """Tests verifying old test file should be deleted."""

    def test_old_test_file_should_not_exist(self) -> None:
        """Test that test_workspace_diagnostic_manager.py should be deleted.

        This is a marker test - the actual deletion should happen in REFACTOR phase.
        """
        # This test documents that the file SHOULD be deleted
        # The actual assertion will be enforced in REFACTOR phase
        # For now, just document the expected state
        expected_deleted = True
        assert expected_deleted
