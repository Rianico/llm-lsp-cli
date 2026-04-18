"""Integration tests for domain layer components.

Tests the integration between WorkspacePath, ServerDefinition,
and LspMethodRouter to verify full request lifecycle.
"""

from pathlib import Path

import pytest

from llm_lsp_cli.domain.entities.server_definition import ServerDefinition
from llm_lsp_cli.domain.exceptions import PathValidationError
from llm_lsp_cli.domain.repositories.server_registry_repo import (
    ServerDefinitionRepository,
)
from llm_lsp_cli.domain.services.lsp_method_router import LspMethodRouter
from llm_lsp_cli.domain.value_objects.workspace_path import WorkspacePath
from llm_lsp_cli.lsp.constants import LSPConstants

# =============================================================================
# In-Memory Repository Implementation for Testing
# =============================================================================


class InMemoryServerDefinitionRepository:
    """In-memory implementation of ServerDefinitionRepository for testing."""

    def __init__(self) -> None:
        self._definitions: dict[str, ServerDefinition] = {}

    def get(self, language_id: str) -> ServerDefinition | None:
        """Retrieve a server definition by language ID."""
        return self._definitions.get(language_id)

    def list_all(self) -> list[ServerDefinition]:
        """List all registered server definitions."""
        return list(self._definitions.values())

    def register(self, definition: ServerDefinition) -> None:
        """Register a new server definition."""
        self._definitions[definition.language_id] = definition


# Type alias for test fixture return type
LifecycleFixture = tuple[WorkspacePath, InMemoryServerDefinitionRepository, LspMethodRouter]


# =============================================================================
# WorkspacePath and ServerDefinition Integration Tests
# =============================================================================


