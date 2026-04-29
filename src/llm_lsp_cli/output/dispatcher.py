"""Output dispatcher for unified format handling."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import Any

import yaml

from llm_lsp_cli.output.protocol import FormattableRecord
from llm_lsp_cli.utils import OutputFormat


class OutputDispatcher:
    """Dispatcher for formatting FormattableRecord objects in multiple formats.

    Centralizes format dispatch logic to eliminate if/elif chains in CLI
    commands. Uses match/case for exhaustive handling of OutputFormat enum.
    """

    def format(
        self,
        record: FormattableRecord,
        fmt: OutputFormat,
        _source: str | None = None,
        file_path: str | None = None,
    ) -> str:
        """Format a single record in the specified format.

        Args:
            record: Any object implementing FormattableRecord protocol
            fmt: Output format (JSON, YAML, CSV, TEXT)
            _source: Server name for JSON/YAML output (ignored for TEXT/CSV)
            file_path: Optional file path to include at top level

        Returns:
            Formatted string representation
        """
        match fmt:
            case OutputFormat.JSON:
                data = record.to_compact_dict()
                if _source is not None or file_path is not None:
                    # _source and file must be first fields
                    top_level: dict[str, Any] = {}
                    if _source is not None:
                        top_level["_source"] = _source
                    if file_path is not None:
                        top_level["file"] = file_path
                    data = {**top_level, **data}
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                data = record.to_compact_dict()
                if _source is not None or file_path is not None:
                    top_level: dict[str, Any] = {}
                    if _source is not None:
                        top_level["_source"] = _source
                    if file_path is not None:
                        top_level["file"] = file_path
                    data = {**top_level, **data}
                return yaml.dump(
                    data,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            case OutputFormat.CSV:
                return self._format_csv_single(record)
            case OutputFormat.TEXT:
                return record.get_text_line()

    def format_list(
        self,
        records: Sequence[FormattableRecord],
        fmt: OutputFormat,
        _source: str | None = None,
        file_path: str | None = None,
    ) -> str:
        """Format a list of records in the specified format.

        Args:
            records: Sequence of objects implementing FormattableRecord protocol
            fmt: Output format (JSON, YAML, CSV, TEXT)
            _source: Server name for JSON/YAML output (ignored for TEXT/CSV)
            file_path: Optional file path to include at top level

        Returns:
            Formatted string representation. For JSON/YAML, returns "[]" for empty lists.
            For CSV/TEXT, returns empty string for empty lists.
        """
        match fmt:
            case OutputFormat.JSON:
                items = [r.to_compact_dict() for r in records]
                if _source is not None or file_path is not None:
                    # _source and file must be first fields
                    data: dict[str, Any] = {}
                    if _source is not None:
                        data["_source"] = _source
                    if file_path is not None:
                        data["file"] = file_path
                    data["items"] = items
                else:
                    data = items  # type: ignore[assignment]
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                items = [r.to_compact_dict() for r in records]
                if _source is not None or file_path is not None:
                    data: dict[str, Any] = {}
                    if _source is not None:
                        data["_source"] = _source
                    if file_path is not None:
                        data["file"] = file_path
                    data["items"] = items
                else:
                    data = items  # type: ignore[assignment]
                return yaml.dump(
                    data,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            case OutputFormat.CSV:
                return self._format_csv_list(records)
            case OutputFormat.TEXT:
                if not records:
                    return ""
                return "\n".join(r.get_text_line() for r in records)

    def _format_csv_single(self, record: FormattableRecord) -> str:
        """Format a single record as CSV with header row.

        Args:
            record: Object implementing FormattableRecord

        Returns:
            CSV string with header + single data row
        """
        output = io.StringIO()
        headers = record.get_csv_headers()
        writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerow(record.get_csv_row())
        return output.getvalue()

    def _format_csv_list(self, records: Sequence[FormattableRecord]) -> str:
        """Format multiple records as CSV with header row.

        Args:
            records: Sequence of objects implementing FormattableRecord

        Returns:
            CSV string with header + data rows
        """
        if not records:
            return ""

        output = io.StringIO()
        headers = records[0].get_csv_headers()
        writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow(record.get_csv_row())
        return output.getvalue()

    def format_grouped(
        self,
        grouped_data: list[dict[str, Any]],
        fmt: OutputFormat,
        items_key: str = "symbols",
        _source: str | None = None,
        command: str | None = None,
    ) -> str:
        """Format grouped data for JSON/YAML output.

        Args:
            grouped_data: List of group dicts with 'file' and items_key
            fmt: Output format (JSON or YAML)
            items_key: Key name for items ('symbols' or 'diagnostics')
            _source: Server name for JSON/YAML output
            command: Command name for workspace-level commands

        Returns:
            Formatted string representation
        """
        match fmt:
            case OutputFormat.JSON:
                data: dict[str, Any] = {}
                if _source is not None:
                    data["_source"] = _source
                if command is not None:
                    data["command"] = command
                data["files"] = grouped_data
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                data: dict[str, Any] = {}
                if _source is not None:
                    data["_source"] = _source
                if command is not None:
                    data["command"] = command
                data["files"] = grouped_data
                return yaml.dump(
                    data,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            case _:
                # For other formats, delegate to format_grouped_text
                raise ValueError(f"Use format_grouped_text for {fmt} format")

    def format_grouped_text(
        self,
        grouped_data: list[dict[str, Any]],
        items_key: str = "symbols",
        header: str | None = None,
    ) -> str:
        """Format grouped data for TEXT output with hierarchical structure.

        Args:
            grouped_data: List of group dicts with 'file' and items_key
            items_key: Key name for items ('symbols' or 'diagnostics')
            header: Optional alert header to prepend

        Returns:
            Formatted TEXT string with file headers and tree connectors
        """
        from llm_lsp_cli.output.text_renderer import (
            render_workspace_diagnostics_grouped,
            render_workspace_symbols_grouped,
        )

        if items_key == "symbols":
            return render_workspace_symbols_grouped(grouped_data, header=header)
        else:
            return render_workspace_diagnostics_grouped(grouped_data, header=header)

    def format_grouped_flat(
        self,
        grouped_data: list[dict[str, Any]],
        fmt: OutputFormat,
        items_key: str = "symbols",
        headers: list[str] | None = None,
    ) -> str:
        """Format grouped data as flat table for CSV output.

        Flattens the grouped structure into a single table with file column.

        Args:
            grouped_data: List of group dicts with 'file' and items_key
            fmt: Output format (CSV)
            items_key: Key name for items ('symbols' or 'diagnostics')
            headers: CSV column headers

        Returns:
            Flattened CSV string
        """
        if not grouped_data:
            return ""

        # Flatten the grouped data
        flat_rows: list[dict[str, Any]] = []
        for group in grouped_data:
            file_path = group.get("file", "")
            items = group.get(items_key, [])
            for item in items:
                row = {"file": file_path, **item}
                flat_rows.append(row)

        if not flat_rows:
            return ""

        # Determine headers from first row
        if headers is None:
            headers = list(flat_rows[0].keys())

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in flat_rows:
            # Convert all values to strings
            str_row = {k: str(v) if v is not None else "" for k, v in row.items()}
            writer.writerow(str_row)
        return output.getvalue()
