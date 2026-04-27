"""LSP commands for llm-lsp-cli."""

from __future__ import annotations

from pathlib import Path

import typer

from llm_lsp_cli.commands.shared import (
    GlobalOptions,
    build_request_context,
    resolve_effective_options,
    resolve_workspace_path,
    send_notification,
    send_request,
    validate_file_in_workspace,
)
from llm_lsp_cli.exceptions import CLIError
from llm_lsp_cli.lsp.constants import LSPConstants
from llm_lsp_cli.output.dispatcher import OutputDispatcher
from llm_lsp_cli.output.formatter import CompactFormatter
from llm_lsp_cli.output.raw_formatter import RawFormatter
from llm_lsp_cli.test_filter import (
    _filter_test_diagnostic_items,
    _filter_test_locations,
    _filter_test_symbols,
)
from llm_lsp_cli.utils import OutputFormat
from llm_lsp_cli.utils.language_detector import detect_language_from_file

app = typer.Typer(name="lsp", help="LSP operations for code intelligence.")


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
    """Get definition location for symbol at position."""
    context = build_request_context(
        ctx, workspace, language, output_format, file, line, column, include_tests=include_tests
    )

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = send_request(
            LSPConstants.DEFINITION,
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

        formatter = CompactFormatter(context.workspace_path)
        records = formatter.transform_locations(filtered)
        dispatcher = OutputDispatcher()
        typer.echo(dispatcher.format_list(records, context.output_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


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
    raw: bool = typer.Option(False, "--raw", help="original LSP server response"),
) -> None:
    """Get references to symbol at position."""
    context = build_request_context(
        ctx, workspace, language, output_format, file, line, column, include_tests=include_tests
    )

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = send_request(
            LSPConstants.REFERENCES,
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
            raw_formatter = RawFormatter(context.workspace_path)
            typer.echo(raw_formatter.format(response, context.output_format))
        else:
            formatter = CompactFormatter(context.workspace_path)
            records = formatter.transform_locations(filtered)
            dispatcher = OutputDispatcher()
            typer.echo(dispatcher.format_list(records, context.output_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("document-symbol")
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
    depth: int = typer.Option(1, "--depth", "-d", help="Hierarchy depth"),
    raw: bool = typer.Option(False, "--raw", help="original LSP server response"),
) -> None:
    """Get document symbols."""
    context = build_request_context(ctx, workspace, language, output_format, file)

    try:
        response = send_request(
            LSPConstants.DOCUMENT_SYMBOL,
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
            },
            language=context.language,
        )

        symbols = response.get("symbols", [])

        if raw:
            raw_formatter = RawFormatter(context.workspace_path)
            typer.echo(raw_formatter.format(response, context.output_format))
        elif context.output_format == OutputFormat.TEXT:
            from llm_lsp_cli.output.symbol_transformer import transform_symbols
            from llm_lsp_cli.output.text_renderer import render_text

            nodes = transform_symbols(
                symbols, depth_limit=depth, workspace=Path(context.workspace_path)
            )
            file_header = f"{context.file_path}:" if context.file_path else None
            typer.echo(render_text(nodes, file_header=file_header))
        else:
            formatter = CompactFormatter(context.workspace_path)
            records = formatter.transform_symbols(symbols, depth=depth)
            dispatcher = OutputDispatcher()
            typer.echo(dispatcher.format_list(records, context.output_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("workspace-symbol")
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
    depth: int = typer.Option(1, "--depth", "-d", help="Hierarchy depth"),
    raw: bool = typer.Option(False, "--raw", help="original LSP server response"),
) -> None:
    """Search workspace symbols."""
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    workspace_path = resolve_workspace_path(effective_workspace)
    language_value = effective_language or "python"

    try:
        response = send_request(
            LSPConstants.WORKSPACE_SYMBOL,
            {"workspacePath": workspace_path, "query": query},
            language=language_value,
        )

        symbols = response.get("symbols", [])
        filtered = _filter_test_symbols(symbols, include_tests=include_tests)

        if raw:
            raw_formatter = RawFormatter(workspace_path)
            typer.echo(raw_formatter.format(response, effective_format))
        else:
            formatter = CompactFormatter(workspace_path)
            records = formatter.transform_symbols(filtered, depth=depth)
            dispatcher = OutputDispatcher()
            typer.echo(dispatcher.format_list(records, effective_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("incoming-calls")
def incoming_calls(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (1-based)"),
    column: int = typer.Argument(..., help="Column number (1-based)"),
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
    raw: bool = typer.Option(False, "--raw", help="original LSP server response"),
) -> None:
    """Get incoming calls (callers) for symbol at position."""
    context = build_request_context(
        ctx, workspace, language, output_format, file, line, column, include_tests=include_tests
    )

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = send_request(
            LSPConstants.CALL_HIERARCHY_INCOMING_CALLS,
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
                "line": line_index,
                "column": column_index,
            },
            language=context.language,
        )

        calls = response.get("calls", [])

        if raw:
            raw_formatter = RawFormatter(context.workspace_path)
            typer.echo(raw_formatter.format(response, context.output_format))
        else:
            formatter = CompactFormatter(context.workspace_path)
            records = formatter.transform_call_hierarchy_incoming(calls)
            if not records:
                typer.echo("No calls found.")
            else:
                dispatcher = OutputDispatcher()
                typer.echo(dispatcher.format_list(records, context.output_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("outgoing-calls")
def outgoing_calls(
    ctx: typer.Context,
    file: str = typer.Argument(..., help="File path"),
    line: int = typer.Argument(..., help="Line number (1-based)"),
    column: int = typer.Argument(..., help="Column number (1-based)"),
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
    raw: bool = typer.Option(False, "--raw", help="original LSP server response"),
) -> None:
    """Get outgoing calls (callees) for symbol at position."""
    context = build_request_context(
        ctx, workspace, language, output_format, file, line, column, include_tests=include_tests
    )

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = send_request(
            LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS,
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
                "line": line_index,
                "column": column_index,
            },
            language=context.language,
        )

        calls = response.get("calls", [])

        if raw:
            raw_formatter = RawFormatter(context.workspace_path)
            typer.echo(raw_formatter.format(response, context.output_format))
        else:
            formatter = CompactFormatter(context.workspace_path)
            records = formatter.transform_call_hierarchy_outgoing(calls)
            if not records:
                typer.echo("No calls found.")
            else:
                dispatcher = OutputDispatcher()
                typer.echo(dispatcher.format_list(records, context.output_format))

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
    context = build_request_context(ctx, workspace, language, output_format, file, line, column)

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = send_request(
            LSPConstants.COMPLETION,
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
                "line": line_index,
                "column": column_index,
            },
            language=context.language,
        )

        items = response.get("items", [])
        formatter = CompactFormatter(context.workspace_path)
        records = formatter.transform_completions(items, file_path=str(context.file_path))
        dispatcher = OutputDispatcher()
        typer.echo(dispatcher.format_list(records, context.output_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


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
    context = build_request_context(ctx, workspace, language, output_format, file, line, column)

    line_index = context.line - 1 if context.line else 0
    column_index = context.column - 1 if context.column else 0

    try:
        response = send_request(
            LSPConstants.HOVER,
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
                "line": line_index,
                "column": column_index,
            },
            language=context.language,
        )

        hover_data = response.get("hover")
        formatter = CompactFormatter(context.workspace_path)
        record = formatter.transform_hover(hover_data, file_path=str(context.file_path))
        if record:
            dispatcher = OutputDispatcher()
            typer.echo(dispatcher.format(record, context.output_format))
        else:
            typer.echo("No hover information available.")

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
    """Get diagnostics for a single file."""
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    if effective_language is None:
        effective_language = detect_language_from_file(file)

    workspace_path = resolve_workspace_path(effective_workspace)
    file_path = validate_file_in_workspace(file, effective_workspace)

    try:
        response = send_request(
            LSPConstants.DIAGNOSTIC,
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
            },
            language=effective_language or "python",
        )

        diagnostics_list = response.get("diagnostics", [])
        formatter = CompactFormatter(workspace_path)
        records = formatter.transform_diagnostics(diagnostics_list, file_path=str(file_path))
        dispatcher = OutputDispatcher()
        typer.echo(dispatcher.format_list(records, effective_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("workspace-diagnostics")
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
    """Get diagnostics for entire workspace."""
    global_opts: GlobalOptions = ctx.obj
    effective_workspace, effective_language, effective_format = resolve_effective_options(
        global_opts, workspace, language, output_format
    )

    workspace_path = resolve_workspace_path(effective_workspace)
    language_value = effective_language or "python"

    try:
        response = send_request(
            LSPConstants.WORKSPACE_DIAGNOSTIC,
            {"workspacePath": workspace_path},
            language=language_value,
        )

        diagnostics_items = response.get("diagnostics", [])

        if not include_tests:
            diagnostics_items = _filter_test_diagnostic_items(
                diagnostics_items, include_tests=False, language=language_value
            )

        all_records = []
        formatter = CompactFormatter(workspace_path)

        for item in diagnostics_items:
            uri = item.get("uri", "")
            file_diagnostics = item.get("diagnostics", [])
            from urllib.parse import urlparse

            parsed = urlparse(uri)
            file_path = parsed.path if parsed.scheme == "file" else uri
            records = formatter.transform_diagnostics(file_diagnostics, file_path=file_path)
            all_records.extend(records)

        dispatcher = OutputDispatcher()
        typer.echo(dispatcher.format_list(all_records, effective_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def rename(
    ctx: typer.Context,
    file: str = typer.Argument(None, help="File path"),
    line: int = typer.Argument(None, help="Line number (1-based)"),
    column: int = typer.Argument(None, help="Column number (1-based)"),
    new_name: str = typer.Argument(None, help="New symbol name"),
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
    apply: bool = typer.Option(False, "--apply", help="Apply changes to files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Explicit dry-run"),
    rollback: str | None = typer.Option(None, "--rollback", help="Session ID to rollback"),
) -> None:
    """Rename symbol at position across workspace."""
    from llm_lsp_cli.domain.services.backup_manager import BackupManager
    from llm_lsp_cli.domain.services.rename_service import RenameService
    from llm_lsp_cli.output.formatter import Position

    if not rollback:
        if file is None:
            typer.echo("Error: Missing argument 'FILE'.", err=True)
            raise typer.Exit(1)
        if line is None:
            typer.echo("Error: Missing argument 'LINE'.", err=True)
            raise typer.Exit(1)
        if column is None:
            typer.echo("Error: Missing argument 'COLUMN'.", err=True)
            raise typer.Exit(1)
        if new_name is None:
            typer.echo("Error: Missing argument 'NEW_NAME'.", err=True)
            raise typer.Exit(1)

    context = build_request_context(ctx, workspace, language, output_format, file, line, column)

    if rollback:
        try:
            backup_manager = BackupManager(Path(context.workspace_path))
            backup_manager.restore_by_id(rollback)
            typer.echo(f"Rollback completed for session: {rollback}")
            return
        except Exception as e:
            typer.echo(f"Error during rollback: {e}", err=True)
            raise typer.Exit(1) from e

    try:
        response = send_request(
            LSPConstants.RENAME,
            {
                "workspacePath": context.workspace_path,
                "filePath": str(context.file_path),
                "line": context.line - 1 if context.line else 0,
                "column": context.column - 1 if context.column else 0,
                "newName": new_name,
            },
            language=context.language,
        )

        workspace_edit = response.get("workspace_edit")
        backup_manager = BackupManager(Path(context.workspace_path))
        rename_service = RenameService(backup_manager)
        position = Position(
            line=context.line - 1 if context.line else 0,
            character=context.column - 1 if context.column else 0,
        )

        if apply:
            records, session = rename_service.apply_from_edit(
                workspace_edit=workspace_edit,
                file_path=str(context.file_path),
                position=position,
                new_name=new_name,
            )
            if not records:
                typer.echo("No rename changes found.")
                return
            dispatcher = OutputDispatcher()
            typer.echo(dispatcher.format_list(records, context.output_format))
            typer.echo(f"Session ID: {session.session_id}", err=True)
        else:
            records = rename_service.preview_from_edit(
                workspace_edit=workspace_edit,
                file_path=str(context.file_path),
                position=position,
                new_name=new_name,
            )
            if not records:
                typer.echo("No rename changes found.")
                return
            dispatcher = OutputDispatcher()
            typer.echo(dispatcher.format_list(records, context.output_format))

    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("did-change")
def did_change(
    file: str = typer.Argument(..., help="File path"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path (overrides global)"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Language (overrides global)"
    ),
) -> None:
    """Notify the LSP server of an external file change."""
    workspace_path = resolve_workspace_path(workspace)

    if language is None:
        language = detect_language_from_file(file)

    file_path = validate_file_in_workspace(file, workspace)

    try:
        send_notification(
            LSPConstants.TEXT_DOCUMENT_DID_CHANGE,
            {
                "workspacePath": workspace_path,
                "filePath": str(file_path),
            },
            language=language or "python",
        )
        typer.echo("Change acknowledged.")
    except CLIError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