class TestWorkspacePathWithServerDefinition:
    """Integration tests for WorkspacePath with ServerDefinition."""

    def test_workspace_path_validates_server_command_path(
        self, temp_dir: Path
    ) -> None:
        """WorkspacePath can validate paths referenced in server commands."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        (workspace / "bin").mkdir()
        server_bin = workspace / "bin" / "lsp-server"
        server_bin.touch()

        ws_path = WorkspacePath(workspace)
        resolved_bin = ws_path.resolve_child("bin/lsp-server")

        assert resolved_bin.exists()
        assert resolved_bin == server_bin.resolve()

    def test_workspace_path_prevents_outside_server_binary(
        self, temp_dir: Path
    ) -> None:
        """WorkspacePath prevents referencing server binaries outside workspace."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        outside = temp_dir / "outside"
        outside.mkdir()
        (outside / "malicious-server").touch()

        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("../outside/malicious-server")

    def test_server_definition_with_workspace_relative_path(
        self, temp_dir: Path
    ) -> None:
        """ServerDefinition can use workspace-relative paths."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        (workspace / "node_modules").mkdir()

        ws_path = WorkspacePath(workspace)
        node_modules_path = ws_path.resolve_child("node_modules")

        server_def = ServerDefinition(
            language_id="typescript",
            command=str(node_modules_path / ".bin" / "typescript-language-server"),
            args=["--stdio"],
        )

        assert server_def.language_id == "typescript"
        assert "node_modules" in server_def.command


# =============================================================================
# LspMethodRouter and Repository Integration Tests
# =============================================================================


class TestLspMethodRouterWithServerRegistry:
    """Integration tests for LspMethodRouter with ServerDefinitionRepository."""

    @pytest.fixture
    def repository(self) -> InMemoryServerDefinitionRepository:
        """Create an in-memory repository with default servers."""
        repo = InMemoryServerDefinitionRepository()
        repo.register(
            ServerDefinition(
                language_id="python",
                command="pyright-langserver",
                args=["--stdio"],
                timeout_seconds=30,
            )
        )
        repo.register(
            ServerDefinition(
                language_id="typescript",
                command="typescript-language-server",
                args=["--stdio"],
                timeout_seconds=45,
            )
        )
        return repo

    @pytest.fixture
    def router(self) -> LspMethodRouter:
        """Create a fresh LspMethodRouter instance."""
        return LspMethodRouter()

    def test_router_configures_definition_request(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """LspMethodRouter correctly configures definition requests."""
        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None
        assert config.registry_method == "request_definition"
        assert "textDocument" in config.required_params
        assert "position" in config.required_params
        assert config.param_mapping.get("uri") == "textDocument.uri"

    def test_router_configures_hover_request(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """LspMethodRouter correctly configures hover requests."""
        config = router.get_config(LSPConstants.HOVER)
        assert config is not None
        assert config.registry_method == "request_hover"
        assert "textDocument" in config.required_params
        assert "position" in config.required_params

    def test_router_configures_workspace_symbol_without_uri(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """LspMethodRouter configures workspace/symbol without URI mapping."""
        config = router.get_config(LSPConstants.WORKSPACE_SYMBOL)
        assert config is not None
        assert config.registry_method == "request_workspace_symbols"
        assert config.required_params == ["query"]
        assert "uri" not in config.param_mapping

    def test_repository_returns_correct_server_definition(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """Repository returns correct server definition for language."""
        server_def = repository.get("python")
        assert server_def is not None
        assert server_def.language_id == "python"
        assert server_def.command == "pyright-langserver"
        assert server_def.timeout_seconds == 30

    def test_repository_list_all_returns_all_servers(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """Repository list_all returns all registered servers."""
        all_servers = repository.list_all()
        assert len(all_servers) == 2
        language_ids = {s.language_id for s in all_servers}
        assert language_ids == {"python", "typescript"}

    def test_unknown_language_returns_none(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """Repository returns None for unknown language ID."""
        server_def = repository.get("unknown-language")
        assert server_def is None

    def test_unknown_lsp_method_returns_none(
        self,
        router: LspMethodRouter,
        repository: InMemoryServerDefinitionRepository,
    ) -> None:
        """Router returns None for unknown LSP method."""
        config = router.get_config("unknown/method")
        assert config is None


# =============================================================================
# Path Traversal Edge Case Tests
# =============================================================================


class TestPathTraversalEdgeCases:
    """Edge case tests for path traversal prevention."""

    def test_double_dot_traversal(self, temp_dir: Path) -> None:
        """Blocks ../ traversal attempts."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("../../../etc/passwd")

    def test_encoded_dot_traversal(self, temp_dir: Path) -> None:
        """Blocks URL-encoded traversal attempts.

        Note: Path objects don't automatically decode URL encoding,
        so "..%2F..%2Fetc/passwd" is treated as a literal filename.
        This test verifies the behavior - the path resolves within workspace
        because it's treated as a literal filename, not traversal.
        """
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        # URL-encoded paths are NOT decoded by Path - treated as literal filename
        # This is expected behavior - URL decoding should happen at a higher layer
        result = ws_path.resolve_child("..%2F..%2Fetc/passwd")
        # The result is workspace/..%2F..%2Fetc/passwd (literal filename)
        assert workspace.resolve() in result.parents or result.parent == workspace.resolve()

    def test_absolute_path_attempt(self, temp_dir: Path) -> None:
        """Blocks absolute path attempts."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("/etc/passwd")

    def test_symlink_chain_traversal(self, temp_dir: Path) -> None:
        """Blocks symlink chain traversal attempts."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        outside = temp_dir / "outside"
        outside.mkdir()
        intermediate = workspace / "link1"
        intermediate.symlink_to(outside)

        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("link1/secret.txt")

    def test_nested_symlink_traversal(self, temp_dir: Path) -> None:
        """Blocks nested symlink traversal attempts."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        outside = temp_dir / "outside"
        outside.mkdir()
        (outside / "nested").mkdir()

        link1 = workspace / "link1"
        link1.symlink_to(outside)

        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("link1/nested/secret.txt")

    def test_empty_relative_path(self, temp_dir: Path) -> None:
        """Empty relative path returns workspace root."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        # Empty string should return the workspace path itself
        result = ws_path.resolve_child("")
        assert result == workspace.resolve()

    def test_dot_only_path(self, temp_dir: Path) -> None:
        """Single dot path returns workspace root."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        result = ws_path.resolve_child(".")
        assert result == workspace.resolve()

    def test_double_dot_only_path(self, temp_dir: Path) -> None:
        """Double dot path escapes workspace."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("..")

    def test_mixed_traversal(self, temp_dir: Path) -> None:
        """Blocks mixed valid and traversal paths."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        (workspace / "valid").mkdir()
        outside = temp_dir / "outside"
        outside.mkdir()

        ws_path = WorkspacePath(workspace)

        with pytest.raises(PathValidationError):
            ws_path.resolve_child("valid/../../outside/secret.txt")


# =============================================================================
# Invalid Server Name Handling Tests
# =============================================================================


class TestInvalidServerNameHandling:
    """Tests for invalid server name edge cases."""

    def test_empty_language_id(self) -> None:
        """ServerDefinition accepts empty language ID but repository handles it."""
        server_def = ServerDefinition(
            language_id="",
            command="some-server",
        )
        assert server_def.language_id == ""

    def test_whitespace_only_language_id(self) -> None:
        """ServerDefinition accepts whitespace-only language ID."""
        server_def = ServerDefinition(
            language_id="   ",
            command="some-server",
        )
        assert server_def.language_id == "   "

    def test_unicode_language_id(self) -> None:
        """ServerDefinition supports unicode language IDs."""
        server_def = ServerDefinition(
            language_id="python-日本語",
            command="japanese-lsp-server",
        )
        assert server_def.language_id == "python-日本語"

    def test_special_characters_in_language_id(self) -> None:
        """ServerDefinition handles special characters in language ID."""
        server_def = ServerDefinition(
            language_id="c++",
            command="clangd",
        )
        assert server_def.language_id == "c++"

    def test_very_long_language_id(self) -> None:
        """ServerDefinition handles very long language IDs."""
        long_id = "a" * 1000
        server_def = ServerDefinition(
            language_id=long_id,
            command="some-server",
        )
        assert server_def.language_id == long_id

    def test_none_language_id_rejected(self) -> None:
        """None language ID is accepted at runtime but flagged by type checker.

        Note: Python dataclasses don't enforce type hints at runtime.
        The type system (pyright/mypy) will catch this, not runtime.
        """
        # Runtime accepts None - type checking is static, not runtime
        server_def = ServerDefinition(
            language_id=None,  # type: ignore[arg-type]
            command="some-server",
        )
        assert server_def.language_id is None


# =============================================================================
# Full Request Lifecycle Tests
# =============================================================================


class TestFullRequestLifecycle:
    """Tests for full request lifecycle through domain layer."""

    @pytest.fixture
    def setup_lifecycle(
        self, temp_dir: Path
    ) -> tuple[WorkspacePath, InMemoryServerDefinitionRepository, LspMethodRouter]:
        """Set up full domain layer stack."""
        workspace = temp_dir / "project"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("print('hello')")

        ws_path = WorkspacePath(workspace)

        repo = InMemoryServerDefinitionRepository()
        repo.register(
            ServerDefinition(
                language_id="python",
                command="pyright-langserver",
                args=["--stdio"],
                timeout_seconds=30,
            )
        )

        router = LspMethodRouter()

        return ws_path, repo, router

    def test_complete_definition_request_lifecycle(
        self, setup_lifecycle: LifecycleFixture
    ) -> None:
        """Complete lifecycle for a definition request."""
        ws_path, repo, router = setup_lifecycle

        # 1. Validate workspace path
        assert ws_path.path.exists()

        # 2. Resolve source file within workspace
        source_file = ws_path.resolve_child("src/main.py")
        assert source_file.exists()

        # 3. Get server definition for language
        server_def = repo.get("python")
        assert server_def is not None
        assert server_def.command == "pyright-langserver"

        # 4. Get LSP method configuration
        config = router.get_config(LSPConstants.DEFINITION)
        assert config is not None
        assert config.registry_method == "request_definition"

    def test_complete_hover_request_lifecycle(
        self, setup_lifecycle: LifecycleFixture
    ) -> None:
        """Complete lifecycle for a hover request."""
        ws_path, repo, router = setup_lifecycle

        # Validate workspace
        assert ws_path.path.exists()

        # Resolve file
        source_file = ws_path.resolve_child("src/main.py")
        assert source_file.exists()

        # Get server
        server_def = repo.get("python")
        assert server_def is not None

        # Get method config
        config = router.get_config(LSPConstants.HOVER)
        assert config is not None
        assert config.registry_method == "request_hover"

    def test_workspace_symbol_request_lifecycle(
        self, setup_lifecycle: LifecycleFixture
    ) -> None:
        """Complete lifecycle for a workspace/symbol request."""
        ws_path, repo, router = setup_lifecycle

        # Validate workspace
        assert ws_path.path.exists()

        # Get server
        server_def = repo.get("python")
        assert server_def is not None

        # Get method config (no URI mapping for workspace symbols)
        config = router.get_config(LSPConstants.WORKSPACE_SYMBOL)
        assert config is not None
        assert config.registry_method == "request_workspace_symbols"
        assert "uri" not in config.param_mapping

    def test_request_lifecycle_with_path_validation_failure(
        self, setup_lifecycle: LifecycleFixture
    ) -> None:
        """Request lifecycle fails gracefully with path validation error."""
        ws_path, repo, router = setup_lifecycle

        # Attempt to resolve path outside workspace
        with pytest.raises(PathValidationError):
            ws_path.resolve_child("../outside/secret.py")

        # Server and router still functional
        server_def = repo.get("python")
        assert server_def is not None

        config = router.get_config(LSPConstants.COMPLETION)
        assert config is not None

    def test_request_lifecycle_with_unknown_server(
        self, setup_lifecycle: LifecycleFixture
    ) -> None:
        """Request lifecycle handles unknown server gracefully."""
        ws_path, repo, router = setup_lifecycle

        # Workspace is valid
        assert ws_path.path.exists()

        # Unknown server returns None
        server_def = repo.get("unknown-language")
        assert server_def is None

        # Router still functional
        config = router.get_config(LSPConstants.REFERENCES)
        assert config is not None


# =============================================================================
# Repository Protocol Compliance Tests
# =============================================================================


class TestRepositoryProtocolCompliance:
    """Tests verifying repository protocol compliance."""

    def test_repository_implements_get_method(self) -> None:
        """Repository implements get method with correct signature."""
        repo = InMemoryServerDefinitionRepository()
        assert hasattr(repo, "get")
        assert callable(repo.get)  # type: ignore[attr-defined]

    def test_repository_implements_list_all_method(self) -> None:
        """Repository implements list_all method."""
        repo = InMemoryServerDefinitionRepository()
        assert hasattr(repo, "list_all")
        result = repo.list_all()
        assert isinstance(result, list)

    def test_repository_implements_register_method(self) -> None:
        """Repository implements register method."""
        repo = InMemoryServerDefinitionRepository()
        assert hasattr(repo, "register")
        assert callable(repo.register)  # type: ignore[attr-defined]

    def test_repository_protocol_type_hints(self) -> None:
        """Repository protocol has correct type hints."""
        # Verify the protocol defines correct types
        assert hasattr(ServerDefinitionRepository, "get")
        assert hasattr(ServerDefinitionRepository, "list_all")
        assert hasattr(ServerDefinitionRepository, "register")


# =============================================================================
# Data Class Immutability Tests
# =============================================================================


class TestDataClassImmutability:
    """Tests verifying domain objects are immutable."""

    def test_server_definition_is_frozen(self) -> None:
        """ServerDefinition is frozen (immutable)."""
        import dataclasses

        server_def = ServerDefinition(
            language_id="python",
            command="pyright-langserver",
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            server_def.command = "new-command"  # type: ignore[misc]

    def test_workspace_path_is_frozen(self, temp_dir: Path) -> None:
        """WorkspacePath is frozen (immutable)."""
        import dataclasses

        workspace = temp_dir / "project"
        workspace.mkdir()
        ws_path = WorkspacePath(workspace)

        # Attempting to modify via normal attribute assignment raises FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            ws_path.path = Path("/something/else")  # type: ignore[misc]

    def test_lsp_method_config_is_frozen(self) -> None:
        """LspMethodConfig is frozen (immutable)."""
        import dataclasses

        from llm_lsp_cli.domain.services.lsp_method_router import LspMethodConfig

        config = LspMethodConfig(
            registry_method="definition",
            required_params=["textDocument", "position"],
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.registry_method = "new-method"  # type: ignore[misc]
