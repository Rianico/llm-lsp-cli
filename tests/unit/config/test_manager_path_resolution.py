"""Integration tests for ConfigManager.resolve_server_command() with ServerPathResolver."""

import os
from pathlib import Path

import pytest

from llm_lsp_cli.config.manager import ConfigManager
from llm_lsp_cli.infrastructure.config.exceptions import ServerNotFoundError
from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths


@pytest.fixture(autouse=True)
def reset_xdg_paths() -> None:
    """Reset XdgPaths singleton before each test."""
    XdgPaths.reset_for_testing()


@pytest.fixture
def mock_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Mock HOME environment variable."""
    home = tmp_path / "mock_home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def clean_config_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up clean XDG config environment."""
    # Reset singleton first
    XdgPaths.reset_for_testing()

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))


class TestConfigManagerBackwardCompatibility:
    """Tests for backward compatibility with existing PATH-based configs."""

    @pytest.fixture
    def mock_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create a mock PATH directory."""
        path_dir = tmp_path / "mock_bin"
        path_dir.mkdir()
        current_path = os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", f"{path_dir}:{current_path}")
        return path_dir

    def test_resolve_with_simple_command_in_path(
        self, mock_path: Path, clean_config_env: None
    ) -> None:
        """BC-01: Simple command in PATH returns resolved path."""
        # Create a fake server in mock PATH
        server_exe = mock_path / "test-server"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        # Create minimal config
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text("""
languages:
  testlang:
    command: test-server
    args: ["--stdio"]
""")

        resolved_cmd, args = ConfigManager.resolve_server_command("testlang")
        assert Path(resolved_cmd).name == "test-server"
        assert args == ["--stdio"]

    def test_resolve_cli_override_simple(self, mock_path: Path, clean_config_env: None) -> None:
        """BC-03: CLI override with simple command uses PATH."""
        # Create fake 'echo' in mock PATH
        echo_exe = mock_path / "echo"
        echo_exe.write_text("#!/bin/sh\n")
        echo_exe.chmod(0o755)

        resolved_cmd, args = ConfigManager.resolve_server_command("python", cli_arg="echo")
        assert Path(resolved_cmd).name == "echo"
        assert args == []


class TestConfigManagerNewFunctionality:
    """Tests for new path resolution functionality."""

    def test_resolve_with_tilde_path(self, mock_home: Path, clean_config_env: None) -> None:
        """NEW-01: Tilde path in config returns expanded absolute path."""
        # Create executable at tilde path (~/.local/bin/server)
        bin_dir = mock_home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        server_exe = bin_dir / "server"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        # Create config with tilde command - use custom language to avoid default fallback
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text("""
languages:
  mytestlang:
    command: "~/.local/bin/server"
    args: ["--stdio"]
""")

        resolved_cmd, args = ConfigManager.resolve_server_command("mytestlang")
        assert resolved_cmd == str(server_exe)
        assert Path(resolved_cmd).is_absolute()
        assert args == ["--stdio"]

    def test_resolve_with_env_var_path(
        self, mock_home: Path, clean_config_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NEW-02: Environment variable path in config returns expanded path."""
        # Set up env var and executable
        mason_bin = mock_home / "mason" / "bin"
        mason_bin.mkdir(parents=True)
        monkeypatch.setenv("MASON_BIN", str(mason_bin))
        server_exe = mason_bin / "pyright-langserver"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        # Create config with env var command - use custom language
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text("""
languages:
  mytestlang:
    command: "$MASON_BIN/pyright-langserver"
    args: ["--stdio"]
""")

        resolved_cmd, args = ConfigManager.resolve_server_command("mytestlang")
        assert resolved_cmd == str(server_exe)
        assert args == ["--stdio"]

    def test_resolve_with_absolute_path(self, clean_config_env: None, tmp_path: Path) -> None:
        """NEW-03: Absolute path in config returns absolute path."""
        # Create executable at absolute path
        server_exe = tmp_path / "usr" / "local" / "bin" / "server"
        server_exe.parent.mkdir(parents=True)
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        # Create config with absolute path - use custom language
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text(f"""
languages:
  mytestlang:
    command: "{server_exe}"
    args: ["--stdio"]
""")

        resolved_cmd, args = ConfigManager.resolve_server_command("mytestlang")
        assert resolved_cmd == str(server_exe.resolve())
        assert args == ["--stdio"]

    def test_resolve_with_braced_env_var(
        self, mock_home: Path, clean_config_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NEW-04: Braced environment variable path works correctly."""
        # Set up env var and executable
        bin_dir = mock_home / "bin"
        bin_dir.mkdir()
        monkeypatch.setenv("HOME", str(mock_home))
        server_exe = bin_dir / "server"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        # Create config with braced env var - use custom language
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text("""
languages:
  mytestlang:
    command: "${HOME}/bin/server"
    args: ["--stdio"]
""")

        resolved_cmd, args = ConfigManager.resolve_server_command("mytestlang")
        assert resolved_cmd == str(server_exe)
        assert args == ["--stdio"]


class TestConfigManagerErrorPropagation:
    """Tests for error propagation from ServerPathResolver."""

    def test_resolve_nonexistent_path_file_not_found(
        self, mock_home: Path, clean_config_env: None
    ) -> None:
        """ERR-PROP-01: Non-existent tilde path raises FileNotFoundError."""
        # Create config with non-existent tilde path - use custom language
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text("""
languages:
  mytestlang:
    command: "~/.nonexistent/server"
    args: ["--stdio"]
""")

        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager.resolve_server_command("mytestlang")

        # Check that ServerNotFoundError is the cause
        assert isinstance(exc_info.value.__cause__, ServerNotFoundError)
        assert "~/.nonexistent/server" in str(exc_info.value)

    def test_resolve_non_executable_file_not_found(
        self, clean_config_env: None, tmp_path: Path
    ) -> None:
        """ERR-PROP-02: Non-executable file raises FileNotFoundError."""
        # Create non-executable file
        server_file = tmp_path / "not_executable"
        server_file.write_text("not executable")
        server_file.chmod(0o644)

        # Create config pointing to non-executable - use custom language
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text(f"""
languages:
  mytestlang:
    command: "{server_file}"
    args: ["--stdio"]
""")

        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager.resolve_server_command("mytestlang")

        assert isinstance(exc_info.value.__cause__, ServerNotFoundError)

    def test_resolve_language_not_configured(self, clean_config_env: None) -> None:
        """ERR-PROP-03: Unconfigured language raises FileNotFoundError with helpful message."""
        # Create empty config
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
        llm_config_dir = config_dir / "llm-lsp-cli"
        llm_config_dir.mkdir(parents=True)
        config_file = llm_config_dir / "config.yaml"
        config_file.write_text("""
languages: {}
""")

        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager.resolve_server_command("unknown-lang-xyz")

        assert "unknown-lang-xyz" in str(exc_info.value)
        assert "Language server" in str(exc_info.value)
