"""Config commands for llm-lsp-cli."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.config.defaults import DEFAULT_CONFIG

app = typer.Typer(name="config", help="Manage configuration.")


@app.command("list")
def config_list(
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, yaml, or text",
    ),
    lsp_server: str | None = typer.Option(
        None,
        "--lsp-server",
        "-ls",
        help="Override auto-detected LSP server (e.g., 'pyright-langserver')",
    ),
) -> None:
    """List supported LSP server capabilities.

    Outputs capabilities for all configured LSP servers (pyright, basedpyright,
    typescript-language-server, rust-analyzer, gopls, jdtls).

    Auto-detects the current project language and shows capabilities for the
    configured LSP server based on language.xxx.command in config.yaml.
    Use --lsp-server to override auto-detection.
    """
    from llm_lsp_cli.config.capabilities import format_capabilities
    from llm_lsp_cli.utils.language_detector import detect_language_from_workspace

    # Determine server filter
    server_filter: str | None = None

    if lsp_server is not None:
        # Explicit override provided
        server_filter = lsp_server
    else:
        # Auto-detect language and resolve to server name
        workspace_path = str(Path.cwd())
        # Check if any project files were found
        raw_detected = detect_language_from_workspace(workspace_path)
        if raw_detected:
            try:
                server_filter = ConfigManager.get_lsp_server_name(raw_detected)
            except Exception:
                # If we can't resolve, fall through to showing all servers
                server_filter = None

    try:
        output = format_capabilities(format, server_filter=server_filter)
        typer.echo(output)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("init")
def config_init(
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Create .llm-lsp-cli.yaml in current directory instead of global config",
    ),
) -> None:
    """Initialize configuration file.

    Creates either:
    - Global config: ~/.config/llm-lsp-cli/config.yaml (default)
    - Project config: ./.llm-lsp-cli.yaml (with --project)
    """
    if project:
        config_path = Path.cwd() / ".llm-lsp-cli.yaml"
        if config_path.exists():
            typer.echo(f"Project config already exists at: {config_path}")
            return
        config_path.write_text(
            yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
        )
        typer.echo(f"Created project config at: {config_path}")
    else:
        config_path = ConfigManager.get_config_dir() / "config.yaml"

        if config_path.exists():
            typer.echo(f"Configuration already exists at: {config_path}")
            return

        # Create config directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_path.write_text(
            yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
        )

        typer.echo(f"Created default configuration at: {config_path}")
