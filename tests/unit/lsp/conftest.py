"""Shared fixtures for LSP unit tests."""

import logging
import typing
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from llm_lsp_cli.lsp.cache import DiagnosticCache
from llm_lsp_cli.lsp.client import LSPClient


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock LSPClient."""
    return MagicMock()


@pytest.fixture
def temp_workspace_path(temp_dir: Path) -> Path:
    """Create a temporary workspace path for DiagnosticCache."""
    return temp_dir / "workspace"


@pytest.fixture
def diagnostic_cache(temp_workspace_path: Path) -> DiagnosticCache:
    """Create a DiagnosticCache instance for testing."""
    temp_workspace_path.mkdir(exist_ok=True)
    return DiagnosticCache(temp_workspace_path)


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


@pytest.fixture
def log_capture_handler() -> typing.Generator[logging.Handler, None, None]:
    """Fixture to capture log output for assertions."""
    # Arrange
    logger = logging.getLogger("llm_lsp_cli.lsp.transport")
    handler = logging.StreamHandler(StringIO())
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.DEBUG)

    yield handler

    # Cleanup
    logger.removeHandler(handler)
    logger.setLevel(original_level)


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
