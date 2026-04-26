"""Pytest configuration and fixtures."""

import logging
import shutil
import tempfile
import typing
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> typing.Generator[Path, None, None]:
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
    filepath.write_text(content)
    return filepath


@pytest.fixture(autouse=True)
def _reset_diagnostic_logger() -> typing.Generator[None, None, None]:
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
    (src / "main.py").write_text('''
class OldClassName:
    def method(self):
        return OldClassName()

def standalone_func():
    obj = OldClassName()
    return obj
''')

    # Create second module with imports
    (src / "utils.py").write_text('''
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
