"""CLI entry point for llm-lsp-cli."""
import asyncio
import json
from pathlib import Path
from typing import Any

import typer

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.ipc import UNIXClient

app = typer.Typer(
    name="llm-lsp-cli",
    help="Interact with language servers to provide code intelligence features.",
    add_completion=True,
)


class CLIError(Exception):
    """Custom exception for CLI errors."""
    pass


def _ensure_daemon_running() -> None:
    """Ensure daemon is running before executing commands."""
    from llm_lsp_cli.daemon import DaemonManager

    manager = DaemonManager(workspace_path=str(Path.cwd()), language="python")
    if not manager.is_running():
        typer.echo(
            "Error: Daemon is not running.\n"
            "Start it with: llm-lsp-cli start",
            err=True
        )
        raise typer.Exit(1)


def _send_request(method: str, params: dict[str, Any]) -> Any:
    """Send a request to the daemon and return the response."""
    # Assuming python as default fallback, but ideally language comes from daemon status or args
    socket_path = ConfigManager.build_socket_path(
        workspace_path=params.get("workspacePath", str(Path.cwd())),
        language="python",  # TODO: Fix architecture limitation
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
                f"Cannot connect to daemon: {e}\n"
                "Ensure the daemon is running: llm-lsp-cli start"
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
    language: str = typer.Option("python", "--language", "-l", help="Language"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to bind to"),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
) -> None:
    """Start the LSP daemon server."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path = workspace or str(Path.cwd())
    manager = DaemonManager(
        workspace_path=workspace_path, language=language, lsp_conf=lsp_conf, debug=debug
    )
    if manager.is_running():
        typer.echo("Daemon is already running.", err=True)
        raise typer.Exit(1)

    manager.start()
    typer.echo(f"Daemon started successfully (workspace: {workspace_path}, language: {language}).")


@app.command()
def stop(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str = typer.Option("python", "--language", "-l", help="Language"),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Stop the LSP daemon server."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path = workspace or str(Path.cwd())
    manager = DaemonManager(workspace_path=workspace_path, language=language, lsp_conf=lsp_conf)
    if not manager.is_running():
        typer.echo("Daemon is not running.", err=True)
        raise typer.Exit(0)

    manager.stop()
    typer.echo("Daemon stopped successfully.")


@app.command()
def restart(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str = typer.Option("python", "--language", "-l", help="Language"),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Restart the LSP daemon server."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path = workspace or str(Path.cwd())
    manager = DaemonManager(workspace_path=workspace_path, language=language, lsp_conf=lsp_conf)
    manager.stop()
    manager.start()
    typer.echo(
        f"Daemon restarted successfully (workspace: {workspace_path}, language: {language})."
    )


@app.command()
def status(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str = typer.Option("python", "--language", "-l", help="Language"),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Show the daemon server status."""
    from llm_lsp_cli.daemon import DaemonManager

    workspace_path = workspace or str(Path.cwd())
    manager = DaemonManager(workspace_path=workspace_path, language=language, lsp_conf=lsp_conf)
    if manager.is_running():
        pid = manager.get_pid()
        typer.echo(f"Daemon is running (PID: {pid})")

        # Show socket path
        socket_path = manager.socket_path
        typer.echo(f"Socket: {socket_path}")
        typer.echo(f"Workspace: {workspace_path}")
        typer.echo(f"Language: {language}")
    else:
        typer.echo("Daemon is not running.")


@app.command()
def definition(
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
) -> None:
    """Get definition location for symbol at position."""
    _ensure_daemon_running()

    workspace_path = workspace or str(Path.cwd())
    file_path = Path(file).resolve()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    try:
        response = _send_request("textDocument/definition", {
            "workspacePath": workspace_path,
            "filePath": str(file_path),
            "line": line,
            "column": column,
        })
        locations = response.get("locations", [])
        if locations:
            for loc in locations:
                uri = loc.get("uri", "")
                range_obj = loc.get("range", {})
                start = range_obj.get("start", {})
                typer.echo(f"{uri}:{start.get('line', 0)+1}:{start.get('character', 0)+1}")
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
) -> None:
    """Get references to symbol at position."""
    _ensure_daemon_running()

    workspace_path = workspace or str(Path.cwd())
    file_path = Path(file).resolve()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    try:
        response = _send_request("textDocument/references", {
            "workspacePath": workspace_path,
            "filePath": str(file_path),
            "line": line,
            "column": column,
        })
        locations = response.get("locations", [])
        if locations:
            for loc in locations:
                uri = loc.get("uri", "")
                range_obj = loc.get("range", {})
                start = range_obj.get("start", {})
                typer.echo(f"{uri}:{start.get('line', 0)+1}:{start.get('character', 0)+1}")
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
) -> None:
    """Get completions at position."""
    _ensure_daemon_running()

    workspace_path = workspace or str(Path.cwd())
    file_path = Path(file).resolve()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    try:
        response = _send_request("textDocument/completion", {
            "workspacePath": workspace_path,
            "filePath": str(file_path),
            "line": line,
            "column": column,
        })
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
) -> None:
    """Get hover information at position."""
    _ensure_daemon_running()

    workspace_path = workspace or str(Path.cwd())
    file_path = Path(file).resolve()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    try:
        response = _send_request("textDocument/hover", {
            "workspacePath": workspace_path,
            "filePath": str(file_path),
            "line": line,
            "column": column,
        })
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
) -> None:
    """Get document symbols."""
    _ensure_daemon_running()

    workspace_path = workspace or str(Path.cwd())
    file_path = Path(file).resolve()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}", err=True)
        raise typer.Exit(1)

    try:
        response = _send_request("textDocument/documentSymbol", {
            "workspacePath": workspace_path,
            "filePath": str(file_path),
        })
        symbols = response.get("symbols", [])
        if symbols:
            for sym in symbols:
                name = sym.get("name", "")
                kind = sym.get("kind", 0)
                range_obj = sym.get("range", {})
                start = range_obj.get("start", {})
                typer.echo(
                    f"{name} (kind={kind}) at {start.get('line', 0)+1}:" \
                    f"{start.get('character', 0)+1}"
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
) -> None:
    """Search workspace symbols."""
    _ensure_daemon_running()

    workspace_path = workspace or str(Path.cwd())

    try:
        response = _send_request("workspace/symbol", {
            "workspacePath": workspace_path,
            "query": query,
        })
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
