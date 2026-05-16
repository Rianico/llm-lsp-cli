"""Shared utilities for CLI commands.

This module handles LSP response data for text output formatting.
Uses object for unknown data fields; specific types for known structures.
Typer's ctx.obj is typed as Any by design.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast, overload

import typer

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.exceptions import CLIError
from llm_lsp_cli.utils import OutputFormat, get_symbol_kind_name
from llm_lsp_cli.utils.language_detector import FILE_EXTENSION_MAP, detect_language_from_file
from llm_lsp_cli.utils.root_detector import (
    detect_workspace_and_language,
    format_unsupported_message,
)
from llm_lsp_cli.utils.type_helpers import (
    get_dict as _get_dict,
)
from llm_lsp_cli.utils.type_helpers import (
    get_int as _get_int,
)
from llm_lsp_cli.utils.type_helpers import (
    get_optional_dict as _get_optional_dict,
)
from llm_lsp_cli.utils.type_helpers import (
    get_optional_str as _get_optional_str,
)
from llm_lsp_cli.utils.type_helpers import (
    get_str as _get_str,
)

if TYPE_CHECKING:
    from llm_lsp_cli.daemon import DaemonManager

from pydantic import BaseModel as _BaseModel
from pydantic import TypeAdapter

from llm_lsp_cli.daemon import RESPONSE_KEYS
from llm_lsp_cli.ipc import (
    DaemonFileParams,
    DaemonPositionParams,
    DaemonRenameParams,
    DaemonSymbolQueryParams,
    DaemonWorkspaceParams,
)
from llm_lsp_cli.lsp.types import (
    CallHierarchyIncomingCall,
    CallHierarchyOutgoingCall,
    CompletionItem,
    DocumentSymbol,
    Hover,
    Location,
    PrepareRenameResult,
    SymbolInformation,
    WorkspaceEdit,
)


@dataclass
class GlobalOptions:
    """Global options shared across all subcommands."""

    workspace: str | None = None
    language: str | None = None
    output_format: OutputFormat = OutputFormat.JSON


def get_global_options(ctx: typer.Context) -> GlobalOptions:
    """Extract GlobalOptions from typer context with type safety.

    Args:
        ctx: Typer context containing global options in ctx.obj

    Returns:
        GlobalOptions instance, or default if not available
    """
    obj: object = cast(object, ctx.obj)
    if isinstance(obj, GlobalOptions):
        return obj
    return GlobalOptions()


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


def format_location_range(range_obj: object) -> str:
    """Format a location range from LSP response."""
    start = _get_dict(range_obj, "start")
    end = _get_dict(range_obj, "end")
    start_line = _get_int(start, "line", 0) + 1
    start_char = _get_int(start, "character", 0) + 1
    end_line = _get_int(end, "line", 0) + 1
    end_char = _get_int(end, "character", 0) + 1
    return f"{start_line}:{start_char}-{end_line}:{end_char}"


def format_locations_text(locations: object) -> None:
    """Format and print location list in text format."""
    if isinstance(locations, list) and locations:
        for loc in cast(list[object], locations):
            uri = _get_str(loc, "uri", "")
            range_obj = _get_dict(loc, "range")
            range_str = format_location_range(range_obj)
            typer.echo(f"{uri}:{range_str}")
    else:
        typer.echo("No locations found.")


def format_completions_text(items: object) -> None:
    """Format and print completion items in text format."""
    if isinstance(items, list) and items:
        for item in cast(list[object], items):
            label = _get_str(item, "label", "")
            detail = _get_optional_str(item, "detail") or ""
            range_info = ""
            text_edit = _get_optional_dict(item, "textEdit")
            if text_edit:
                range_obj = _get_optional_dict(text_edit, "range")
                if range_obj:
                    range_info = f" [{format_location_range(range_obj)}]"

            if detail:
                typer.echo(f"{label} - {detail}{range_info}")
            else:
                typer.echo(f"{label}{range_info}")
    else:
        typer.echo("No completions found.")


def format_hover_text(hover: object) -> None:
    """Format and print hover information in text format."""
    if hover is not None:
        contents = _get_dict(hover, "contents")
        value = _get_str(contents, "value", "") if contents else str(hover)
        range_obj = _get_optional_dict(hover, "range")
        if range_obj:
            range_str = format_location_range(range_obj)
            typer.echo(f"[{range_str}] {value}")
        else:
            typer.echo(value)
    else:
        typer.echo("No hover information available.")


def format_workspace_symbols_text(symbols: object) -> None:
    """Format and print workspace symbol list in text format."""
    if isinstance(symbols, list) and symbols:
        for sym in cast(list[object], symbols):
            name = _get_str(sym, "name", "")
            kind = _get_int(sym, "kind", 0)
            kind_name = get_symbol_kind_name(kind)
            location = _get_dict(sym, "location")
            uri = _get_str(location, "uri", "")
            range_info = ""
            range_obj = _get_optional_dict(location, "range")
            if range_obj:
                range_info = f" [{format_location_range(range_obj)}]"
            typer.echo(f"{name} ({kind_name}) in {uri}{range_info}")
    else:
        typer.echo("No symbols found.")


def resolve_workspace_path(workspace: str | None) -> str:
    """Resolve workspace path, defaulting to cwd if not specified."""
    return str(Path(workspace).resolve()) if workspace else str(Path.cwd().resolve())


def resolve_language(
    workspace: str | None, language: str | None
) -> tuple[str, str | None, list[str]]:
    """Resolve workspace path and language.

    Returns:
        Tuple of (workspace_path, language_or_none, available_languages).
        Language is None when no language can be detected and none provided.
        Available languages are returned for error messaging without extra config load.
    """
    from llm_lsp_cli.config import ConfigManager
    from llm_lsp_cli.utils.language_detector import FILE_EXTENSION_MAP

    # Get language configs with root_markers from typed config
    language_configs: dict[str, dict[str, object]] = {}
    try:
        config_obj = ConfigManager.load()
        if config_obj:
            for lang_name, lang_conf in config_obj.languages.items():
                language_configs[lang_name] = {"root_markers": lang_conf.root_markers}
    except Exception:
        pass

    # Extract available languages before processing
    available_languages = list(language_configs.keys())

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

    # Return workspace path, language (may be None), and available languages
    return str(workspace_path), detected_language, available_languages


def _format_no_language_message(available_languages: list[str]) -> str:
    """Format error when no language detected.

    Args:
        available_languages: List of supported language names.

    Returns:
        Formatted error message with available languages.
    """
    langs_str = ", ".join(sorted(available_languages)) if available_languages else "none configured"
    return (
        f"No language detected in workspace. "
        f"Supported languages: {langs_str}. "
        f"Use --language to specify explicitly."
    )


def require_language_or_detect(workspace: str | None, language: str | None) -> tuple[str, str]:
    """Resolve language or fail with helpful message.

    Args:
        workspace: Optional workspace path
        language: Optional explicit language

    Returns:
        Tuple of (workspace_path, language)

    Raises:
        CLIError: When no language can be detected
    """
    workspace_path, detected_language, available_languages = resolve_language(workspace, language)

    if detected_language is None:
        raise CLIError(_format_no_language_message(available_languages))

    return workspace_path, detected_language


def validate_file_in_workspace(file: str, workspace: str | None) -> Path:
    """Validate file exists and is within workspace boundary."""
    workspace_path = resolve_workspace_path(workspace)
    file_path = Path(file).resolve()
    workspace_resolved = Path(workspace_path).resolve()

    try:
        _ = file_path.relative_to(workspace_resolved)
    except ValueError:
        typer.echo(
            (
                f"Error: File path escapes workspace boundary: {file_path}\n"
                f"Workspace: {workspace_resolved}"
            ),
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
    global_opts = get_global_options(ctx)
    effective_workspace, effective_language, effective_format = resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    # Get language configs with root_markers from typed config
    language_configs: dict[str, dict[str, object]] = {}
    try:
        config_obj = ConfigManager.load()
        if config_obj:
            for lang_name, lang_conf in config_obj.languages.items():
                language_configs[lang_name] = {"root_markers": lang_conf.root_markers}
    except Exception:
        pass

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


def _get_daemon_log_path(error: Exception, workspace_path: str, language: str) -> str:
    """Extract log path from daemon error or build default path."""
    log_file: object = getattr(error, "log_file", None)
    if log_file:
        return str(log_file)
    return str(ConfigManager.build_daemon_log_path(workspace_path, language))


def _handle_daemon_error(error: Exception, workspace_path: str, language: str) -> CLIError:
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
            + "Ensure the daemon is running: llm-lsp-cli daemon status"
        )
    if isinstance(error, OSError):
        return CLIError(
            f"Cannot connect to daemon: {error}\n"
            + "Ensure the daemon is running: llm-lsp-cli daemon start"
        )
    return CLIError(str(error))


# =============================================================================
# send_request overloads and implementation (ADR-0028)
# =============================================================================


@overload
def send_request(
    method: Literal["textDocument/definition"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> list[Location]: ...


@overload
def send_request(
    method: Literal["textDocument/hover"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> Hover | None: ...


@overload
def send_request(
    method: Literal["textDocument/documentSymbol"],
    params: DaemonFileParams,
    language: str | None = None,
) -> list[DocumentSymbol]: ...


@overload
def send_request(
    method: Literal["textDocument/completion"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> list[CompletionItem] | None: ...


@overload
def send_request(
    method: Literal["textDocument/references"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> list[Location]: ...


@overload
def send_request(
    method: Literal["textDocument/prepareRename"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> PrepareRenameResult: ...


@overload
def send_request(
    method: Literal["textDocument/rename"],
    params: DaemonRenameParams,
    language: str | None = None,
) -> WorkspaceEdit: ...


@overload
def send_request(
    method: Literal["workspace/symbol"],
    params: DaemonSymbolQueryParams,
    language: str | None = None,
) -> list[SymbolInformation]: ...


@overload
def send_request(
    method: Literal["textDocument/diagnostic"],
    params: DaemonFileParams,
    language: str | None = None,
) -> dict[str, object]: ...


@overload
def send_request(
    method: Literal["workspace/diagnostic"],
    params: DaemonWorkspaceParams,
    language: str | None = None,
) -> dict[str, object]: ...


@overload
def send_request(
    method: Literal["callHierarchy/incomingCalls"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> list[CallHierarchyIncomingCall]: ...


@overload
def send_request(
    method: Literal["callHierarchy/outgoingCalls"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> list[CallHierarchyOutgoingCall]: ...


@overload
def send_request(
    method: Literal["textDocument/didChange"],
    params: DaemonFileParams,
    language: str | None = None,
) -> None: ...


@overload
def send_request(
    method: str,
    params: object,
    language: str | None = None,
) -> object: ...


def send_request(
    method: str,
    params: object,
    language: str | None = None,
) -> object:
    """Send a request to the daemon and return the typed response.

    This function serves as a typed gateway at the CLI-IPC boundary:
    - Accepts daemon RPC param models (DaemonPositionParams, etc.)
    - Serializes BaseModel params to flat camelCase dicts
    - Unwraps response dicts using RESPONSE_KEYS
    - Validates inner values with Pydantic models
    - Returns typed results for overload-matched methods

    Args:
        method: LSP method name (e.g., "textDocument/definition")
        params: Either a BaseModel (daemon RPC params) or dict[str, object]
        language: Optional language override

    Returns:
        Typed result based on method overload, or object for unknown methods
    """
    from llm_lsp_cli.daemon_client import DaemonClient
    from llm_lsp_cli.ipc.method_registry import MethodName

    # Extract workspace_path and detect language
    file_path: str | None
    if isinstance(params, (DaemonPositionParams, DaemonFileParams)):
        workspace_path = params.workspace_path
        file_path = params.file_path
    elif isinstance(params, DaemonWorkspaceParams):
        workspace_path = params.workspace_path
        file_path = None
    elif isinstance(params, _BaseModel):
        # Fallback for other BaseModel types (shouldn't happen with current models)
        workspace_path = str(Path.cwd())
        file_path = None
    else:
        # Extract from dict
        params_dict = cast("dict[str, object]", params) if isinstance(params, dict) else {}
        workspace_path_val = params_dict.get("workspacePath", str(Path.cwd()))
        workspace_path = str(workspace_path_val) if workspace_path_val else str(Path.cwd())
        file_path_val = params_dict.get("filePath")
        file_path = str(file_path_val) if file_path_val else None
        if language is None:
            language = detect_language_from_file(file_path) if file_path else "python"

    if isinstance(params, _BaseModel) and language is None and file_path:
        language = detect_language_from_file(str(file_path))

    language = language or "python"

    # Serialize params for daemon
    if isinstance(params, _BaseModel):
        serialized_params = params.model_dump(mode="json", by_alias=True)
    elif isinstance(params, dict):
        serialized_params = cast("dict[str, object]", params)
    else:
        serialized_params = {}

    client = DaemonClient(
        workspace_path=str(workspace_path),
        language=language,
    )

    async def send() -> object:
        try:
            result = await client.request(cast(MethodName, method), serialized_params)
            if not isinstance(result, dict):
                return result

            # Cast to dict[str, object] after isinstance check
            result_dict = cast(dict[str, object], result)

            # textDocument/didChange returns None (acknowledgment only, no data needed)
            if method == "textDocument/didChange":
                return None

            # Methods that always keep dict returns (diagnostics)
            if method in (
                "textDocument/diagnostic",
                "workspace/diagnostic",
            ):
                return result_dict

            # Only validate when typed params (BaseModel) are used.
            # Dict params maintain backward compatibility with raw responses.
            if isinstance(params, _BaseModel):
                # Unwrap response using RESPONSE_KEYS
                response_key = RESPONSE_KEYS.get(method, "result")
                inner_value = result_dict.get(response_key)
                # Validate and return typed result
                return _validate_response(method, inner_value)

            # Dict params: return raw response for backward compat
            return result_dict

        except Exception as e:
            raise _handle_daemon_error(e, str(workspace_path), language) from e
        finally:
            await client.close()

    return asyncio.run(send())


def _validate_response(method: str, inner_value: object) -> object:
    """Validate inner response value with appropriate Pydantic model.

    Args:
        method: LSP method name
        inner_value: The unwrapped inner value from daemon response

    Returns:
        Validated Pydantic model or list of models

    Raises:
        ValidationError: If validation fails (no silent fallback)
    """
    # Map methods to their result types
    # Note: Some methods return lists, some return single items, some return None
    if inner_value is None:
        return None

    # Single-item returns
    single_item_types: dict[str, type[_BaseModel]] = {
        "textDocument/hover": Hover,
        "textDocument/prepareRename": PrepareRenameResult,
        "textDocument/rename": WorkspaceEdit,
    }

    # List-item returns
    list_item_types: dict[str, type[_BaseModel]] = {
        "textDocument/definition": Location,
        "textDocument/references": Location,
        "textDocument/completion": CompletionItem,
        "textDocument/documentSymbol": DocumentSymbol,
        "workspace/symbol": SymbolInformation,
        "callHierarchy/incomingCalls": CallHierarchyIncomingCall,
        "callHierarchy/outgoingCalls": CallHierarchyOutgoingCall,
    }

    if method in single_item_types:
        model_type = single_item_types[method]
        adapter = TypeAdapter(model_type)
        return adapter.validate_python(inner_value)

    if method in list_item_types:
        if not isinstance(inner_value, list):
            return inner_value
        model_type = list_item_types[method]
        adapter = TypeAdapter(list[model_type])  # type: ignore[valid-type]
        return adapter.validate_python(inner_value)

    # Unknown method - return as-is
    return inner_value


def send_notification(
    method: str,
    params: dict[str, object],
    language: str | None = None,
) -> None:
    """Send a notification to the daemon (no response expected)."""
    from llm_lsp_cli.daemon_client import DaemonClient

    workspace_path_val = params.get("workspacePath", str(Path.cwd()))
    workspace_path = str(workspace_path_val) if workspace_path_val else str(Path.cwd())

    if language is None:
        file_path_val = params.get("filePath")
        file_path = str(file_path_val) if file_path_val else None
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
    response: object,
    output_format: OutputFormat,
    text_formatter: Callable[[object], None],
    csv_formatter: Callable[[object], str] | None = None,
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
) -> DaemonManager:
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
    action_fn: Callable[[DaemonManager, str, str], None] | None = None,
    ctx: typer.Context | None = None,
) -> None:
    """Execute a daemon lifecycle command with consistent logging."""
    if ctx is not None:
        global_opts = get_global_options(ctx)
        effective_workspace = workspace if workspace is not None else global_opts.workspace
        effective_language = language if language is not None else global_opts.language
    else:
        effective_workspace = workspace
        effective_language = language

    workspace_path, detected_language = require_language_or_detect(
        effective_workspace, effective_language
    )
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
            log_path = getattr(e, "log_file", None) or str(manager.daemon_log_file)
            typer.echo(f"[{command_name}] Failed: {e}", err=True)
            typer.echo(f"[{command_name}] Check logs at: {log_path}", err=True)
            raise typer.Exit(1) from e
