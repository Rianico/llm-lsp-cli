"""Config commands for llm-lsp-cli."""

from __future__ import annotations

from pathlib import Path

import typer

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
from llm_lsp_cli.utils.yaml_formatter import dump_config

app = typer.Typer(name="config", help="Manage configuration.")


def _write_config_with_confirmation(
    config_path: Path,
    force: bool,
    config_type: str,
    create_parent: bool = False,
    success_prefix: str | None = None,
) -> bool:
    """Write config file with optional force/overwrite handling.

    Args:
        config_path: Path to write config file
        force: Whether to prompt for overwrite if file exists
        config_type: Description for messages (e.g., "project config", "configuration")
        create_parent: Whether to create parent directory if needed
        success_prefix: Custom prefix for success message (e.g., "default configuration")
                       If None, uses config_type

    Returns:
        True if config was written, False if user declined or file exists without force
    """
    if config_path.exists():
        if not force:
            typer.echo(f"{config_type.capitalize()} already exists at: {config_path}")
            if config_type == "configuration":
                typer.echo("Use --force to overwrite.")
            return False
        if not typer.confirm(
            f"Overwrite existing {config_type} at {config_path}?",
            default=False,
        ):
            return False

    if create_parent:
        config_path.parent.mkdir(parents=True, exist_ok=True)

    config_path.write_text(dump_config(DEFAULT_CONFIG))
    success_msg = success_prefix if success_prefix else config_type
    typer.echo(f"Created {success_msg} at: {config_path}")
    return True


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
    from llm_lsp_cli.utils.language_detector import FILE_EXTENSION_MAP
    from llm_lsp_cli.utils.root_detector import detect_workspace_and_language

    # Determine server filter
    server_filter: str | None = None

    if lsp_server is not None:
        # Explicit override provided
        server_filter = lsp_server
    else:
        # Auto-detect language and resolve to server name
        from llm_lsp_cli.config import ConfigManager

        try:
            config_obj = ConfigManager.load()
            config = config_obj.model_dump(mode="json") if config_obj else {}
        except Exception:
            config = {}

        language_configs: dict[str, dict] = {}
        for lang_name, lang_conf in config.get("languages", {}).items():
            if isinstance(lang_conf, dict):
                language_configs[lang_name] = {
                    "root_markers": lang_conf.get("root_markers", [])
                }

        workspace_path, raw_detected = detect_workspace_and_language(
            file_path=None,
            explicit_workspace=None,
            explicit_language=None,
            language_configs=language_configs,
            extension_map=dict(FILE_EXTENSION_MAP),
        )
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
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing config file (prompts for confirmation)",
    ),
) -> None:
    """Initialize configuration file.

    Creates either:
    - Global config: ~/.config/llm-lsp-cli/config.yaml (default)
    - Project config: ./.llm-lsp-cli.yaml (with --project)
    """
    if project:
        config_path = Path.cwd() / ".llm-lsp-cli.yaml"
        _write_config_with_confirmation(config_path, force, "project config")
    else:
        config_path = ConfigManager.get_config_dir() / "config.yaml"
        _write_config_with_confirmation(
            config_path, force, "configuration", create_parent=True,
            success_prefix="default configuration",
        )
