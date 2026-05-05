# pyright: reportExplicitAny=false
# pyright: reportAny=false
"""Output dispatcher for unified format handling.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from collections.abc import Sequence
from typing import Any

import yaml

from llm_lsp_cli.output.protocol import FormattableRecord
from llm_lsp_cli.utils import OutputFormat

logger = logging.getLogger(__name__)


def _build_top_level_dict(
    _source: str | None,
    file_path: str | None,
    command: str | None,
) -> dict[str, Any]:
    """Build top-level metadata dict with non-None values.

    Args:
        _source: Server name for JSON/YAML output
        file_path: Optional file path to include at top level
        command: Optional command name

    Returns:
        Dict with only the provided non-None values.
    """
    top_level: dict[str, Any] = {}
    if _source is not None:
        top_level["_source"] = _source
    if file_path is not None:
        top_level["file"] = file_path
    if command is not None:
        top_level["command"] = command
    return top_level


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
        command: str | None = None,
    ) -> str:
        """Format a single record in the specified format.

        Args:
            record: Any object implementing FormattableRecord protocol
            fmt: Output format (JSON, YAML, CSV, TEXT)
            _source: Server name for JSON/YAML output (ignored for TEXT/CSV)
            file_path: Optional file path to include at top level
            command: Optional command name (e.g., "hover")

        Returns:
            Formatted string representation
        """
        match fmt:
            case OutputFormat.JSON:
                top_level = _build_top_level_dict(_source, file_path, command)
                data = record.to_compact_dict()
                if top_level:
                    data = {**top_level, **data}
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                top_level = _build_top_level_dict(_source, file_path, command)
                yaml_data = record.to_compact_dict()
                if top_level:
                    yaml_data = {**top_level, **yaml_data}
                return str(
                    yaml.dump(
                        yaml_data,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
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
        command: str | None = None,
    ) -> str:
        """Format a list of records in the specified format.

        Args:
            records: Sequence of objects implementing FormattableRecord protocol
            fmt: Output format (JSON, YAML, CSV, TEXT)
            _source: Server name for JSON/YAML output (ignored for TEXT/CSV)
            file_path: Optional file path to include at top level
            command: Optional command name (e.g., "document-symbol")

        Returns:
            Formatted string representation. For JSON/YAML, returns "[]" for empty lists.
            For CSV/TEXT, returns empty string for empty lists.
        """
        match fmt:
            case OutputFormat.JSON:
                items = [r.to_compact_dict() for r in records]
                data = _build_top_level_dict(_source, file_path, command)
                data["items"] = items
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                yaml_items = [r.to_compact_dict() for r in records]
                yaml_data = _build_top_level_dict(_source, file_path, command)
                yaml_data["items"] = yaml_items
                return str(
                    yaml.dump(
                        yaml_data,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
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
                data = _build_top_level_dict(_source, None, command)
                data["files"] = grouped_data
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                grouped_yaml_data = _build_top_level_dict(_source, None, command)
                grouped_yaml_data["files"] = grouped_data
                return str(
                    yaml.dump(
                        grouped_yaml_data,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
                )
            case _:
                # For other formats, delegate to format_grouped_text
                raise ValueError(f"Use format_grouped_text for {fmt} format")

    def format_references_csv(
        self,
        grouped_data: list[dict[str, Any]],
    ) -> str:
        """Format grouped references as CSV with file and ranges columns.

        Args:
            grouped_data: List of group dicts with 'file' and 'references' keys

        Returns:
            CSV string with header row: file,ranges
            Ranges are pipe-separated (e.g., "1:5-1:10|5:1-5:20") to avoid CSV quoting.
        """
        if not grouped_data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["file", "ranges"], lineterminator="\n")
        writer.writeheader()

        for group in grouped_data:
            file_path = group.get("file", "")
            references = group.get("references", [])
            ranges = [ref.get("range", "") for ref in references]
            ranges_str = "|".join(ranges)
            writer.writerow({"file": file_path, "ranges": ranges_str})

        return output.getvalue()

    def format_grouped_text(
        self,
        grouped_data: list[dict[str, Any]],
        items_key: str = "symbols",
        header: str | None = None,
    ) -> str:
        """Format grouped data for TEXT output with hierarchical structure.

        Args:
            grouped_data: List of group dicts with 'file' and items_key
            items_key: Key name for items ('symbols', 'diagnostics', or 'references')
            header: Optional alert header to prepend

        Returns:
            Formatted TEXT string with file headers and tree connectors
        """
        from llm_lsp_cli.output.text_renderer import (
            render_references_grouped,
            render_workspace_diagnostics_grouped,
            render_workspace_symbols_grouped,
        )

        if items_key == "symbols":
            return render_workspace_symbols_grouped(grouped_data, header=header)
        elif items_key == "references":
            return render_references_grouped(grouped_data, header=header)
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

    def format_rename_grouped(
        self,
        records: Sequence[FormattableRecord],
        fmt: OutputFormat,
        _source: str | None = None,
        command: str | None = None,
    ) -> str:
        """Format rename edits with grouped structure.

        For JSON/YAML: groups edits by file with hoisted old_text/new_text.
        For TEXT: shows header line with file groups and indented ranges.
        For CSV: delegates to format_list for flat output.

        Args:
            records: Sequence of RenameEditRecord objects
            fmt: Output format (JSON, YAML, TEXT, CSV)
            _source: Server name for JSON/YAML output
            command: Command name (typically "rename")

        Returns:
            Formatted string representation
        """
        from llm_lsp_cli.output.formatter import (
            RenameEditRecord,
            group_rename_edits_by_file,
        )

        # Type narrow to RenameEditRecord
        rename_records = [r for r in records if isinstance(r, RenameEditRecord)]
        if len(rename_records) < len(records):
            logger.debug(
                "Filtered %d non-RenameEditRecord items in format_rename_grouped",
                len(records) - len(rename_records),
            )

        match fmt:
            case OutputFormat.JSON:
                old_text, new_text, file_records = group_rename_edits_by_file(rename_records)
                items = [
                    {"file": fr.file, "ranges": fr.ranges}
                    for fr in file_records
                ]
                data = _build_top_level_dict(_source, None, command)
                data["old_text"] = old_text
                data["new_text"] = new_text
                data["items"] = items
                return json.dumps(data, indent=2)

            case OutputFormat.YAML:
                old_text, new_text, file_records = group_rename_edits_by_file(rename_records)
                yaml_items = [
                    {"file": fr.file, "ranges": fr.ranges}
                    for fr in file_records
                ]
                yaml_data = _build_top_level_dict(_source, None, command)
                yaml_data["old_text"] = old_text
                yaml_data["new_text"] = new_text
                yaml_data["items"] = yaml_items
                return str(
                    yaml.dump(
                        yaml_data,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
                )

            case OutputFormat.TEXT:
                old_text, new_text, file_records = group_rename_edits_by_file(rename_records)
                if not file_records:
                    return ""
                lines: list[str] = [f"Rename: '{old_text}' -> '{new_text}'"]
                for fr in file_records:
                    lines.append(f"File: {fr.file}")
                    for range_str in fr.ranges:
                        lines.append(f"  - {range_str}")
                return "\n".join(lines)

            case OutputFormat.CSV:
                # CSV remains flat - delegate to format_list
                return self.format_list(records, fmt)
