"""Output dispatcher for unified format handling."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import yaml

from llm_lsp_cli.output.protocol import FormattableRecord
from llm_lsp_cli.utils import OutputFormat


class OutputDispatcher:
    """Dispatcher for formatting FormattableRecord objects in multiple formats.

    Centralizes format dispatch logic to eliminate if/elif chains in CLI
    commands. Uses match/case for exhaustive handling of OutputFormat enum.
    """

    def format(self, record: FormattableRecord, fmt: OutputFormat) -> str:
        """Format a single record in the specified format.

        Args:
            record: Any object implementing FormattableRecord protocol
            fmt: Output format (JSON, YAML, CSV, TEXT)

        Returns:
            Formatted string representation
        """
        match fmt:
            case OutputFormat.JSON:
                return json.dumps(record.to_compact_dict(), indent=2)
            case OutputFormat.YAML:
                return yaml.dump(
                    record.to_compact_dict(),
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            case OutputFormat.CSV:
                return self._format_csv_single(record)
            case OutputFormat.TEXT:
                return record.get_text_line()

    def format_list(self, records: Sequence[FormattableRecord], fmt: OutputFormat) -> str:
        """Format a list of records in the specified format.

        Args:
            records: Sequence of objects implementing FormattableRecord protocol
            fmt: Output format (JSON, YAML, CSV, TEXT)

        Returns:
            Formatted string representation. For JSON/YAML, returns "[]" for empty lists.
            For CSV/TEXT, returns empty string for empty lists.
        """
        match fmt:
            case OutputFormat.JSON:
                data = [r.to_compact_dict() for r in records]
                return json.dumps(data, indent=2)
            case OutputFormat.YAML:
                data = [r.to_compact_dict() for r in records]
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
