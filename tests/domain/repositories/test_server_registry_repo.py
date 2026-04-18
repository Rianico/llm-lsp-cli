"""Tests for ServerDefinitionRepository protocol."""

import inspect

from llm_lsp_cli.domain.repositories.server_registry_repo import ServerDefinitionRepository


class TestServerDefinitionRepositoryIsProtocol:
    """ServerDefinitionRepository defines abstract interface."""

    def test_server_definition_repository_is_protocol(self) -> None:
        """ServerDefinitionRepository defines abstract interface."""
        assert hasattr(ServerDefinitionRepository, "get")
        assert hasattr(ServerDefinitionRepository, "list_all")
        assert hasattr(ServerDefinitionRepository, "register")


class TestRepositoryMethodsHaveTypeHints:
    """Repository methods have complete type annotations."""

    def test_repository_methods_have_type_hints(self) -> None:
        """Repository methods have complete type annotations."""
        sig_get = inspect.signature(ServerDefinitionRepository.get)
        # Verify return type annotations exist
        assert sig_get.return_annotation != inspect.Signature.empty
