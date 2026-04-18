"""Shared fixtures for LSP unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.client import LSPClient, WorkspaceDiagnosticManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock LSPClient."""
    return MagicMock()


@pytest.fixture
def workspace_diagnostic_manager(mock_client: MagicMock) -> WorkspaceDiagnosticManager:
    """Create a WorkspaceDiagnosticManager with a mock client."""
    return WorkspaceDiagnosticManager(mock_client)


@pytest.fixture
def sample_diagnostics() -> list[dict[str, object]]:
    """Sample diagnostic data for tests."""
    return [
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
            "severity": 1,
            "message": "Test error",
            "source": "test",
        }
    ]


@pytest.fixture
def sample_uri() -> str:
    """Sample URI for tests."""
    return "file:///tmp/test/file.py"


@pytest.fixture
def lsp_client() -> LSPClient:
    """Create a basic LSPClient instance."""
    return LSPClient(
        workspace_path="/tmp/test",
        server_command="test",
    )


@pytest.fixture
def lsp_client_with_mocked_transport(lsp_client: LSPClient) -> LSPClient:
    """Create an LSPClient with a mocked transport."""
    lsp_client._transport = AsyncMock()
    return lsp_client


# Helper classes for tests that need them without fixtures
class Helpers:
    """Helper classes for tests."""

    @staticmethod
    def async_mock() -> AsyncMock:
        """Create a basic AsyncMock."""
        return AsyncMock()

    @staticmethod
    def mock() -> MagicMock:
        """Create a basic MagicMock."""
        return MagicMock()


# Make helpers available as pytest.helpers
pytest.helpers = Helpers  # type: ignore
