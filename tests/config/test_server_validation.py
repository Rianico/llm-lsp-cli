"""Tests for LSP server validation with stderr alerts and GitHub URL hints.

This module tests the server validation feature that:
1. Checks if LSP server executables exist before starting
2. Prints helpful alerts to stderr when servers are not found
3. Provides GitHub URLs for known language servers
4. Distinguishes between default config paths and custom user paths
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Mark all tests in this file as unit tests (no real LSP servers needed)
pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_server_in_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock shutil.which to find server in PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    server_exe = bin_dir / "mock-lsp-server"
    server_exe.write_text("#!/bin/sh\necho mock")
    server_exe.chmod(0o755)

    # Add to PATH
    current_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{bin_dir}:{current_path}")
    return server_exe


@pytest.fixture
def mock_server_not_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock shutil.which to return None (server not found)."""
    import shutil

    def mock_which(cmd: str, /) -> str | None:  # noqa: ARG001
        return None

    monkeypatch.setattr(shutil, "which", mock_which)


@pytest.fixture
def executable_file(tmp_path: Path) -> Path:
    """Create a temporary executable file."""
    exe = tmp_path / "custom-lsp-server"
    exe.write_text("#!/bin/sh\necho custom")
    exe.chmod(0o755)
    return exe


@pytest.fixture
def non_executable_file(tmp_path: Path) -> Path:
    """Create a non-executable file."""
    f = tmp_path / "non_executable"
    f.write_text("not executable")
    f.chmod(0o644)
    return f


@pytest.fixture
def captured_stderr(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture stderr output via typer.secho."""
    outputs: list[str] = []

    def mock_secho(message: str, **kwargs: object) -> None:
        if kwargs.get("err"):
            outputs.append(message)

    import typer

    monkeypatch.setattr(typer, "secho", mock_secho)
    return outputs


@pytest.fixture
def reset_xdg_paths() -> Generator[None, None, None]:
    """Reset XdgPaths singleton before and after each test."""
    from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

    XdgPaths.reset_for_testing()
    yield
    XdgPaths.reset_for_testing()


@pytest.fixture
def clean_config_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reset_xdg_paths: None  # noqa: ARG001
) -> Path:
    """Set up clean XDG config environment and return config dir path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))

    llm_config_dir = config_dir / "llm-lsp-cli"
    llm_config_dir.mkdir(parents=True)
    return llm_config_dir


# =============================================================================
# Test Classes
# =============================================================================


