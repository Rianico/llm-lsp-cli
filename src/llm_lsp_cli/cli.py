"""CLI entry point for llm-lsp-cli."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.exceptions import CLIError
from llm_lsp_cli.output.formatter import CompactFormatter
from llm_lsp_cli.output.symbol_filter import filter_symbols
from llm_lsp_cli.output.verbosity import VerbosityLevel
from llm_lsp_cli.test_filter import (
    _filter_test_diagnostic_items,
    _filter_test_locations,
    _filter_test_symbols,
)
from llm_lsp_cli.utils import (
    OutputFormat,
    format_completions_csv,
    format_document_symbols_csv,
    format_hover_csv,
    format_locations_csv,
    format_output,
    format_workspace_symbols_csv,
    get_symbol_kind_name,
)
from llm_lsp_cli.utils.language_detector import (
    detect_language_from_file,
    detect_language_with_fallback,
)


@dataclass
class GlobalOptions:
    """Global options shared across all subcommands."""

    workspace: str | None = None
    language: str | None = None
    output_format: OutputFormat = OutputFormat.JSON


@dataclass
class RequestContext:
    """Context for an LSP command request."""

    workspace_path: str
    language: str
    output_format: OutputFormat
    file_path: Path | None = None
    line: int | None = None
    column: int | None = None
    query: str | None = None
    include_tests: bool = False


def _resolve_effective_options(
    global_opts: GlobalOptions,
    workspace: str | None = None,
    language: str | None = None,
    output_format: OutputFormat | None = None,
) -> tuple[str | None, str | None, OutputFormat]:
    """Resolve effective options from global and local overrides.

    Local options override global options. Uses LSP response type for output_format.

    Args:
        global_opts: Global options from context
        workspace: Optional local workspace override
        language: Optional local language override
        output_format: Optional local format override

    Returns:
        Tuple of (effective_workspace, effective_language, effective_format)
    """
    effective_workspace = workspace if workspace is not None else global_opts.workspace
    effective_language = language if language is not None else global_opts.language
    effective_format = output_format if output_format is not None else global_opts.output_format
    return effective_workspace, effective_language, effective_format


def global_options_callback(
    ctx: typer.Context,
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    output_format: OutputFormat = typer.Option(  # noqa: B008
        OutputFormat.JSON,
        "--format",
        "-o",
        help="Output format (text, yaml, json, or csv)",
    ),
) -> None:
    """Callback to capture global options into context.

    Subcommands can override individual options locally if needed.
    """
    ctx.obj = GlobalOptions(
        workspace=workspace,
        language=language,
        output_format=output_format,
    )


app = typer.Typer(
    name="llm-lsp-cli",
    help="Interact with language servers to provide code intelligence features.",
    add_completion=True,
    callback=global_options_callback,
)


def _format_location_range(range_obj: dict[str, Any]) -> str:
    """Format a location range from LSP response.

    Args:
        range_obj: LSP range object with start/end positions

    Returns:
        Formatted range string "start_line:start_char-end_line:end_char"
    """
    start = range_obj.get("start", {})
    end = range_obj.get("end", {})
    start_line = start.get("line", 0) + 1
    start_char = start.get("character", 0) + 1
    end_line = end.get("line", 0) + 1
    end_char = end.get("character", 0) + 1
    return f"{start_line}:{start_char}-{end_line}:{end_char}"


def _format_locations_text(locations: list[dict[str, Any]]) -> None:
    """Format and print location list in text format.

    Args:
        locations: List of LSP location objects
    """
    if locations:
        for loc in locations:
            uri = loc.get("uri", "")
            range_obj = loc.get("range", {})
            range_str = _format_location_range(range_obj)
            typer.echo(f"{uri}:{range_str}")
    else:
        typer.echo("No locations found.")


def _format_completions_text(items: list[dict[str, Any]]) -> None:
    """Format and print completion items in text format.

    Args:
        items: List of LSP completion items
    """
    if items:
        for item in items:
            label = item.get("label", "")
            detail = item.get("detail", "")
            range_info = ""
            text_edit = item.get("textEdit", {})
            if text_edit and isinstance(text_edit, dict):
                range_obj = text_edit.get("range", {})
                if range_obj:
                    range_info = f" [{_format_location_range(range_obj)}]"

            if detail:
                typer.echo(f"{label} - {detail}{range_info}")
            else:
                typer.echo(f"{label}{range_info}")
    else:
        typer.echo("No completions found.")


def _format_hover_text(hover: dict[str, Any] | None) -> None:
    """Format and print hover information in text format.

    Args:
        hover: LSP hover response object
    """
    if hover:
        contents = hover.get("contents", {})
        value = contents.get("value", "") if isinstance(contents, dict) else str(contents)
        range_obj = hover.get("range", {})
        if range_obj:
            range_str = _format_location_range(range_obj)
            typer.echo(f"[{range_str}] {value}")
        else:
            typer.echo(value)
    else:
        typer.echo("No hover information available.")


def _format_symbols_text(symbols: list[dict[str, Any]], include_location: bool = True) -> None:
    """Format and print symbol list in text format.

    Args:
        symbols: List of LSP symbol objects
        include_location: Whether to include location info in output
    """
    if symbols:
        for sym in symbols:
            name = sym.get("name", "")
            kind = sym.get("kind", 0)
            kind_name = get_symbol_kind_name(kind)
            if include_location:
                range_obj = sym.get("range", {})
                range_str = _format_location_range(range_obj)
                typer.echo(f"{name} ({kind_name}) at {range_str}")
            else:
                typer.echo(f"{name} ({kind_name})")
    else:
        typer.echo("No symbols found.")


def _format_workspace_symbols_text(symbols: list[dict[str, Any]]) -> None:
    """Format and print workspace symbol list in text format.

    Args:
        symbols: List of LSP workspace symbol objects
    """
    if symbols:
        for sym in symbols:
            name = sym.get("name", "")
            kind = sym.get("kind", 0)
            kind_name = get_symbol_kind_name(kind)
            location = sym.get("location", {})
            uri = location.get("uri", "")
            range_info = ""
            range_obj = location.get("range", {})
            if range_obj:
                range_info = f" [{_format_location_range(range_obj)}]"
            typer.echo(f"{name} ({kind_name}) in {uri}{range_info}")
    else:
        typer.echo("No symbols found.")


def _apply_verbosity_filter(symbols: list[dict[str, Any]], verbose: int) -> list[dict[str, Any]]:
    """Apply verbosity-based filtering to symbols.

    Caps verbosity at DEBUG level (2) and filters symbols accordingly.

    Args:
        symbols: List of symbol dictionaries
        verbose: Verbosity count from CLI option

    Returns:
        Filtered list of symbols
    """
    verbosity = VerbosityLevel(min(verbose, 2))  # Cap at DEBUG level
    return filter_symbols(symbols, verbosity)


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


def _build_request_context(
    ctx: typer.Context,
    workspace: str | None,
    language: str | None,
    output_format: OutputFormat | None,
    file: str | None = None,
    line: int | None = None,
    column: int | None = None,
    query: str | None = None,
    include_tests: bool = False,
) -> RequestContext:
    """Build a request context from command arguments.

    Args:
        ctx: Typer context
        workspace: Optional workspace override
        language: Optional language override
        output_format: Optional format override
        file: Optional file path
        line: Optional line number (1-based)
        column: Optional column number (1-based)
        query: Optional search query
        include_tests: Whether to include test files

    Returns:
        RequestContext with resolved values
    """
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = _resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    # Auto-detect language from file if not provided
    if effective_language is None and file is not None:
        effective_language = detect_language_from_file(file)

    workspace_path = effective_workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, effective_workspace) if file else None

    return RequestContext(
        workspace_path=workspace_path,
        language=effective_language or "python",
        output_format=effective_format,
        file_path=file_path,
        line=line,
        column=column,
        query=query,
        include_tests=include_tests,
    )


def _execute_lsp_command(
    method: str,
    params: dict[str, Any],
    language: str,
    text_formatter: Callable[[Any], None],
    csv_formatter: Callable[[Any], str] | None = None,
    output_format: OutputFormat = OutputFormat.JSON,
    filter_tests: bool = False,
    test_filter_fn: Callable[[list[dict[str, Any]], bool], list[dict[str, Any]]] | None = None,
    include_tests: bool = False,
) -> None:
    """Execute an LSP command and output the result.

    Args:
        method: LSP method name
        params: Request parameters
        language: Language identifier
        text_formatter: Function to format response for text output
        csv_formatter: Optional function to format response for CSV output
        output_format: Output format
        filter_tests: Whether to filter test files from results
        test_filter_fn: Function to filter test results (takes list and include_tests flag)
        include_tests: Whether to include test files
    """
    try:
        response = _send_request(method, params, language=language)

        # Apply test filtering if requested
        if filter_tests and not include_tests and test_filter_fn is not None:
            if "locations" in response:
                locations = response.get("locations", [])
                response["locations"] = test_filter_fn(locations, False)
            elif "symbols" in response:
                symbols = response.get("symbols", [])
                response["symbols"] = test_filter_fn(symbols, False)

        def text_format_with_filter(resp: Any) -> None:
            if test_filter_fn is not None and filter_tests:
                # Re-apply filtering in text formatter for --include-tests flag
                if "locations" in resp:
                    locations = resp.get("locations", [])
                    filtered = test_filter_fn(locations, include_tests)
                    _format_locations_text(filtered)
                    return
                elif "symbols" in resp:
                    symbols = resp.get("symbols", [])
                    filtered = test_filter_fn(symbols, include_tests)
                    _format_workspace_symbols_text(filtered)
                    return
            text_formatter(resp)

        _output_result(response, output_format, text_format_with_filter, csv_formatter)
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


def _send_request(
    method: str,
    params: dict[str, Any],
    language: str | None = None,
) -> Any:
    """Send a request to the daemon and return the response.

    Auto-starts daemon if not running. Uses DaemonClient for transparent auto-start.

    Args:
        method: LSP method name
        params: Request parameters
        language: Language identifier (auto-detected from filePath if not provided)

    Returns:
        LSP response

    Raises:
        CLIError: If request fails or daemon cannot be started
    """
    from llm_lsp_cli.daemon_client import DaemonClient

    workspace_path = params.get("workspacePath", str(Path.cwd()))

    # Detect language from file if not provided
    if language is None:
        file_path = params.get("filePath")
        language = detect_language_from_file(file_path) if file_path else "python"

    # Use DaemonClient for transparent auto-start
    client = DaemonClient(
        workspace_path=workspace_path,
        language=language,
    )

    async def send() -> Any:
        from llm_lsp_cli.exceptions import DaemonCrashedError, DaemonStartupError

        try:
            response = await client.request(method, params)
            return response
        except DaemonStartupError as e:
            raise CLIError(
                f"Failed to start daemon: {e}\n"
                f"Check logs at: {ConfigManager.build_log_file_path(workspace_path, language)}"
            ) from e
        except DaemonCrashedError as e:
            raise CLIError(
                f"Daemon crashed: {e}\n"
                f"Check logs at: {ConfigManager.build_log_file_path(workspace_path, language)}"
            ) from e
        except FileNotFoundError:
            raise CLIError(
                "Cannot connect to daemon. Socket not found.\n"
                "Ensure the daemon is running: llm-lsp-cli status"
            ) from None
        except OSError as e:
            raise CLIError(
                f"Cannot connect to daemon: {e}\nEnsure the daemon is running: llm-lsp-cli start"
            ) from e
        finally:
            await client.close()

    return asyncio.run(send())


def _output_result(
    response: Any,
    output_format: OutputFormat,
    text_formatter: Callable[[Any], None],
    csv_formatter: Callable[[Any], str] | None = None,
) -> None:
    """Output response in the specified format.

    Args:
        response: The LSP response dict
        output_format: The desired output format (text, yaml, json, or csv)
        text_formatter: Function to format response for text output
        csv_formatter: Optional function to format response for CSV output
    """
    if output_format == OutputFormat.YAML:
        typer.echo(format_output(response, output_format), nl=False)
    elif output_format == OutputFormat.JSON:
        typer.echo(format_output(response, output_format))
    elif output_format == OutputFormat.CSV and csv_formatter:
        typer.echo(csv_formatter(response), nl=False)
    else:
        text_formatter(response)


@app.command()
def version() -> None:
    """Show the version of llm-lsp-cli."""
    from llm_lsp_cli import __version__

    typer.echo(f"llm-lsp-cli version {__version__}")


def _get_lsp_server_name(language: str) -> str:
    """Get the LSP server name for a language.

    Args:
        language: Language identifier

    Returns:
        LSP server name (e.g., 'pyright-langserver')
    """
    from llm_lsp_cli.config import ConfigManager

    return ConfigManager._get_lsp_server_name(language)


def _create_daemon_manager(
    workspace_path: str,
    language: str,
    lsp_conf: str | None = None,
    debug: bool = False,
) -> Any:
    """Create a DaemonManager instance.

    Args:
        workspace_path: Path to workspace directory
        language: Language identifier
        lsp_conf: Optional custom LSP config path
        debug: Enable debug logging

    Returns:
        DaemonManager instance
    """
    from llm_lsp_cli.daemon import DaemonManager

    return DaemonManager(
        workspace_path=workspace_path,
        language=language,
        lsp_conf=lsp_conf,
        debug=debug,
    )


@app.command()
def start(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
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
    workspace_path, detected_language = _resolve_language(workspace, language)
    manager = _create_daemon_manager(workspace_path, detected_language, lsp_conf, debug)

    if manager.is_running():
        typer.echo("Error: Daemon is already running.", err=True)
        raise typer.Exit(1)

    # Log detected language only if auto-detected (not explicit)
    if language is None:
        typer.echo(f"[START] Detected language: {detected_language}", err=True)

    typer.echo("[START] Initializing daemon...", err=True)
    typer.echo(f"[START] Spawning {_get_lsp_server_name(detected_language)}...", err=True)

    manager.start()
    typer.echo(f"[START] Ready (PID: {manager.get_pid()})", err=True)


@app.command()
def stop(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Stop the LSP daemon server."""
    workspace_path, detected_language = _resolve_language(workspace, language)
    manager = _create_daemon_manager(workspace_path, detected_language, lsp_conf)

    if not manager.is_running():
        typer.echo("[STOP] Daemon is not running.", err=True)
        raise typer.Exit(0)

    typer.echo("[STOP] Stopping daemon...", err=True)
    manager.stop()
    typer.echo("[STOP] Daemon stopped", err=True)


