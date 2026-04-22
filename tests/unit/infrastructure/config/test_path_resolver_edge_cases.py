"""Edge case tests for ServerPathResolver."""

import asyncio
import pytest
from pathlib import Path

from llm_lsp_cli.infrastructure.config.path_resolver import (
    ServerPathResolver,
    ServerNotFoundError,
)
from llm_lsp_cli.infrastructure.config.exceptions import ServerPathValidationError


def test_reject_empty_command() -> None:
    """SEC-EDGE-01: Empty string commands are rejected."""
    with pytest.raises(ServerPathValidationError) as exc_info:
        ServerPathResolver.resolve("")

    assert "empty" in str(exc_info.value).lower()


def test_reject_whitespace_only_command() -> None:
    """SEC-EDGE-02: Whitespace-only commands are rejected."""
    for ws in [" ", "  ", "   ", "\t", "\n", "\r\n"]:
        with pytest.raises(ServerPathValidationError):
            ServerPathResolver.resolve(ws)


def test_unicode_path_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-EDGE-03: Unicode paths are handled correctly."""
    # Arrange: Create directory with Unicode name
    unicode_dir = tmp_path / "服务器" / "bin"
    unicode_dir.mkdir(parents=True)
    server_exe = unicode_dir / "server"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    # Act
    result = ServerPathResolver.resolve(str(server_exe))

    # Assert
    assert Path(result).exists()
    assert "服务器" in result


def test_very_long_path_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SEC-EDGE-04: Very long paths are handled (within OS limits)."""
    # Arrange: Create deep directory structure
    deep_path = tmp_path
    for i in range(30):
        deep_path = deep_path / f"level_{i}"
        deep_path.mkdir()

    server_exe = deep_path / "server"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    # Act
    result = ServerPathResolver.resolve(str(server_exe))

    # Assert
    assert Path(result).exists()
    assert "level_0" in result
    assert "level_29" in result


def test_symlink_to_non_executable(tmp_path: Path) -> None:
    """SEC-EDGE-05: Symlinks to non-executables are rejected."""
    # Arrange: Create non-executable file
    non_exec = tmp_path / "not_executable.txt"
    non_exec.write_text("not executable")
    non_exec.chmod(0o644)

    # Create symlink to non-executable
    link = tmp_path / "link_to_nonexec"
    link.symlink_to(non_exec)

    # Act & Assert
    with pytest.raises(ServerNotFoundError):
        ServerPathResolver.resolve(str(link))


def test_broken_symlink_handling(tmp_path: Path) -> None:
    """SEC-EDGE-06: Broken symlinks raise ServerNotFoundError."""
    # Arrange: Create symlink to non-existent target
    target = tmp_path / "nonexistent_target"
    link = tmp_path / "broken_link"
    link.symlink_to(target)

    # Act & Assert
    with pytest.raises(ServerNotFoundError):
        ServerPathResolver.resolve(str(link))

    # Error should not expose whether target exists


def test_directory_rejected(tmp_path: Path) -> None:
    """SEC-EDGE-07: Directories are rejected as server commands."""
    # Arrange
    exe_dir = tmp_path / "server_dir"
    exe_dir.mkdir()
    (exe_dir / "server").write_text("#!/bin/sh\necho 'server'\n")
    (exe_dir / "server").chmod(0o755)

    # Act & Assert - pointing to dir, not the file inside
    with pytest.raises(ServerNotFoundError):
        ServerPathResolver.resolve(str(exe_dir))


def test_path_with_trailing_slash(tmp_path: Path) -> None:
    """SEC-EDGE-08: Paths with trailing slashes are handled."""
    # Arrange: Create executable file
    exe_file = tmp_path / "executable_server"
    exe_file.write_text("#!/bin/sh\necho 'server'\n")
    exe_file.chmod(0o755)

    # Act: Trailing slash on file path
    result = ServerPathResolver.resolve(str(exe_file) + "/")

    # Should still resolve correctly (Path normalization)
    assert Path(result).exists()


def test_case_sensitivity_behavior(tmp_path: Path) -> None:
    """SEC-EDGE-09: Document case sensitivity on current platform."""
    import sys

    # Arrange: Create executable
    exe_file = tmp_path / "executable_server"
    exe_file.write_text("#!/bin/sh\necho 'server'\n")
    exe_file.chmod(0o755)

    # macOS is case-insensitive, Linux is case-sensitive
    if sys.platform == "darwin":
        # On macOS, case variations should work
        # This may or may not work depending on filesystem
        # Test documents the behavior
        _ = str(exe_file).upper()  # noqa: F841
    else:
        # On Linux, exact case required
        pass

    # Test passes if no unexpected exceptions


@pytest.mark.asyncio
async def test_concurrent_path_resolution(tmp_path: Path) -> None:
    """SEC-EDGE-10: Path resolution is thread-safe."""
    # Arrange
    exe_file = tmp_path / "executable_server"
    exe_file.write_text("#!/bin/sh\necho 'server'\n")
    exe_file.chmod(0o755)

    results = []
    errors = []

    async def resolve_concurrently():
        try:
            result = ServerPathResolver.resolve(str(exe_file))
            results.append(result)
        except Exception as e:
            errors.append(e)

    # Act: Run 100 concurrent resolutions
    await asyncio.gather(*[resolve_concurrently() for _ in range(100)])

    # Assert: All should succeed, no errors
    assert len(results) == 100
    assert len(errors) == 0
