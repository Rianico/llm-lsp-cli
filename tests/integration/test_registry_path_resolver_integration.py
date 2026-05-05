"""Integration tests for ServerRegistry using ServerPathResolver."""

import os
import pytest
from pathlib import Path

from llm_lsp_cli.server.registry import ServerRegistry
from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths


@pytest.fixture(autouse=True)
def reset_xdg_paths():
    """Reset XDG paths before and after each test."""
    XdgPaths.reset_for_testing()
    yield
    XdgPaths.reset_for_testing()


@pytest.mark.asyncio
async def test_registry_resolves_absolute_path_via_path_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_project_config: None
) -> None:
    """INT-REG-01: ServerRegistry uses ServerPathResolver for absolute paths."""
    # Arrange: Create executable at absolute path
    custom_bin = tmp_path / "custom_bin"
    custom_bin.mkdir()
    server_exe = custom_bin / "pyright-langserver"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    # Create config in the exact location XdgPaths will look
    # XdgPaths creates: $XDG_CONFIG_HOME/llm-lsp-cli/config.yaml
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(f"""languages:
  python:
    command: "{server_exe}"
""")

    # Mock config directory
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # Reset XDG paths singleton to pick up new env var
    XdgPaths.reset_for_testing()

    # Verify config is being loaded from correct location
    from llm_lsp_cli.config.manager import ConfigManager

    test_config = ConfigManager.load()
    assert test_config.languages.get("python") is not None, "Python config should be loaded"

    # Act: Create registry and get workspace
    registry = ServerRegistry()
    workspace = await registry.get_or_create_workspace(
        workspace_path=str(tmp_path / "workspace"), language="python"
    )

    # Assert: Server command is resolved correctly
    assert workspace.server_command == str(server_exe.resolve())


@pytest.mark.asyncio
async def test_registry_resolves_tilde_path_via_path_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_project_config: None
) -> None:
    """INT-REG-02: ServerRegistry expands tilde paths via ServerPathResolver."""
    # Arrange: Mock HOME and create executable
    mock_home = tmp_path / "home"
    mock_home.mkdir()
    bin_dir = mock_home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    server_exe = bin_dir / "basedpyright"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    monkeypatch.setenv("HOME", str(mock_home))

    # Create config in the exact location XdgPaths will look
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""languages:
  python:
    command: "~/.local/bin/basedpyright"
""")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    XdgPaths.reset_for_testing()

    # Act
    registry = ServerRegistry()
    workspace = await registry.get_or_create_workspace(
        workspace_path=str(tmp_path / "workspace"), language="python"
    )

    # Assert: Tilde expanded correctly
    assert workspace.server_command == str(server_exe.resolve())


@pytest.mark.asyncio
async def test_registry_resolves_env_var_path_via_path_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_project_config: None
) -> None:
    """INT-REG-03: ServerRegistry expands environment variable paths."""
    # Arrange
    custom_dir = tmp_path / "lsp_servers"
    custom_dir.mkdir()
    server_exe = custom_dir / "typescript-language-server"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    monkeypatch.setenv("LSP_SERVER_DIR", str(custom_dir))

    # Create config in the exact location XdgPaths will look
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""languages:
  typescript:
    command: "$LSP_SERVER_DIR/typescript-language-server"
""")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    XdgPaths.reset_for_testing()

    # Act
    registry = ServerRegistry()
    workspace = await registry.get_or_create_workspace(
        workspace_path=str(tmp_path / "workspace"), language="typescript"
    )

    # Assert
    assert workspace.server_command == str(server_exe.resolve())


@pytest.mark.asyncio
async def test_registry_falls_back_to_path_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_project_config: None
) -> None:
    """INT-REG-04: ServerRegistry falls back to PATH for simple commands."""
    # Arrange: Create executable in mock PATH
    mock_bin = tmp_path / "mock_bin"
    mock_bin.mkdir()
    server_exe = mock_bin / "pyright"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    # Prepend to PATH
    monkeypatch.setenv("PATH", f"{mock_bin}:{os.environ.get('PATH', '')}")

    # Create config in the exact location XdgPaths will look
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""languages:
  python:
    command: "pyright"
""")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    XdgPaths.reset_for_testing()

    # Act
    registry = ServerRegistry()
    workspace = await registry.get_or_create_workspace(
        workspace_path=str(tmp_path / "workspace"), language="python"
    )

    # Assert: Found via PATH
    assert workspace.server_command == str(server_exe.resolve())


@pytest.mark.asyncio
async def test_registry_raises_file_not_found_for_nonexistent_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_project_config: None
) -> None:
    """INT-REG-05: ServerRegistry raises FileNotFoundError for invalid paths."""
    # Arrange: Config with non-existent path
    # Create config in the exact location XdgPaths will look
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("""languages:
  python:
    command: "/nonexistent/path/to/server"
""")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    XdgPaths.reset_for_testing()

    # Act & Assert
    registry = ServerRegistry()
    with pytest.raises(FileNotFoundError):
        await registry.get_or_create_workspace(
            workspace_path=str(tmp_path / "workspace"), language="python"
        )


@pytest.mark.asyncio
async def test_registry_preserves_server_args_with_path_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_project_config: None
) -> None:
    """INT-REG-06: ServerRegistry preserves args when resolving paths."""
    # Arrange
    custom_bin = tmp_path / "bin"
    custom_bin.mkdir()
    server_exe = custom_bin / "pyright-langserver"
    server_exe.write_text("#!/bin/sh\necho 'server'\n")
    server_exe.chmod(0o755)

    # Create config in the exact location XdgPaths will look
    config_dir = tmp_path / "llm-lsp-cli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(f"""languages:
  python:
    command: "{server_exe}"
    args: ["--stdio", "--log-level", "debug"]
""")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    XdgPaths.reset_for_testing()

    # Act
    registry = ServerRegistry()
    workspace = await registry.get_or_create_workspace(
        workspace_path=str(tmp_path / "workspace"), language="python"
    )

    # Assert
    assert workspace.server_command == str(server_exe.resolve())
    assert workspace.server_args == ["--stdio", "--log-level", "debug"]