@app.command()
def restart(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (auto-detected if not specified)"
    ),
    lsp_conf: str | None = typer.Option(None, "--lsp-conf", "-c", help="Custom LSP config"),
) -> None:
    """Restart the LSP daemon server."""
    workspace_path, detected_language = _resolve_language(workspace, language)
    manager = _create_daemon_manager(workspace_path, detected_language, lsp_conf)

    typer.echo("[RESTART] Restarting daemon...", err=True)

    if manager.is_running():
        typer.echo("[RESTART] Stopping existing daemon...", err=True)
        manager.stop()

    typer.echo(f"[RESTART] Starting {_get_lsp_server_name(detected_language)}...", err=True)
    manager.start()
    typer.echo(f"[RESTART] Daemon restarted (PID: {manager.get_pid()})", err=True)


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
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include results from test files (excluded by default)",
    ),
) -> None:
    """Get definition location for symbol at position.

    By default, filters out results from test files. Use --include-tests to include them.
    """
    context = _build_request_context(
        ctx, workspace, language, output_format, file, line, column, include_tests=include_tests
    )

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    def text_format(resp: Any) -> None:
        locations = resp.get("locations", [])
        _format_locations_text(locations)

    def csv_format(resp: Any) -> str:
        locations = resp.get("locations", [])
        return format_locations_csv(locations)

    _execute_lsp_command(
        method="textDocument/definition",
        params={
            "workspacePath": context.workspace_path,
            "filePath": str(context.file_path),
            "line": line_index,
            "column": column_index,
        },
        language=context.language,
        text_formatter=text_format,
        csv_formatter=csv_format,
        output_format=context.output_format,
        filter_tests=True,
        test_filter_fn=_filter_test_locations,
        include_tests=include_tests,
    )


