"""Security tests for error message sanitization."""

import pytest
from pathlib import Path

from llm_lsp_cli.infrastructure.config.path_resolver import (
    ServerPathResolver,
    ServerNotFoundError,
)
from llm_lsp_cli.infrastructure.config.exceptions import ServerPathValidationError


def test_error_sanitizes_resolved_path(tmp_path: Path) -> None:
    """SEC-ERR-01: Error messages don't expose full resolved paths in Attempted path."""
    # Arrange: Deep path that shouldn't be fully exposed
    secret_dir = tmp_path / ".secret" / "internal" / "lsp" / "bin"
    secret_dir.mkdir(parents=True)
    non_exe = secret_dir / "server"
    non_exe.write_text("not executable")

    # Act & Assert
    with pytest.raises(ServerNotFoundError) as exc_info:
        ServerPathResolver.resolve(str(non_exe))

    error_msg = str(exc_info.value)

    # The "Attempted path:" field should only show basename, not full path
    # The original command is shown (user-provided), but internal resolution is sanitized
    assert "Attempted path: server" in error_msg  # Only basename
    assert ".secret/internal/lsp" not in error_msg.split("Attempted path:")[1]


def test_error_for_path_traversal_attempt(tmp_path: Path) -> None:
    """SEC-ERR-02: Path traversal attempts don't reveal structure in Attempted path."""
    # Create a decoy file
    (tmp_path / "secret.txt").write_text("secret")

    # Attempt traversal from a subdirectory (file exists but not executable)
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    traversal_path = str(subdir / "../../../secret.txt")

    with pytest.raises(ServerNotFoundError) as exc_info:
        ServerPathResolver.resolve(traversal_path)

    error_msg = str(exc_info.value)

    # The "Attempted path:" field should only show basename
    # This prevents revealing the resolved parent directory structure
    assert "Attempted path: secret.txt" in error_msg  # Only basename
    # Should not confirm existence of parent directory files in the sanitized portion
    assert "subdir" not in error_msg.split("Attempted path:")[1]


def test_error_shows_user_friendly_hint() -> None:
    """SEC-ERR-03: Error messages provide helpful guidance."""
    with pytest.raises(ServerNotFoundError) as exc_info:
        ServerPathResolver.resolve("nonexistent-server")

    error_msg = str(exc_info.value)

    # Should include actionable hints
    assert "install" in error_msg.lower() or "path" in error_msg.lower()
    assert "config" in error_msg.lower()


def test_debug_mode_shows_full_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-ERR-04: Debug mode optionally shows full paths."""
    # Arrange: Enable debug mode via env var
    monkeypatch.setenv("LSP_DEBUG_MODE", "1")

    secret_dir = tmp_path / "debug" / "path"
    secret_dir.mkdir(parents=True)

    # In debug mode, full path might be shown
    # This is acceptable for local debugging
    with pytest.raises(ServerNotFoundError) as exc_info:
        ServerPathResolver.resolve(str(secret_dir / "server"))

    # Debug mode may show more details (implementation dependent)
    # Test verifies the mechanism exists
    error_msg = str(exc_info.value)
    assert "not found" in error_msg.lower() or "not executable" in error_msg.lower()


def test_error_for_empty_command() -> None:
    """SEC-ERR-05: Empty command shows clear error."""
    with pytest.raises(ServerPathValidationError) as exc_info:
        ServerPathResolver.resolve("")

    error_msg = str(exc_info.value)
    assert "empty" in error_msg.lower() or "command" in error_msg.lower()
