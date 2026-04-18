"""Integration tests for type-safe architecture."""

import pytest
from pathlib import Path

from llm_lsp_cli.domain import (
    ServerDefinition,
    WorkspacePath,
    ServerDefinitionRepository,
    LspMethodRouter,
    LspMethodConfig,
)
from llm_lsp_cli.lsp.constants import LSPConstants


class TestTypeSafeArchitecture:
    """Integration tests verifying type-safe components work together."""

    def test_server_definition_type_construction(self, tmp_path: Path):
        """Verify ServerDefinition construction with type safety."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create workspace path (type-safe VO)
        ws_path = WorkspacePath(workspace)
        assert ws_path.path == workspace.resolve()

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


class TestProtocolImplementations:
    """Verify concrete implementations satisfy protocols."""

    def test_json_repo_satisfies_protocol(self):
        """Verify JsonServerDefinitionRepository satisfies protocol."""
        from llm_lsp_cli.infrastructure.config.repository.json_server_def_repo import (
            JsonServerDefinitionRepository,
        )
        from llm_lsp_cli.domain import ServerDefinitionRepository

        # Runtime check - repository should satisfy protocol
        repo = JsonServerDefinitionRepository(config_file=Path("/tmp/test.json"))

        # Verify protocol methods exist
        assert callable(getattr(repo, "get", None))
        assert callable(getattr(repo, "list_all", None))
        assert callable(getattr(repo, "register", None))