@app.command()
def references(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include results from test files (excluded by default)",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Output in legacy verbose format (one location per line, full columns)",
    ),
) -> None:
    """Get references to symbol at position.

    By default, filters out results from test files. Use --include-tests to include them.
    """
    context = _build_request_context(
        ctx, workspace, language, output_format, file, line, column, include_tests=include_tests
    )

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = _send_request(
            "textDocument/references",
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
                "line": line_index,
                "column": column_index,
            },
            language=context.language,
        )

        locations = response.get("locations", [])
        filtered = _filter_test_locations(locations, include_tests=include_tests)

        if raw:
            # Legacy verbose format
            if context.output_format == OutputFormat.TEXT:
                _format_locations_text(filtered)
            elif context.output_format == OutputFormat.YAML:
                typer.echo(format_output(filtered, OutputFormat.YAML), nl=False)
            elif context.output_format == OutputFormat.CSV:
                typer.echo(format_locations_csv(filtered), nl=False)
            else:  # JSON (default)
                typer.echo(format_output(filtered, OutputFormat.JSON))
        else:
            # Compact format (default)
            formatter = CompactFormatter(context.workspace_path)
            records = formatter.transform_locations(filtered)

            if context.output_format == OutputFormat.TEXT:
                typer.echo(formatter.locations_to_text(records))
            elif context.output_format == OutputFormat.YAML:
                typer.echo(formatter.locations_to_yaml(records), nl=False)
            elif context.output_format == OutputFormat.CSV:
                typer.echo(formatter.locations_to_csv(records), nl=False)
            else:  # JSON (default)
                typer.echo(formatter.locations_to_json(records))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def completion(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
) -> None:
    """Get completions at position."""
    context = _build_request_context(ctx, workspace, language, output_format, file, line, column)

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    def text_format(resp: Any) -> None:
        items = resp.get("items", [])
        _format_completions_text(items)

    def csv_format(resp: Any) -> str:
        items = resp.get("items", [])
        return format_completions_csv(items)

    _execute_lsp_command(
        method="textDocument/completion",
        params={
            "workspacePath": context.workspace_path,
            "filePath": str(context.file_path),
            "line": line_index,
            "column": column_index,
        },
        language=context.language,
        text_formatter=text_format,
        csv_formatter=csv_format,
        output_format=context.output_format,
    )


