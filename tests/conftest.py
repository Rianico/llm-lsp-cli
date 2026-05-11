"""Pytest configuration and fixtures."""

# pyright: reportMissingTypeStubs=false

import logging
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from llm_lsp_cli.output.formatter import Position


def setup_mock_client_cache_accessors(mock_client: MagicMock, cache: "DiagnosticCache") -> None:
    """Set up mock accessor methods that delegate to the cache.

    The public accessor methods get_diagnostic_cache_state,
    mark_diagnostic_cache_open, and is_diagnostic_cache_stale
    need to be mocked to work with the real cache.

    Args:
        mock_client: Mock client to configure with cache accessor methods
        cache: Real DiagnosticCache instance to delegate to
    """
    from llm_lsp_cli.lsp.cache import FileState

    async def get_diagnostic_cache_state(uri: str) -> FileState:
        return await cache.get_file_state(uri)

    async def mark_diagnostic_cache_open(uri: str) -> None:
        await cache.on_did_open(uri)

    async def is_diagnostic_cache_stale(uri: str, mtime: float) -> bool:
        return await cache.is_stale(uri, mtime)

    mock_client.get_diagnostic_cache_state = get_diagnostic_cache_state
    mock_client.mark_diagnostic_cache_open = mark_diagnostic_cache_open
    mock_client.is_diagnostic_cache_stale = is_diagnostic_cache_stale


# Import for type hints only
from llm_lsp_cli.lsp.cache import DiagnosticCache  # noqa: E402


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """Create a temporary file for testing."""
    filepath = temp_dir / "test_file.py"
    filepath.touch()
    return filepath


@pytest.fixture
def sample_python_file(temp_dir: Path) -> Path:
    """Create a sample Python file for testing."""
    content = """
def hello():
    print("Hello, World!")

class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"

if __name__ == "__main__":
    hello()
"""
    filepath = temp_dir / "sample.py"
    _ = filepath.write_text(content)
    return filepath


@pytest.fixture(autouse=True)
def _reset_diagnostic_logger() -> Generator[None, None, None]:  # pyright: ignore[reportUnusedFunction]
    """Reset diagnostic logger state between tests for isolation.

    This fixture ensures that tests configuring the diagnostic logger
    (llm_lsp_cli.lsp.diagnostic) don't affect other tests.
    """
    yield
    # Cleanup after test
    diagnostic_logger = logging.getLogger("llm_lsp_cli.lsp.diagnostic")
    diagnostic_logger.handlers.clear()
    diagnostic_logger.setLevel(logging.NOTSET)
    diagnostic_logger.propagate = True


def is_pyright_langserver_installed() -> bool:
    """Check if pyright-langserver is installed and available."""
    try:
        import shutil

        path = shutil.which("pyright-langserver")
        return path is not None
    except Exception:
        return False


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with sample Python files for rename tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    src = workspace / "src"
    src.mkdir()

    # Create sample module
    _ = (src / "main.py").write_text('''
class OldClassName:
    def method(self):
        return OldClassName()

def standalone_func():
    obj = OldClassName()
    return obj
''')

    # Create second module with imports
    _ = (src / "utils.py").write_text('''
from main import OldClassName

def use_class():
    return OldClassName()
''')
    return workspace


@pytest.fixture
def sample_position() -> "Position":
    """Create a sample Position for testing rename operations."""
    from llm_lsp_cli.output.formatter import Position

    return Position(line=1, character=6)


@pytest.fixture
def xdg_test_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    """Set up isolated XDG environment for config tests.

    Yields:
        Path to the config directory (tmp_path / "config")
    """
    from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

    XdgPaths.reset_for_testing()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    yield config_dir


@pytest.fixture
def no_project_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable project config loading for tests that need isolated XDG config.

    The .llm-lsp-cli.yaml file in the project root (CWD during tests) can override
    test configs set up in XDG_CONFIG_HOME. This fixture disables project config
    loading to ensure test isolation.
    """
    from llm_lsp_cli.config.manager import ConfigManager

    # Return None for project config to prevent CWD config override
    monkeypatch.setattr(ConfigManager, "_load_project_config", classmethod(lambda cls: None))
