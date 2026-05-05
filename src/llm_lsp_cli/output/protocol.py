# pyright: reportExplicitAny=false
"""FormattableRecord Protocol for unified output formatting.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FormattableRecord(Protocol):
    """Protocol for records that can be formatted in multiple output formats.

    Any dataclass that implements these four methods can be dispatched
    through OutputDispatcher for consistent formatting across JSON, YAML,
    CSV, and TEXT output formats.
    """

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert record to a dict suitable for JSON/YAML output.

        Returns:
            Dict with compact representation, omitting null/empty fields
            and using human-readable names for enum-like fields (kind_name,
            severity_name, tag names).
        """
        ...

    def get_csv_headers(self) -> list[str]:
        """Return the CSV column headers for this record type.

        Returns:
            List of column header strings in display order.
        """
        ...

    def get_csv_row(self) -> dict[str, str]:
        """Return a single CSV row as string values.

        Returns:
            Dict mapping header names to string values.
            All values must be strings for CSV compatibility.
        """
        ...

    def get_text_line(self) -> str:
        """Return a single-line text representation.

        Returns:
            Single-line string suitable for human reading.
            Should not contain embedded newlines.
        """
        ...
