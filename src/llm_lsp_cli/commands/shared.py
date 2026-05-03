"""Shared utilities for CLI commands."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.exceptions import CLIError
from llm_lsp_cli.utils import OutputFormat, get_symbol_kind_name
from llm_lsp_cli.utils.language_detector import FILE_EXTENSION_MAP, detect_language_from_file
from llm_lsp_cli.utils.root_detector import (
    detect_workspace_and_language,
    format_unsupported_message,
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


def resolve_effective_options(
    global_opts: GlobalOptions,
    workspace: str | None = None,
    language: str | None = None,
    output_format: OutputFormat | None = None,
) -> tuple[str | None, str | None, OutputFormat]:
    """Resolve effective options from global and local overrides."""
    effective_workspace = workspace if workspace is not None else global_opts.workspace
    effective_language = language if language is not None else global_opts.language
    effective_format = output_format if output_format is not None else global_opts.output_format
    return effective_workspace, effective_language, effective_format


def format_location_range(range_obj: dict[str, Any]) -> str:
    """Format a location range from LSP response."""
    start = range_obj.get("start", {})
    end = range_obj.get("end", {})
    start_line = start.get("line", 0) + 1
    start_char = start.get("character", 0) + 1
    end_line = end.get("line", 0) + 1
    end_char = end.get("character", 0) + 1
    return f"{start_line}:{start_char}-{end_line}:{end_char}"


def format_locations_text(locations: list[dict[str, Any]]) -> None:
    """Format and print location list in text format."""
    if locations:
        for loc in locations:
            uri = loc.get("uri", "")
            range_obj = loc.get("range", {})
            range_str = format_location_range(range_obj)
            typer.echo(f"{uri}:{range_str}")
    else:
        typer.echo("No locations found.")


def format_completions_text(items: list[dict[str, Any]]) -> None:
    """Format and print completion items in text format."""
    if items:
        for item in items:
            label = item.get("label", "")
            detail = item.get("detail", "")
            range_info = ""
            text_edit = item.get("textEdit", {})
            if text_edit and isinstance(text_edit, dict):
                range_obj = text_edit.get("range", {})
                if range_obj:
                    range_info = f" [{format_location_range(range_obj)}]"

            if detail:
                typer.echo(f"{label} - {detail}{range_info}")
            else:
                typer.echo(f"{label}{range_info}")
    else:
        typer.echo("No completions found.")


def format_hover_text(hover: dict[str, Any] | None) -> None:
    """Format and print hover information in text format."""
    if hover:
        contents = hover.get("contents", {})
        value = contents.get("value", "") if isinstance(contents, dict) else str(contents)
        range_obj = hover.get("range", {})
        if range_obj:
            range_str = format_location_range(range_obj)
            typer.echo(f"[{range_str}] {value}")
        else:
            typer.echo(value)
    else:
        typer.echo("No hover information available.")


def format_workspace_symbols_text(symbols: list[dict[str, Any]]) -> None:
    """Format and print workspace symbol list in text format."""
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
                range_info = f" [{format_location_range(range_obj)}]"
            typer.echo(f"{name} ({kind_name}) in {uri}{range_info}")
    else:
        typer.echo("No symbols found.")


def resolve_workspace_path(workspace: str | None) -> str:
    """Resolve workspace path, defaulting to cwd if not specified."""
    return str(Path(workspace).resolve()) if workspace else str(Path.cwd().resolve())


def resolve_language(workspace: str | None, language: str | None) -> tuple[str, str]:
    """Resolve workspace path and language, returning (workspace_path, language)."""
    from llm_lsp_cli.config import ConfigManager
    from llm_lsp_cli.utils.language_detector import FILE_EXTENSION_MAP

    # Get language configs with root_markers
    try:
        config_obj = ConfigManager.load()
        config = config_obj.model_dump(mode="json") if config_obj else {}
    except Exception:
        config = {}

    language_configs: dict[str, dict[str, Any]] = {}
    for lang_name, lang_conf in config.get("languages", {}).items():
        if isinstance(lang_conf, dict):
            language_configs[lang_name] = {
                "root_markers": lang_conf.get("root_markers", [])
            }

    # Build extension map from FILE_EXTENSION_MAP
    extension_map = dict(FILE_EXTENSION_MAP)

    # Detect workspace and language
    workspace_path, detected_language = detect_workspace_and_language(
        file_path=None,
        explicit_workspace=workspace,
        explicit_language=language,
        language_configs=language_configs,
        extension_map=extension_map,
    )

    # Return as strings for backward compatibility
    return str(workspace_path), detected_language or "python"


def validate_file_in_workspace(file: str, workspace: str | None) -> Path:
    """Validate file exists and is within workspace boundary."""
    workspace_path = resolve_workspace_path(workspace)
    file_path = Path(file).resolve()
    workspace_resolved = Path(workspace_path).resolve()

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


def build_request_context(
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
    """Build a request context from command arguments."""
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    # Get language configs with root_markers (needed for detection)
    try:
        config_obj = ConfigManager.load()
        config = config_obj.model_dump(mode="json") if config_obj else {}
    except Exception:
        config = {}

    language_configs: dict[str, dict[str, Any]] = {}
    for lang_name, lang_conf in config.get("languages", {}).items():
        if isinstance(lang_conf, dict):
            language_configs[lang_name] = {
                "root_markers": lang_conf.get("root_markers", [])
            }

    # Use detect_workspace_and_language for proper detection flow
    if effective_language is None or effective_workspace is None:
        detected_workspace, detected_language = detect_workspace_and_language(
            file_path=file,
            explicit_workspace=effective_workspace,
            explicit_language=effective_language,
            language_configs=language_configs,
            extension_map=dict(FILE_EXTENSION_MAP),
        )

        if effective_workspace is None:
            effective_workspace = str(detected_workspace)
        if effective_language is None:
            effective_language = detected_language

    # Handle unsupported file type
    if effective_language is None:
        available_languages = list(language_configs.keys())
        typer.echo(format_unsupported_message(None, available_languages))
        raise typer.Exit(0)

    if effective_workspace:
        workspace_path = str(Path(effective_workspace).resolve())
    else:
        workspace_path = str(Path.cwd().resolve())
    file_path = validate_file_in_workspace(file, effective_workspace) if file else None

    return RequestContext(
        workspace_path=workspace_path,
        language=effective_language,
        output_format=effective_format,
        file_path=file_path,
        line=line,
        column=column,
        query=query,
        include_tests=include_tests,
    )


def _get_daemon_log_path(
    error: Exception, workspace_path: str, language: str
) -> str:
    """Extract log path from daemon error or build default path."""
    log_file = getattr(error, 'log_file', None)
    if log_file:
        return str(log_file)
    return str(ConfigManager.build_daemon_log_path(workspace_path, language))


def _handle_daemon_error(
    error: Exception, workspace_path: str, language: str
) -> CLIError:
    """Convert daemon errors to CLI errors with log paths."""
    from llm_lsp_cli.exceptions import DaemonCrashedError, DaemonStartupError

    if isinstance(error, DaemonStartupError):
        log_path = _get_daemon_log_path(error, workspace_path, language)
        return CLIError(f"Failed to start daemon: {error}\nCheck logs at: {log_path}")
    if isinstance(error, DaemonCrashedError):
        log_path = _get_daemon_log_path(error, workspace_path, language)
        return CLIError(f"Daemon crashed: {error}\nCheck logs at: {log_path}")
    if isinstance(error, FileNotFoundError):
        return CLIError(
            "Cannot connect to daemon. Socket not found.\n"
            "Ensure the daemon is running: llm-lsp-cli daemon status"
        )
    if isinstance(error, OSError):
        return CLIError(
            f"Cannot connect to daemon: {error}\n"
            "Ensure the daemon is running: llm-lsp-cli daemon start"
        )
    return CLIError(str(error))


def send_request(
    method: str,
    params: dict[str, Any],
    language: str | None = None,
) -> Any:
    """Send a request to the daemon and return the response."""
    from llm_lsp_cli.daemon_client import DaemonClient

    workspace_path = params.get("workspacePath", str(Path.cwd()))

    if language is None:
        file_path = params.get("filePath")
        language = detect_language_from_file(file_path) if file_path else "python"

    client = DaemonClient(
        workspace_path=workspace_path,
        language=language,
    )

    async def send() -> Any:
        try:
            return await client.request(method, params)
        except Exception as e:
            raise _handle_daemon_error(e, workspace_path, language) from e
        finally:
            await client.close()

    return asyncio.run(send())


def send_notification(
    method: str,
    params: dict[str, Any],
    language: str | None = None,
) -> None:
    """Send a notification to the daemon (no response expected)."""
    from llm_lsp_cli.daemon_client import DaemonClient

    workspace_path = params.get("workspacePath", str(Path.cwd()))

    if language is None:
        file_path = params.get("filePath")
        language = detect_language_from_file(file_path) if file_path else "python"

    client = DaemonClient(workspace_path=workspace_path, language=language)

    async def send() -> None:
        try:
            await client.send_notification(method, params)
        except Exception as e:
            raise _handle_daemon_error(e, workspace_path, language) from e
        finally:
            await client.close()

    asyncio.run(send())


def output_result(
    response: Any,
    output_format: OutputFormat,
    text_formatter: Callable[[Any], None],
    csv_formatter: Callable[[Any], str] | None = None,
) -> None:
    """Output response in the specified format."""
    from llm_lsp_cli.utils import format_output

    if output_format == OutputFormat.YAML:
        typer.echo(format_output(response, output_format), nl=False)
    elif output_format == OutputFormat.JSON:
        typer.echo(format_output(response, output_format))
    elif output_format == OutputFormat.CSV and csv_formatter:
        typer.echo(csv_formatter(response), nl=False)
    else:
        text_formatter(response)


def get_lsp_server_name(language: str) -> str:
    """Get the LSP server name for a language."""
    return ConfigManager.get_lsp_server_name(language)


def create_daemon_manager(
    workspace_path: str,
    language: str,
    lsp_conf: str | None = None,
    debug: bool = False,
    trace: bool = False,
) -> Any:
    """Create a DaemonManager instance."""
    from llm_lsp_cli.daemon import DaemonManager

    return DaemonManager(
        workspace_path=workspace_path,
        language=language,
        lsp_conf=lsp_conf,
        debug=debug,
        trace=trace,
    )


def run_daemon_command(
    command_name: str,
    workspace: str | None,
    language: str | None,
    lsp_conf: str | None,
    debug: bool = False,
    trace: bool = False,
    check_running: bool | None = None,
    action_fn: Callable[[Any, str, str], None] | None = None,
    ctx: typer.Context | None = None,
) -> None:
    """Execute a daemon lifecycle command with consistent logging."""
    if ctx is not None and ctx.obj is not None:
        global_opts: GlobalOptions = ctx.obj
        effective_workspace = workspace if workspace is not None else global_opts.workspace
        effective_language = language if language is not None else global_opts.language
    else:
        effective_workspace = workspace
        effective_language = language

    workspace_path, detected_language = resolve_language(effective_workspace, effective_language)
    manager = create_daemon_manager(workspace_path, detected_language, lsp_conf, debug, trace)

    is_running = manager.is_running()
    if check_running is True and not is_running:
        typer.echo(f"[{command_name}] Daemon is not running.", err=True)
        raise typer.Exit(0)
    if check_running is False and is_running:
        typer.echo("Error: Daemon is already running.", err=True)
        raise typer.Exit(1)

    if language is None:
        typer.echo(f"[{command_name}] Detected language: {detected_language}", err=True)

    if action_fn:
        try:
            action_fn(manager, command_name, detected_language)
        except Exception as e:
            log_path = getattr(e, 'log_file', None) or str(manager.daemon_log_file)
            typer.echo(f"[{command_name}] Failed: {e}", err=True)
            typer.echo(f"[{command_name}] Check logs at: {log_path}", err=True)
            raise typer.Exit(1) from e
