"""Unit tests for ServerPathResolver and ServerNotFoundError."""

import os
from pathlib import Path

import pytest

from llm_lsp_cli.infrastructure.config.exceptions import (
    ConfigError,
    ServerNotFoundError,
)
from llm_lsp_cli.infrastructure.config.path_resolver import ServerPathResolver


@pytest.fixture
def mock_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Mock HOME environment variable."""
    home = tmp_path / "mock_home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


class TestServerPathResolverExpand:
    """Tests for ServerPathResolver._expand_path()."""

    def test_expand_tilde_home(self, mock_home: Path) -> None:
        """EXP-01: Expand ~/path to home directory."""
        result = ServerPathResolver._expand_path("~/.local/bin/server")
        assert result == str(mock_home / ".local" / "bin" / "server")

    def test_expand_tilde_user(self, mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EXP-02: Expand ~user/path (simplified - same as home for test)."""
        # Note: os.path.expanduser('~otheruser') behavior depends on system
        # We test that tilde expansion is attempted
        result = ServerPathResolver._expand_path("~/bin/server")
        assert result.startswith(str(mock_home))

    def test_expand_env_var_simple(self, mock_home: Path) -> None:
        """EXP-03: Expand $VAR syntax."""
        result = ServerPathResolver._expand_path("$HOME/bin/server")
        assert result == str(mock_home / "bin" / "server")

    def test_expand_env_var_braced(self, mock_home: Path) -> None:
        """EXP-04: Expand ${VAR} syntax."""
        result = ServerPathResolver._expand_path("${HOME}/bin/server")
        assert result == str(mock_home / "bin" / "server")

    def test_expand_env_var_multiple(
        self, mock_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EXP-05: Expand multiple environment variables."""
        monkeypatch.setenv("PREFIX", "/usr/local")
        monkeypatch.setenv("SERVER", "pyright")
        result = ServerPathResolver._expand_path("$PREFIX/bin/$SERVER")
        assert result == "/usr/local/bin/pyright"

    def test_expand_combined_tilde_env(
        self, mock_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """EXP-06: Expand tilde combined with environment variables."""
        monkeypatch.setenv("SUBDIR", "subdir")
        result = ServerPathResolver._expand_path("~/$SUBDIR/server")
        assert result == str(mock_home / "subdir" / "server")

    def test_expand_no_expansion_needed(self) -> None:
        """EXP-07: Absolute paths pass through unchanged."""
        result = ServerPathResolver._expand_path("/usr/bin/server")
        assert result == "/usr/bin/server"

    def test_expand_unset_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """EXP-08: Unset environment variables are preserved (not expanded)."""
        # Ensure UNSET_VAR is not set
        monkeypatch.delenv("UNSET_VAR", raising=False)
        result = ServerPathResolver._expand_path("$UNSET_VAR/bin/server")
        # os.path.expandvars preserves unrecognized variables
        assert result == "$UNSET_VAR/bin/server"


class TestServerPathResolverIsPathLike:
    """Tests for ServerPathResolver._is_path_like()."""

    def test_is_path_like_absolute(self) -> None:
        """PATH-01: Absolute paths are path-like."""
        assert ServerPathResolver._is_path_like("/usr/bin/server", "/usr/bin/server") is True

    def test_is_path_like_tilde(self, mock_home: Path) -> None:
        """PATH-02: Tilde paths are path-like."""
        expanded = str(mock_home / ".local" / "bin" / "server")
        assert ServerPathResolver._is_path_like("~/.local/bin/server", expanded) is True

    def test_is_path_like_env_var(self, mock_home: Path) -> None:
        """PATH-03: Environment variable paths are path-like."""
        expanded = str(mock_home / "bin" / "server")
        assert ServerPathResolver._is_path_like("$HOME/bin/server", expanded) is True

    def test_is_path_like_relative_explicit(self) -> None:
        """PATH-04: Relative paths with ./ are path-like."""
        assert ServerPathResolver._is_path_like("./bin/server", "./bin/server") is True

    def test_is_path_like_relative_parent(self) -> None:
        """PATH-05: Relative paths with ../ are path-like."""
        assert ServerPathResolver._is_path_like("../bin/server", "../bin/server") is True

    def test_is_path_like_simple_command(self) -> None:
        """PATH-06: Simple command names are NOT path-like."""
        assert ServerPathResolver._is_path_like("pyright-langserver", "pyright-langserver") is False

    def test_is_path_like_command_with_args(self) -> None:
        """PATH-07: Commands with arguments are NOT path-like."""
        # Note: This tests that "node --stdio" is not considered path-like
        # The space doesn't count as a path separator
        assert ServerPathResolver._is_path_like("node --stdio", "node --stdio") is False


class TestServerPathResolverValidateExecutable:
    """Tests for ServerPathResolver._validate_executable()."""

    @pytest.fixture
    def executable_file(self, tmp_path: Path) -> Path:
        """Create an executable file."""
        exe = tmp_path / "fake_server"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        return exe

    @pytest.fixture
    def non_executable_file(self, tmp_path: Path) -> Path:
        """Create a non-executable file."""
        f = tmp_path / "not_executable"
        f.write_text("not executable")
        f.chmod(0o644)
        return f

    def test_validate_executable_exists_and_executable(self, executable_file: Path) -> None:
        """VAL-01: Valid executable returns resolved path."""
        result = ServerPathResolver._validate_executable(str(executable_file), "fake_server")
        assert Path(result).exists()
        assert os.access(result, os.X_OK)

    def test_validate_executable_not_exists(self, tmp_path: Path) -> None:
        """VAL-02: Non-existent path raises ServerNotFoundError."""
        nonexistent = tmp_path / "nonexistent" / "server"
        with pytest.raises(ServerNotFoundError) as exc_info:
            ServerPathResolver._validate_executable(str(nonexistent), "~/.local/bin/server")
        # Error message should only show basename, not full path (security)
        assert "Attempted path: server" in str(exc_info.value)

    def test_validate_executable_not_file(self, tmp_path: Path) -> None:
        """VAL-03: Directory raises ServerNotFoundError."""
        directory = tmp_path / "server_dir"
        directory.mkdir()
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver._validate_executable(str(directory), "/path/to/dir")

    def test_validate_executable_not_executable(self, non_executable_file: Path) -> None:
        """VAL-04: Non-executable file raises ServerNotFoundError."""
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver._validate_executable(
                str(non_executable_file), "/path/to/not_executable"
            )

    def test_validate_executable_symlink_valid(self, executable_file: Path, tmp_path: Path) -> None:
        """VAL-05: Valid symlink to executable returns resolved path."""
        link = tmp_path / "link_to_server"
        link.symlink_to(executable_file)
        result = ServerPathResolver._validate_executable(str(link), "~/link")
        assert Path(result).exists()

    def test_validate_executable_symlink_broken(self, tmp_path: Path) -> None:
        """VAL-06: Broken symlink raises ServerNotFoundError."""
        target = tmp_path / "nonexistent_target"
        link = tmp_path / "broken_link"
        link.symlink_to(target)
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver._validate_executable(str(link), "~/broken")

    def test_validate_executable_error_message_includes_path(self, tmp_path: Path) -> None:
        """VAL-07: Error message contains attempted path."""
        nonexistent = str(tmp_path / "nonexistent" / "server")
        with pytest.raises(ServerNotFoundError) as exc_info:
            ServerPathResolver._validate_executable(nonexistent, "~/.local/bin/server")
        error_msg = str(exc_info.value)
        assert "~/.local/bin/server" in error_msg or "server" in error_msg


class TestServerPathResolverResolve:
    """Integration tests for ServerPathResolver.resolve()."""

    @pytest.fixture
    def mock_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create a mock PATH directory."""
        path_dir = tmp_path / "mock_bin"
        path_dir.mkdir()
        current_path = os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", f"{path_dir}:{current_path}")
        return path_dir

    def test_resolve_simple_command_in_path(self, mock_path: Path) -> None:
        """RES-01: Simple command in PATH returns resolved path."""
        # Create a fake 'echo' in mock PATH
        echo_exe = mock_path / "echo"
        echo_exe.write_text("#!/bin/sh\n")
        echo_exe.chmod(0o755)

        result = ServerPathResolver.resolve("echo")
        assert Path(result).name == "echo"
        assert os.access(result, os.X_OK)

    def test_resolve_absolute_path(self) -> None:
        """RES-02: Absolute path to existing executable returns absolute path."""
        # Use a known system executable
        result = ServerPathResolver.resolve("/bin/sh")
        assert result == "/bin/sh"

    def test_resolve_tilde_path(self, mock_home: Path) -> None:
        """RES-03: Tilde path to executable returns expanded path."""
        bin_dir = mock_home / "bin"
        bin_dir.mkdir(parents=True)
        server_exe = bin_dir / "server"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        result = ServerPathResolver.resolve("~/bin/server")
        assert result == str(server_exe)

    def test_resolve_env_var_path(self, mock_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """RES-04: Environment variable path returns expanded path."""
        monkeypatch.setenv("TEST_BIN", str(mock_home / "bin"))
        bin_dir = mock_home / "bin"
        bin_dir.mkdir(parents=True)
        server_exe = bin_dir / "server"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        result = ServerPathResolver.resolve("$TEST_BIN/server")
        assert result == str(server_exe)

    def test_resolve_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """RES-05: Relative path to executable returns absolute path."""
        # Change to tmp_path for relative path test
        monkeypatch.chdir(tmp_path)
        test_exe = tmp_path / "test_server"
        test_exe.write_text("#!/bin/sh\n")
        test_exe.chmod(0o755)

        result = ServerPathResolver.resolve("./test_server")
        assert Path(result).is_absolute()
        assert result == str(test_exe)

    def test_resolve_nonexistent_absolute(self, tmp_path: Path) -> None:
        """RES-06: Non-existent absolute path raises ServerNotFoundError."""
        nonexistent = tmp_path / "nonexistent" / "server"
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver.resolve(str(nonexistent))

    def test_resolve_nonexistent_tilde(self, mock_home: Path) -> None:
        """RES-07: Non-existent tilde path raises ServerNotFoundError."""
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver.resolve("~/nonexistent/server")

    def test_resolve_nonexistent_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RES-08: Non-existent env var path raises ServerNotFoundError."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver.resolve("$NONEXISTENT_VAR/server")

    def test_resolve_not_executable(self, tmp_path: Path) -> None:
        """RES-09: Non-executable file raises ServerNotFoundError."""
        not_exe = tmp_path / "not_executable"
        not_exe.write_text("not executable")
        not_exe.chmod(0o644)

        with pytest.raises(ServerNotFoundError):
            ServerPathResolver.resolve(str(not_exe))

    def test_resolve_command_not_in_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RES-10: Simple command not in PATH raises ServerNotFoundError."""
        # Use a guaranteed unique command name
        with pytest.raises(ServerNotFoundError):
            ServerPathResolver.resolve("nonexistent-command-xyz-123-abc")


class TestServerNotFoundError:
    """Tests for ServerNotFoundError exception."""

    def test_error_message_with_resolved_path(self, tmp_path: Path) -> None:
        """ERR-01: Error message contains resolved path and causes."""
        nonexistent = str(tmp_path / "nonexistent" / "server")
        try:
            ServerPathResolver.resolve(nonexistent)
            assert False, "Should have raised ServerNotFoundError"
        except ServerNotFoundError as err:
            error_msg = str(err)
            assert "not found" in error_msg.lower()
            assert "nonexistent" in error_msg

    def test_error_message_without_resolved_path(self) -> None:
        """ERR-02: Error message for simple command not found."""
        try:
            ServerPathResolver.resolve("nonexistent-command-xyz")
            assert False, "Should have raised ServerNotFoundError"
        except ServerNotFoundError as err:
            error_msg = str(err)
            assert "not found" in error_msg.lower()
            assert "nonexistent-command-xyz" in error_msg

    def test_error_is_config_error_subclass(self) -> None:
        """ERR-03: ServerNotFoundError is a ConfigError subclass."""
        assert issubclass(ServerNotFoundError, ConfigError)

        try:
            ServerPathResolver.resolve("nonexistent-command-xyz")
            assert False, "Should have raised ServerNotFoundError"
        except ServerNotFoundError as err:
            assert isinstance(err, ConfigError)


class TestServerPathResolverEdgeCases:
    """Edge case tests for ServerPathResolver."""

    def test_expand_env_var_with_special_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """EDGE-01: Environment variables with underscores expand correctly."""
        monkeypatch.setenv("VAR_WITH_UNDERSCORE", "/path/with/underscore")
        result = ServerPathResolver._expand_path("$VAR_WITH_UNDERSCORE/bin")
        assert result == "/path/with/underscore/bin"

    def test_expand_env_var_shell_default_not_supported(self) -> None:
        """EDGE-02: Shell default syntax ${VAR:-default} is NOT supported."""
        # This is a documented limitation - the raw string is preserved
        result = ServerPathResolver._expand_path("${UNSET_VAR:-default}")
        # expandvars leaves the syntax intact if variable is unset
        assert "${UNSET_VAR:-default}" in result or result.startswith("$")

    def test_resolve_empty_command(self) -> None:
        """EDGE-04: Empty string command raises ServerPathValidationError."""
        from llm_lsp_cli.infrastructure.config.exceptions import ServerPathValidationError

        with pytest.raises(ServerPathValidationError):
            ServerPathResolver.resolve("")

    def test_resolve_whitespace_command(self) -> None:
        """EDGE-05: Whitespace-only command raises ServerPathValidationError."""
        from llm_lsp_cli.infrastructure.config.exceptions import ServerPathValidationError

        with pytest.raises(ServerPathValidationError):
            ServerPathResolver.resolve("   ")

    def test_resolve_command_with_spaces_in_path(self, tmp_path: Path) -> None:
        """EDGE-06: Path with spaces works correctly."""
        space_dir = tmp_path / "path with spaces"
        space_dir.mkdir()
        server_exe = space_dir / "server"
        server_exe.write_text("#!/bin/sh\n")
        server_exe.chmod(0o755)

        result = ServerPathResolver.resolve(str(server_exe))
        assert "path with spaces" in result
        assert Path(result).exists()
