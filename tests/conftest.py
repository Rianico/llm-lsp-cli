"""Pytest configuration and fixtures."""

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


def is_pyright_langserver_installed() -> bool:
    """Check if pyright-langserver is installed and available."""
    try:
        # Check if the command exists using shutil.which
        import shutil
        path = shutil.which("pyright-langserver")
        return path is not None
    except Exception:
        return False


@pytest.fixture
def pyright_langserver_available() -> bool:
    """Fixture that returns True if pyright-langserver is installed."""
    return is_pyright_langserver_installed()
