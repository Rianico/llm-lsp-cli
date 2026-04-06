"""CLI entry point for llm-lsp-cli."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.ipc import UNIXClient
from llm_lsp_cli.utils.language_detector import (
    detect_language_from_file,
    detect_language_with_fallback,
)

app = typer.Typer(
    name="llm-lsp-cli",
    help="Interact with language servers to provide code intelligence features.",
    add_completion=True,
)


class CLIError(Exception):
    """Custom exception for CLI errors."""

    pass


def _resolve_language(workspace: str | None, language: str | None) -> tuple[str, str]:
    """Resolve workspace path and language, returning (workspace_path, language).

    Args:
        workspace: Workspace path (defaults to current directory)
        language: Language identifier (auto-detected if not provided)

    Returns:
        Tuple of (workspace_path, detected_language)
    """
    workspace_path = workspace or str(Path.cwd())
    detected_language = detect_language_with_fallback(
        workspace_path=workspace_path,
        explicit_language=language,
        default_language="python",
    )
    return workspace_path, detected_language


def _validate_file_in_workspace(
    file: str,
    workspace: str | None,
) -> Path:
    """Validate file exists and is within workspace boundary.

    Args:
        file: File path to validate
        workspace: Workspace path (defaults to current directory)

    Returns:
        Resolved file path

    Raises:
        typer.Exit: If file doesn't exist or escapes workspace boundary
    """
    workspace_path = workspace or str(Path.cwd())
    file_path = Path(file).resolve()
    workspace_resolved = Path(workspace_path).resolve()

    # Validate path doesn't escape workspace boundary
    try:
        file_path.relative_to(workspace_resolved)
    except ValueError:
        typer.echo(
            f"Error: File path escapes workspace boundary: {file_path}\n"
            f"Workspace: {workspace_resolved}",
            err=True,
        )
        raise typer.Exit(1) from None

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    return file_path


def _ensure_daemon_running(
    language: str | None = None,
    workspace: str | None = None,
) -> None:
    """Ensure daemon is running before executing commands.

    Args:
        language: Language identifier (auto-detected from workspace if not provided)
        workspace: Workspace path (defaults to current directory)
    """
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path = workspace or str(Path.cwd())
    # Use provided language or default to python for daemon check
    # The actual language-specific socket is resolved in _send_request
    manager = DaemonManager(
        workspace_path=workspace_path,
        language=language or "python",
    )
    if not manager.is_running():
        typer.echo(
            f"Error: Daemon is not running for workspace: {workspace_path}\n"
            f"Start it with: llm-lsp-cli start -l <language>",
            err=True,
        )
        raise typer.Exit(1)


def _send_request(
    method: str,
    params: dict[str, Any],
    language: str | None = None,
) -> Any:
    """Send a request to the daemon and return the response.

    Args:
        method: LSP method name
        params: Request parameters
        language: Language identifier (auto-detected from filePath if not provided)
    """
    workspace_path = params.get("workspacePath", str(Path.cwd()))

    # Detect language from file if not provided
    if language is None:
        file_path = params.get("filePath")
        language = detect_language_from_file(file_path) if file_path else "python"

    socket_path = ConfigManager.build_socket_path(
        workspace_path=workspace_path,
        language=language,
    )

    async def send() -> Any:
        client = UNIXClient(str(socket_path))
        try:
            response = await client.request(method, params)
            return response
        except asyncio.TimeoutError:
            raise CLIError(
                "Request timed out. The LSP server may be busy or unresponsive."
            ) from None
        except FileNotFoundError:
            raise CLIError(
                f"Cannot connect to daemon. Socket not found: {socket_path}\n"
                "Ensure the daemon is running: llm-lsp-cli status"
            ) from None
        except OSError as e:
            raise CLIError(
                f"Cannot connect to daemon: {e}\nEnsure the daemon is running: llm-lsp-cli start"
            ) from e
        finally:
            await client.close()

    return asyncio.run(send())


@app.command()
def version() -> None:
    """Show the version of llm-lsp-cli."""
    from llm_lsp_cli import __version__

    typer.echo(f"llm-lsp-cli version {__version__}")


@app.command()
def start(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to bind to"),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
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
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path, detected_language = _resolve_language(workspace, language)

    if language is None:
        typer.echo(f"Auto-detected language: {detected_language}")

    manager = DaemonManager(
        workspace_path=workspace_path, language=detected_language, lsp_conf=lsp_conf, debug=debug
    )
    if manager.is_running():
        typer.echo("Daemon is already running.", err=True)
        raise typer.Exit(1)

    manager.start()
    typer.echo(f"Daemon started (workspace: {workspace_path}, language: {detected_language}).")


@app.command()
def stop(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Stop the LSP daemon server."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path, detected_language = _resolve_language(workspace, language)

    manager = DaemonManager(
        workspace_path=workspace_path, language=detected_language, lsp_conf=lsp_conf
    )
    if not manager.is_running():
        typer.echo("Daemon is not running.")
        raise typer.Exit(0)

    manager.stop()
    typer.echo("Daemon stopped successfully.")


@app.command()
def restart(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Restart the LSP daemon server."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path, detected_language = _resolve_language(workspace, language)

    manager = DaemonManager(
        workspace_path=workspace_path, language=detected_language, lsp_conf=lsp_conf
    )
    manager.stop()
    manager.start()
    typer.echo(f"Daemon restarted (workspace: {workspace_path}, language: {detected_language}).")


@app.command()
def status(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Show the daemon server status."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path, detected_language = _resolve_language(workspace, language)

    manager = DaemonManager(
        workspace_path=workspace_path, language=detected_language, lsp_conf=lsp_conf
    )
    if manager.is_running():
        pid = manager.get_pid()
        typer.echo(f"Daemon is running (PID: {pid})")

        # Show socket path
        socket_path = manager.socket_path
        typer.echo(f"Socket: {socket_path}")
        typer.echo(f"Workspace: {workspace_path}")
        typer.echo(f"Language: {detected_language}")
    else:
        typer.echo("Daemon is not running.")


@app.command()
def definition(
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
) -> None:
    """Get definition location for symbol at position."""
    # Detect language from file if not provided
    if language is None:
        language = detect_language_from_file(file)

    _ensure_daemon_running(language=language, workspace=workspace)

    workspace_path = workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, workspace)

    try:
        response = _send_request(
            "textDocument/definition",
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
                "line": line,
                "column": column,
            },
            language=language,
        )
        locations = response.get("locations", [])
        if locations:
            for loc in locations:
                uri = loc.get("uri", "")
                range_obj = loc.get("range", {})
                start = range_obj.get("start", {})
                typer.echo(f"{uri}:{start.get('line', 0) + 1}:{start.get('character', 0) + 1}")
        else:
            typer.echo("No definition found.")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def references(
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
) -> None:
    """Get references to symbol at position."""
    # Detect language from file if not provided
    if language is None:
        language = detect_language_from_file(file)

    _ensure_daemon_running(language=language, workspace=workspace)

    workspace_path = workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, workspace)

    try:
        response = _send_request(
            "textDocument/references",
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
                "line": line,
                "column": column,
            },
            language=language,
        )
        locations = response.get("locations", [])
        if locations:
            for loc in locations:
                uri = loc.get("uri", "")
                range_obj = loc.get("range", {})
                start = range_obj.get("start", {})
                typer.echo(f"{uri}:{start.get('line', 0) + 1}:{start.get('character', 0) + 1}")
        else:
            typer.echo("No references found.")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def completion(
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
) -> None:
    """Get completions at position."""
    # Detect language from file if not provided
    if language is None:
        language = detect_language_from_file(file)

    _ensure_daemon_running(language=language, workspace=workspace)

    workspace_path = workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, workspace)

    try:
        response = _send_request(
            "textDocument/completion",
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
                "line": line,
                "column": column,
            },
            language=language,
        )
        items = response.get("items", [])
        if items:
            for item in items:
                label = item.get("label", "")
                detail = item.get("detail", "")
                typer.echo(f"{label} - {detail}" if detail else label)
        else:
            typer.echo("No completions found.")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def hover(
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
) -> None:
    """Get hover information at position."""
    # Detect language from file if not provided
    if language is None:
        language = detect_language_from_file(file)

    _ensure_daemon_running(language=language, workspace=workspace)

    workspace_path = workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, workspace)

    try:
        response = _send_request(
            "textDocument/hover",
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
                "line": line,
                "column": column,
            },
            language=language,
        )
        hover = response.get("hover")
        if hover:
            contents = hover.get("contents", {})
            value = contents.get("value", "") if isinstance(contents, dict) else str(contents)
            typer.echo(value)
        else:
            typer.echo("No hover information available.")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def document_symbol(
    file: str = typer.Argument(..., help="File path"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
) -> None:
    """Get document symbols."""
    # Detect language from file if not provided
    if language is None:
        language = detect_language_from_file(file)

    _ensure_daemon_running(language=language, workspace=workspace)

    workspace_path = workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, workspace)

    try:
        response = _send_request(
            "textDocument/documentSymbol",
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
            },
            language=language,
        )
        symbols = response.get("symbols", [])
        if symbols:
            for sym in symbols:
                name = sym.get("name", "")
                kind = sym.get("kind", 0)
                range_obj = sym.get("range", {})
                start = range_obj.get("start", {})
                typer.echo(
                    f"{name} (kind={kind}) at {start.get('line', 0) + 1}:"
                    f"{start.get('character', 0) + 1}"
                )
        else:
            typer.echo("No symbols found.")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def workspace_symbol(
    query: str = typer.Argument(..., help="Search query"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
) -> None:
    """Search workspace symbols."""
    # Detect language from file if not provided
    if language is None:
        language = "python"  # Default for workspace-wide searches without a specific file

    _ensure_daemon_running(language=language, workspace=workspace)

    workspace_path = workspace or str(Path.cwd())

    try:
        response = _send_request(
            "workspace/symbol",
            {
                "workspacePath": workspace_path,
                "query": query,
            },
            language=language,
        )
        symbols = response.get("symbols", [])
        if symbols:
            for sym in symbols:
                name = sym.get("name", "")
                kind = sym.get("kind", 0)
                location = sym.get("location", {})
                uri = location.get("uri", "")
                typer.echo(f"{name} (kind={kind}) in {uri}")
        else:
            typer.echo(f"No symbols found for query: {query}")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


# Configuration Commands

config_app = typer.Typer(name="config", help="Manage configuration.")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    try:
        config = ConfigManager.load()
        data = config.model_dump(mode="json")
        typer.echo(json.dumps(data, indent=2))
    except Exception as e:
        typer.echo(f"Error loading config: {e}", err=True)
        raise typer.Exit(1) from e


@config_app.command("init")
def config_init() -> None:
    """Initialize configuration with defaults."""
    created = ConfigManager.init_config()
    if created:
        config_path = ConfigManager.CONFIG_FILE
        typer.echo(f"Configuration initialized at: {config_path}")
    else:
        typer.echo("Configuration already exists.")


@config_app.command("path")
def config_path() -> None:
    """Show configuration file path."""
    typer.echo(str(ConfigManager.CONFIG_FILE))


app.add_typer(config_app, name="config")


if __name__ == "__main__":
    app()