class TestServerFound:
    """Tests for when LSP server executable is found (happy path)."""

    def test_server_found_no_alert(
        self,
        mock_server_in_path: Path,  # noqa: ARG002
        captured_stderr: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When server is found, no stderr alert is printed."""
        from llm_lsp_cli.config.server_validation import validate_server_installed

        monkeypatch.setenv("MOCK_LSP_SERVER_PATH", str(mock_server_in_path))
        result = validate_server_installed("mock-lsp-server")

        assert result is not None
        assert len(captured_stderr) == 0

    def test_server_found_returns_path(
        self, mock_server_in_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When server is found, resolved path is returned."""
        from llm_lsp_cli.config.server_validation import validate_server_installed

        result = validate_server_installed("mock-lsp-server")

        assert result is not None
        assert "mock-lsp-server" in result or Path(result).name == "mock-lsp-server"

    def test_rust_analyzer_found_no_alert(
        self, mock_server_in_path: Path, captured_stderr: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rust analyzer found in PATH results in no alert."""
        from llm_lsp_cli.config.server_validation import validate_server_installed

        monkeypatch.setenv("MOCK_SERVER", "rust-analyzer")
        result = validate_server_installed("rust-analyzer", language="rust")

        assert result is not None
        assert len(captured_stderr) == 0


class TestServerNotFound:
    """Tests for when LSP server executable is not found."""

    def test_server_not_found_shows_alert(
        self,
        mock_server_not_in_path: None,  # noqa: ARG002
        captured_stderr: list[str],
    ) -> None:
        """When server is not found, alert is printed to stderr."""
        from llm_lsp_cli.config.server_validation import (
            ServerNotFoundError,
            validate_server_installed,
        )

        with pytest.raises(ServerNotFoundError):
            validate_server_installed("basedpyright-langserver", language="python")

        assert len(captured_stderr) > 0
        assert "basedpyright-langserver" in captured_stderr[0]

    @pytest.mark.parametrize(
        "server,language,expected_url",
        [
            ("basedpyright-langserver", "python", "https://github.com/DetachHead/basedpyright"),
            ("rust-analyzer", "rust", "https://github.com/rust-lang/rust-analyzer"),
            (
                "typescript-language-server",
                "typescript",
                "https://github.com/typescript-language-server/typescript-language-server",
            ),
            ("gopls", "go", "https://github.com/golang/tools/tree/master/gopls"),
        ],
    )
    def test_alert_includes_github_url(
        self,
        mock_server_not_in_path: None,  # noqa: ARG002
        captured_stderr: list[str],
        server: str,
        language: str,
        expected_url: str,
    ) -> None:
        """Alert includes correct GitHub URL for known servers."""
        from llm_lsp_cli.config.server_validation import (
            ServerNotFoundError,
            validate_server_installed,
        )

        with pytest.raises(ServerNotFoundError):
            validate_server_installed(server, language=language)

        stderr_output = "\n".join(captured_stderr)
        assert expected_url in stderr_output

    def test_alert_prints_before_exception(
        self,
        mock_server_not_in_path: None,  # noqa: ARG002
        captured_stderr: list[str],
    ) -> None:
        """Alert is printed BEFORE the exception is raised."""
        from llm_lsp_cli.config.server_validation import (
            ServerNotFoundError,
            validate_server_installed,
        )

        with pytest.raises(ServerNotFoundError):
            validate_server_installed("basedpyright-langserver", language="python")

        # Alert should have been printed (stderr captured)
        assert len(captured_stderr) > 0


class TestCustomServerPath:
    """Tests for custom server paths provided by user."""

    def test_custom_path_found_no_alert(
        self,
        executable_file: Path,
        captured_stderr: list[str],
    ) -> None:
        """Custom path that exists works without alert."""
        from llm_lsp_cli.config.server_validation import validate_server_installed

        result = validate_server_installed(str(executable_file), is_custom_path=True)

        assert result == str(executable_file.resolve())
        assert len(captured_stderr) == 0

    def test_custom_path_not_found_shows_error_no_github(
        self,
        tmp_path: Path,  # noqa: ARG002
        captured_stderr: list[str],
    ) -> None:
        """Custom path not found shows error without GitHub URL."""
        from llm_lsp_cli.config.server_validation import (
            ServerNotFoundError,
            validate_server_installed,
        )

        nonexistent = "/nonexistent/path/to/server"

        with pytest.raises(ServerNotFoundError):
            validate_server_installed(nonexistent, is_custom_path=True)

        stderr_output = "\n".join(captured_stderr)
        assert "Custom server path not found" in stderr_output
        # Should NOT include GitHub URL for custom paths
        assert "github.com" not in stderr_output

    def test_custom_path_relative_resolves(
        self,
        tmp_path: Path,
        captured_stderr: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Relative custom path resolves correctly."""
        from llm_lsp_cli.config.server_validation import validate_server_installed

        # Create executable in subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        server_exe = subdir / "my-server"
        server_exe.write_text("#!/bin/sh\necho test")
        server_exe.chmod(0o755)

        monkeypatch.chdir(tmp_path)

        result = validate_server_installed("./subdir/my-server", is_custom_path=True)

        assert len(captured_stderr) == 0
        assert Path(result).is_absolute()

    def test_custom_path_with_tilde_expands(
        self,
        tmp_path: Path,
        captured_stderr: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tilde in custom path expands correctly."""
        from llm_lsp_cli.config.server_validation import validate_server_installed

        home = tmp_path / "user_home"
        home.mkdir()
        bin_dir = home / "bin"
        bin_dir.mkdir()
        server_exe = bin_dir / "server"
        server_exe.write_text("#!/bin/sh\necho test")
        server_exe.chmod(0o755)

        monkeypatch.setenv("HOME", str(home))

        result = validate_server_installed("~/bin/server", is_custom_path=True)

        assert len(captured_stderr) == 0
        assert result == str(server_exe)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unknown_language_no_github_url(
        self,
        mock_server_not_in_path: None,  # noqa: ARG002
        captured_stderr: list[str],
    ) -> None:
        """Unknown language has no GitHub URL suggestion."""
        from llm_lsp_cli.config.server_validation import (
            ServerNotFoundError,
            validate_server_installed,
        )

        with pytest.raises(ServerNotFoundError):
            validate_server_installed("some-unknown-server", language="unknown-lang")

        stderr_output = "\n".join(captured_stderr)
        # No GitHub URL for unknown servers
        assert "github.com" not in stderr_output

    def test_non_executable_file_shows_permission_error(
        self,
        non_executable_file: Path,
        captured_stderr: list[str],
    ) -> None:
        """Non-executable file shows permission error in alert."""
        from llm_lsp_cli.config.server_validation import (
            ServerNotFoundError,
            validate_server_installed,
        )

        with pytest.raises(ServerNotFoundError):
            validate_server_installed(str(non_executable_file), is_custom_path=True)

        stderr_output = "\n".join(captured_stderr)
        assert "not executable" in stderr_output.lower() or "permission" in stderr_output.lower()

    def test_empty_command_raises_validation_error(
        self,
        captured_stderr: list[str],  # noqa: ARG002
    ) -> None:
        """Empty command raises validation error."""
        from llm_lsp_cli.config.server_validation import (
            ServerValidationError,
            validate_server_installed,
        )

        with pytest.raises(ServerValidationError):
            validate_server_installed("")


class TestConfigManagerIntegration:
    """Tests for ConfigManager.resolve_server_command() integration."""

    def test_resolve_validates_default_server(
        self,
        clean_config_env: Path,
        mock_server_not_in_path: None,  # noqa: ARG002
        captured_stderr: list[str],
    ) -> None:
        """ConfigManager.resolve_server_command validates default servers."""
        from llm_lsp_cli.config.manager import ConfigManager

        # Create config with python language
        config_file = clean_config_env / "config.yaml"
        config_file.write_text("""
languages:
  python:
    command: basedpyright-langserver
    args: ["--stdio"]
""")

        with pytest.raises(FileNotFoundError):
            ConfigManager.resolve_server_command("python")

        # Should have printed alert with GitHub URL
        stderr_output = "\n".join(captured_stderr)
        assert "basedpyright-langserver" in stderr_output
        assert "github.com" in stderr_output

    def test_resolve_with_cli_arg_validates_custom_path(
        self,
        clean_config_env: Path,  # noqa: ARG002
        captured_stderr: list[str],
    ) -> None:
        """CLI arg for custom path validates as custom path."""
        from llm_lsp_cli.config.manager import ConfigManager

        nonexistent = "/nonexistent/custom-server"

        with pytest.raises(FileNotFoundError):
            ConfigManager.resolve_server_command("python", cli_arg=nonexistent)

        # Should show custom path error without GitHub URL
        stderr_output = "\n".join(captured_stderr)
        assert "Custom server path not found" in stderr_output or nonexistent in stderr_output
        # Should NOT have GitHub URL
        assert "github.com" not in stderr_output


class TestGetInstallUrl:
    """Tests for get_install_url utility function."""

    @pytest.mark.parametrize(
        "server,expected_url",
        [
            ("basedpyright-langserver", "https://github.com/DetachHead/basedpyright"),
            ("rust-analyzer", "https://github.com/rust-lang/rust-analyzer"),
            ("gopls", "https://github.com/golang/tools/tree/master/gopls"),
            ("unknown-server-xyz", None),
        ],
    )
    def test_get_install_url(self, server: str, expected_url: str | None) -> None:
        """Get install URL returns correct value for known/unknown servers."""
        from llm_lsp_cli.config.server_validation import get_install_url

        assert get_install_url(server) == expected_url


class TestPrintServerNotFoundAlert:
    """Tests for print_server_not_found_alert function."""

    def test_print_alert_includes_server_name(
        self, captured_stderr: list[str]
    ) -> None:
        """Alert includes the server name."""
        from llm_lsp_cli.config.server_validation import print_server_not_found_alert

        print_server_not_found_alert("test-server-name")

        stderr_output = "\n".join(captured_stderr)
        assert "test-server-name" in stderr_output

    def test_print_alert_custom_path_no_github(
        self, captured_stderr: list[str]
    ) -> None:
        """Alert for custom path does not include GitHub URL."""
        from llm_lsp_cli.config.server_validation import print_server_not_found_alert

        print_server_not_found_alert("/custom/path/server", is_custom=True)

        stderr_output = "\n".join(captured_stderr)
        assert "github.com" not in stderr_output

    def test_print_alert_default_path_with_github(
        self, captured_stderr: list[str]
    ) -> None:
        """Alert for default path includes GitHub URL."""
        from llm_lsp_cli.config.server_validation import print_server_not_found_alert

        print_server_not_found_alert("basedpyright-langserver", is_custom=False)

        stderr_output = "\n".join(captured_stderr)
        assert "github.com" in stderr_output
        assert "DetachHead/basedpyright" in stderr_output
