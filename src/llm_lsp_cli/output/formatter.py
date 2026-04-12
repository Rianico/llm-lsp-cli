"""Compact formatter for LLM-optimized LSP output."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from llm_lsp_cli.output.path_resolver import normalize_uri_to_relative
from llm_lsp_cli.output.range_formatter import format_range_compact
from llm_lsp_cli.utils.formatter import SYMBOL_KIND_MAP


@dataclass
class SymbolRecord:
    """A normalized symbol record for compact output."""

    file: str
    name: str
    kind: int
    kind_name: str
    range: str
    detail: str | None = None
    container: str | None = None
    tags: list[int] = field(default_factory=list)


@dataclass
class LocationRecord:
    """A normalized location record for compact output."""

    file: str
    range: str


class CompactFormatter:
    """Formatter for LLM-optimized compact LSP output.

    Transforms LSP workspace symbols, document symbols, and locations
    into token-efficient formats (text, json, yaml, csv).
    """

    def __init__(self, workspace: str | Path) -> None:
        """Initialize the formatter with a workspace root.

        Args:
            workspace: Workspace root path for URI normalization
        """
        self._workspace = Path(workspace).resolve()

    @property
    def workspace(self) -> Path:
        """Return the workspace root path."""
        return self._workspace

    def transform_symbols(self, symbols: list[dict[str, Any]]) -> list[SymbolRecord]:
        """Transform LSP symbols to SymbolRecord list.

        Handles both workspace symbols (with location wrapper) and
        document symbols (flat structure).

        Args:
            symbols: LSP symbol list

        Returns:
            List of normalized SymbolRecord objects
        """
        records: list[SymbolRecord] = []

        for sym in symbols:
            # Get location - handle both workspace and document symbol formats
            location = sym.get("location", sym)
            uri = location.get("uri", "")
            range_obj = location.get("range", sym.get("range", {}))

            # Normalize URI to relative path
            file_path = normalize_uri_to_relative(uri, self._workspace)

            # Extract fields
            name = sym.get("name", "")
            kind = sym.get("kind", 0)
            kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
            range_str = format_range_compact(range_obj)

            # Optional fields
            detail = sym.get("detail")
            container = sym.get("containerName")
            tags = sym.get("tags", [])

            records.append(
                SymbolRecord(
                    file=file_path,
                    name=name,
                    kind=kind,
                    kind_name=kind_name,
                    range=range_str,
                    detail=detail,
                    container=container,
                    tags=tags if tags else [],
                )
            )

        return records

    def transform_locations(self, locations: list[dict[str, Any]]) -> list[LocationRecord]:
        """Transform LSP locations to LocationRecord list.

        Args:
            locations: LSP location list

        Returns:
            List of normalized LocationRecord objects
        """
        records: list[LocationRecord] = []

        for loc in locations:
            uri = loc.get("uri", "")
            range_obj = loc.get("range", {})

            # Normalize URI to relative path
            file_path = normalize_uri_to_relative(uri, self._workspace)
            range_str = format_range_compact(range_obj)

            records.append(
                LocationRecord(
                    file=file_path,
                    range=range_str,
                )
            )

        return records

    def symbols_to_text(self, records: list[SymbolRecord]) -> str:
        """Format SymbolRecord list as compact text.

        Groups symbols by file with two-space indentation.
        Files are sorted alphabetically for deterministic output.

        Args:
            records: List of SymbolRecord objects

        Returns:
            Formatted text string
        """
        if not records:
            return "No symbols found."

        # Group by file
        by_file: dict[str, list[SymbolRecord]] = {}
        for rec in records:
            by_file.setdefault(rec.file, []).append(rec)

        # Sort files alphabetically
        sorted_files = sorted(by_file.keys())

        lines: list[str] = []
        for file_path in sorted_files:
            lines.append(f"{file_path}:")
            for rec in by_file[file_path]:
                line = f"  {rec.name} ({rec.kind}) [{rec.range}]"
                if rec.detail:
                    line += f" -> {rec.detail}"
                lines.append(line)
            lines.append("")  # Blank line between files

        # Remove trailing blank line
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    @staticmethod
    def _symbol_to_dict(rec: SymbolRecord) -> dict[str, Any]:
        """Convert SymbolRecord to dict, omitting null/empty fields.

        Args:
            rec: SymbolRecord to convert

        Returns:
            Dictionary with only present fields
        """
        obj: dict[str, Any] = {
            "file": rec.file,
            "name": rec.name,
            "kind": rec.kind,
            "kind_name": rec.kind_name,
            "range": rec.range,
        }
        if rec.detail is not None:
            obj["detail"] = rec.detail
        if rec.container is not None:
            obj["container"] = rec.container
        if rec.tags:
            obj["tags"] = rec.tags
        return obj

    def symbols_to_json(self, records: list[SymbolRecord]) -> str:
        """Format SymbolRecord list as compact JSON.

        Omits null fields for token efficiency.

        Args:
            records: List of SymbolRecord objects

        Returns:
            JSON string
        """
        result = [self._symbol_to_dict(rec) for rec in records]
        return json.dumps(result, indent=2)

    def symbols_to_yaml(self, records: list[SymbolRecord]) -> str:
        """Format SymbolRecord list as compact YAML.

        Omits null fields for token efficiency.

        Args:
            records: List of SymbolRecord objects

        Returns:
            YAML string
        """
        result = [self._symbol_to_dict(rec) for rec in records]
        return yaml.safe_dump(result, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def symbols_to_csv(self, records: list[SymbolRecord]) -> str:
        """Format SymbolRecord list as CSV.

        Args:
            records: List of SymbolRecord objects

        Returns:
            CSV string with headers
        """
        if not records:
            return ""

        output = io.StringIO()
        fieldnames = ["file", "name", "kind", "range", "detail", "container", "tags"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for rec in records:
            row = {
                "file": rec.file,
                "name": rec.name,
                "kind": str(rec.kind),
                "range": rec.range,
                "detail": rec.detail or "",
                "container": rec.container or "",
                "tags": "|".join(str(t) for t in rec.tags) if rec.tags else "",
            }
            writer.writerow(row)

        return output.getvalue()

    def locations_to_text(self, records: list[LocationRecord]) -> str:
        """Format LocationRecord list as compact text.

        Groups locations by file with two-space indentation.

        Args:
            records: List of LocationRecord objects

        Returns:
            Formatted text string
        """
        if not records:
            return "No locations found."

        # Group by file
        by_file: dict[str, list[LocationRecord]] = {}
        for rec in records:
            by_file.setdefault(rec.file, []).append(rec)

        # Sort files alphabetically
        sorted_files = sorted(by_file.keys())

        lines: list[str] = []
        for i, file_path in enumerate(sorted_files):
            lines.append(f"{file_path}:")
            for rec in by_file[file_path]:
                lines.append(f"  [{rec.range}]")
            # Add blank line between files (but not after last)
            if i < len(sorted_files) - 1:
                lines.append("")

        return "\n".join(lines)

    def locations_to_json(self, records: list[LocationRecord]) -> str:
        """Format LocationRecord list as compact JSON.

        Args:
            records: List of LocationRecord objects

        Returns:
            JSON string
        """
        result = [{"file": rec.file, "range": rec.range} for rec in records]
        return json.dumps(result, indent=2)

    def locations_to_yaml(self, records: list[LocationRecord]) -> str:
        """Format LocationRecord list as compact YAML.

        Args:
            records: List of LocationRecord objects

        Returns:
            YAML string
        """
        result = [{"file": rec.file, "range": rec.range} for rec in records]
        return yaml.safe_dump(result, default_flow_style=False, sort_keys=False)

    def locations_to_csv(self, records: list[LocationRecord]) -> str:
        """Format LocationRecord list as CSV.

        Args:
            records: List of LocationRecord objects

        Returns:
            CSV string with headers
        """
        if not records:
            return ""

        output = io.StringIO()
        fieldnames = ["file", "range"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for rec in records:
            writer.writerow({"file": rec.file, "range": rec.range})

        return output.getvalue()
