"""Daemon lifecycle commands for llm-lsp-cli."""

from __future__ import annotations

from typing import Any

import typer

from llm_lsp_cli.commands.shared import (
    GlobalOptions,
    create_daemon_manager,
    get_lsp_server_name,
    resolve_language,
    run_daemon_command,
)

app = typer.Typer(name="daemon", help="Manage the LSP daemon server.")


@app.command()
def start(
    ctx: typer.Context,
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
    trace: bool = typer.Option(
        False, "--trace", "-t",
        help="Enable transport-level trace logging (more verbose than --debug)"
    ),
    diagnostic_log: bool = typer.Option(
        False, "--diagnostic-log", help="Write full diagnostics to diagnostics.log file"
    ),
) -> None:
    """Start the LSP daemon server.

    Language is auto-detected from workspace project files if not specified.
    Supported detections:
    - Java: pom.xml, build.gradle
    - Rust: Cargo.toml
    - TypeScript: tsconfig.json
    - JavaScript: package.json
    - Go: go.mod
    - C#: *.sln, *.csproj
    - C/C++: Makefile, compile_commands.json
    - Python: pyproject.toml, setup.py, requirements.txt
    """

    def do_start(manager: Any, cmd: str, detected_lang: str) -> None:
        typer.echo(f"[{cmd}] Initializing daemon...", err=True)
        typer.echo(f"[{cmd}] Spawning {get_lsp_server_name(detected_lang)}...", err=True)
        manager.start(diagnostic_log=diagnostic_log)
        typer.echo(f"[{cmd}] Ready (PID: {manager.get_pid()})", err=True)

    run_daemon_command(
        command_name="START",
        workspace=workspace,
        language=language,
        lsp_conf=lsp_conf,
        debug=debug,
        trace=trace,
        check_running=False,
        action_fn=do_start,
        ctx=ctx,
    )


@app.command()
def stop(
    ctx: typer.Context,
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Stop the LSP daemon server."""

    def do_stop(manager: Any, cmd: str, _lang: str = "") -> None:
        _ = _lang
        typer.echo(f"[{cmd}] Stopping daemon...", err=True)
        manager.stop()
        typer.echo(f"[{cmd}] Daemon stopped", err=True)

    run_daemon_command(
        command_name="STOP",
        workspace=workspace,
        language=language,
        lsp_conf=lsp_conf,
        debug=False,
        check_running=True,
        action_fn=do_stop,
        ctx=ctx,
    )


@app.command()
def restart(
    ctx: typer.Context,
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
    trace: bool = typer.Option(
        False, "--trace", "-t",
        help="Enable transport-level trace logging (more verbose than --debug)"
    ),
    diagnostic_log: bool = typer.Option(
        False, "--diagnostic-log", help="Write full diagnostics to diagnostics.log file"
    ),
) -> None:
    """Restart the LSP daemon server."""

    def do_restart(manager: Any, cmd: str, detected_lang: str) -> None:
        typer.echo(f"[{cmd}] Restarting daemon...", err=True)

        if manager.is_running():
            typer.echo(f"[{cmd}] Stopping existing daemon...", err=True)
            manager.stop()

        typer.echo(f"[{cmd}] Starting {get_lsp_server_name(detected_lang)}...", err=True)
        manager.start(diagnostic_log=diagnostic_log)
        typer.echo(f"[{cmd}] Daemon restarted (PID: {manager.get_pid()})", err=True)

    run_daemon_command(
        command_name="RESTART",
        workspace=workspace,
        language=language,
        lsp_conf=lsp_conf,
        debug=debug,
        trace=trace,
        check_running=None,
        action_fn=do_restart,
        ctx=ctx,
    )


@app.command()
def status(
    ctx: typer.Context,
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Show the daemon server status."""
    if ctx.obj is not None:
        global_opts: GlobalOptions = ctx.obj
        effective_workspace = workspace if workspace is not None else global_opts.workspace
        effective_language = language if language is not None else global_opts.language
    else:
        effective_workspace = workspace
        effective_language = language

    workspace_path, detected_language = resolve_language(effective_workspace, effective_language)
    manager = create_daemon_manager(workspace_path, detected_language, lsp_conf)

    if manager.is_running():
        pid = manager.get_pid()
        typer.echo(f"Daemon is running (PID: {pid})")
        typer.echo(f"Socket: {manager.socket_path}")
        typer.echo(f"Workspace: {workspace_path}")
        typer.echo(f"Language: {detected_language}")
    else:
        typer.echo("Daemon is not running.")
