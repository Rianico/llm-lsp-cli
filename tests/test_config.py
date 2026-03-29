import pytest
from llm_lsp_cli.config import find_lang_server_executable, Config, ServerConfig
from pathlib import Path
import os
import shutil

@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    return config_dir

def test_find_lang_server_cli_path():
    """Test that the CLI path has the highest priority."""
    result = find_lang_server_executable("python", cli_path="/path/from/cli")
    assert result == "/path/from/cli"

def test_find_lang_server_config_path():
    """Test that the config file path is used."""
    config = Config(servers={"python": ServerConfig(langServerPath="/path/from/config")})
    result = find_lang_server_executable("python", config=config)
    assert result == "/path/from/config"

def test_find_lang_server_from_env(monkeypatch):
    """Test that the server is found in the PATH."""
    # Create a dummy executable and add it to PATH
    dummy_dir = Path.cwd() / "dummy_bin"
    dummy_dir.mkdir()
    dummy_executable = dummy_dir / "pylsp"
    dummy_executable.touch(mode=0o755)

    original_path = os.environ["PATH"]
    monkeypatch.setenv("PATH", str(dummy_dir) + os.pathsep + original_path)

    result = find_lang_server_executable("python")
    assert result == str(shutil.which("pylsp"))

    shutil.rmtree(dummy_dir)

def test_find_lang_server_not_found():
    """Test that an error is raised when the server is not found."""
    with pytest.raises(FileNotFoundError):
        find_lang_server_executable("non_existent_language")