@app.command()
def hover(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (0-based)"),
    column: int = typer.Argument(..., help="Column number (0-based)"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
) -> None:
    """Get hover information at position."""
    context = _build_request_context(ctx, workspace, language, output_format, file, line, column)

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    def text_format(resp: Any) -> None:
        hover_data = resp.get("hover")
        _format_hover_text(hover_data)

    def csv_format(resp: Any) -> str:
        hover_data = resp.get("hover")
        return format_hover_csv(hover_data)

    _execute_lsp_command(
        method="textDocument/hover",
        params={
            "workspacePath": context.workspace_path,
            "filePath": str(context.file_path),
            "line": line_index,
            "column": column_index,
        },
        language=context.language,
        text_formatter=text_format,
        csv_formatter=csv_format,
        output_format=context.output_format,
    )


@app.command()
def document_symbol(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Include variable-level symbols (e.g., -v for verbose, -vv for debug)",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Output in legacy verbose format (one symbol per line, full columns)",
    ),
) -> None:
    """Get document symbols.

    By default, excludes variable-level symbols (variables, fields). Use -v to include them.
    """
    context = _build_request_context(ctx, workspace, language, output_format, file)

    try:
        response = _send_request(
            "textDocument/documentSymbol",
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
            },
            language=context.language,
        )

        symbols = response.get("symbols", [])

        # Apply symbol filter based on verbosity level
        filtered_symbols = _apply_verbosity_filter(symbols, verbose)

        if raw:
            # Legacy verbose format
            if context.output_format == OutputFormat.TEXT:
                _format_symbols_text(filtered_symbols)
            elif context.output_format == OutputFormat.YAML:
                typer.echo(format_output(filtered_symbols, OutputFormat.YAML), nl=False)
            elif context.output_format == OutputFormat.CSV:
                typer.echo(format_document_symbols_csv(filtered_symbols), nl=False)
            else:  # JSON (default)
                typer.echo(format_output(filtered_symbols, OutputFormat.JSON))
        else:
            # Compact format (default)
            formatter = CompactFormatter(context.workspace_path)
            records = formatter.transform_symbols(filtered_symbols)

            if context.output_format == OutputFormat.TEXT:
                typer.echo(formatter.symbols_to_text(records))
            elif context.output_format == OutputFormat.YAML:
                typer.echo(formatter.symbols_to_yaml(records), nl=False)
            elif context.output_format == OutputFormat.CSV:
                typer.echo(formatter.symbols_to_csv(records), nl=False)
            else:  # JSON (default)
                typer.echo(formatter.symbols_to_json(records))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def workspace_symbol(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include results from test files (excluded by default)",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Include variable-level symbols (e.g., -v for verbose, -vv for debug)",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Output in legacy verbose format (one symbol per line, full columns)",
    ),
) -> None:
    """Search workspace symbols.

    By default, filters out symbols from test files. Use --include-tests to include them.
    By default, excludes variable-level symbols (variables, fields). Use -v to include them.
    """
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = _resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    workspace_path = effective_workspace or str(Path.cwd())
    language_value = effective_language or "python"

    try:
        response = _send_request(
            "workspace/symbol",
            {"workspacePath": workspace_path, "query": query},
            language=language_value,
        )

        symbols = response.get("symbols", [])
        filtered = _filter_test_symbols(symbols, include_tests=include_tests)

        # Apply symbol filter based on verbosity level
        filtered = _apply_verbosity_filter(filtered, verbose)

        if raw:
            # Legacy verbose format
            if effective_format == OutputFormat.TEXT:
                _format_workspace_symbols_text(filtered)
            elif effective_format == OutputFormat.YAML:
                typer.echo(format_output(filtered, OutputFormat.YAML), nl=False)
            elif effective_format == OutputFormat.CSV:
                typer.echo(format_workspace_symbols_csv(filtered), nl=False)
            else:  # JSON (default)
                typer.echo(format_output(filtered, OutputFormat.JSON))
        else:
            # Compact format (default)
            formatter = CompactFormatter(workspace_path)
            records = formatter.transform_symbols(filtered)

            if effective_format == OutputFormat.TEXT:
                typer.echo(formatter.symbols_to_text(records))
            elif effective_format == OutputFormat.YAML:
                typer.echo(formatter.symbols_to_yaml(records), nl=False)
            elif effective_format == OutputFormat.CSV:
                typer.echo(formatter.symbols_to_csv(records), nl=False)
            else:  # JSON (default)
                typer.echo(formatter.symbols_to_json(records))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def diagnostics(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
) -> None:
    """Get diagnostics for a single file.

    Returns LSP diagnostics (errors, warnings, info, hints) for the specified file.
    """
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = _resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    # Auto-detect language from file if not provided
    if effective_language is None:
        effective_language = detect_language_from_file(file)

    workspace_path = effective_workspace or str(Path.cwd())
    file_path = _validate_file_in_workspace(file, effective_workspace)

    try:
        response = _send_request(
            "textDocument/diagnostic",
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
            },
            language=effective_language or "python",
        )

        diagnostics_list = response.get("diagnostics", [])
        formatter = CompactFormatter(workspace_path)
        records = formatter.transform_diagnostics(diagnostics_list, file_path=str(file_path))

        if effective_format == OutputFormat.TEXT:
            typer.echo(formatter.diagnostics_to_text(records))
        elif effective_format == OutputFormat.YAML:
            typer.echo(formatter.diagnostics_to_yaml(records), nl=False)
        elif effective_format == OutputFormat.CSV:
            typer.echo(formatter.diagnostics_to_csv(records), nl=False)
        else:  # JSON (default)
            typer.echo(formatter.diagnostics_to_json(records))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def workspace_diagnostics(
    ctx: typer.Context,
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
    output_format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "--format",
        "-o",
        help="Output format (overrides global)",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include diagnostics from test files (excluded by default)",
    ),
) -> None:
    """Get diagnostics for entire workspace.

    Returns LSP diagnostics (errors, warnings, info, hints) for all files in the workspace.
    By default, filters out diagnostics from test files. Use --include-tests to include them.
    """
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = _resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    workspace_path = effective_workspace or str(Path.cwd())
    language_value = effective_language or "python"

    try:
        response = _send_request(
            "workspace/diagnostic",
            {"workspacePath": workspace_path},
            language=language_value,
        )

        diagnostics_items = response.get("diagnostics", [])

        # Apply test filtering if requested
        if not include_tests:
            diagnostics_items = _filter_test_diagnostic_items(
                diagnostics_items,
                include_tests=False,
                language=language_value,
            )

        # Flatten workspace diagnostics into a single list with file info
        all_records = []
        formatter = CompactFormatter(workspace_path)

        for item in diagnostics_items:
            uri = item.get("uri", "")
            file_diagnostics = item.get("diagnostics", [])
            # Convert URI to file path
            from urllib.parse import urlparse

            parsed = urlparse(uri)
            file_path = parsed.path if parsed.scheme == "file" else uri
            records = formatter.transform_diagnostics(file_diagnostics, file_path=file_path)
            all_records.extend(records)

        if effective_format == OutputFormat.TEXT:
            typer.echo(formatter.diagnostics_to_text(all_records))
        elif effective_format == OutputFormat.YAML:
            typer.echo(formatter.diagnostics_to_yaml(all_records), nl=False)
        elif effective_format == OutputFormat.CSV:
            typer.echo(formatter.diagnostics_to_csv(all_records), nl=False)
        else:  # JSON (default)
            typer.echo(formatter.diagnostics_to_json(all_records))

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
