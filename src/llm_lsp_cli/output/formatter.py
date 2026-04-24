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
from llm_lsp_cli.utils.formatter import SYMBOL_KIND_MAP


@dataclass(frozen=True)
class Position:
    """LSP Position with line and character (0-based)."""

    line: int
    character: int

    def to_dict(self) -> dict[str, int]:
        """Convert to LSP Position dict format."""
        return {"line": self.line, "character": self.character}


@dataclass(frozen=True)
class Range:
    """LSP Range with start and end Position objects."""

    start: Position
    end: Position

    @classmethod
    def from_dict(cls, range_obj: dict[str, Any]) -> Range:
        """Create Range from LSP range dict."""
        start = range_obj.get("start", {})
        end = range_obj.get("end", {})
        return cls(
            start=Position(
                line=start.get("line", 0) or 0,
                character=start.get("character", 0) or 0,
            ),
            end=Position(
                line=end.get("line", 0) or 0,
                character=end.get("character", 0) or 0,
            ),
        )

    def to_dict(self) -> dict[str, dict[str, int]]:
        """Convert to LSP Range dict format with nested Position structure."""
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        }

    def to_compact(self) -> str:
        """Convert to compact string format for TEXT/CSV output (1-based)."""
        start_line = self.start.line + 1
        start_char = self.start.character + 1
        end_line = self.end.line + 1
        end_char = self.end.character + 1
        return f"{start_line}:{start_char}-{end_line}:{end_char}"


@dataclass
class SymbolRecord:
    """A normalized symbol record for compact output."""

    file: str
    name: str
    kind: int
    kind_name: str
    range: Range
    detail: str | None = None
    container: str | None = None
    tags: list[int] = field(default_factory=list)
    selection_range: Range | None = None
    data: dict[str, Any] | None = None
    parent: str | None = None
    children: list[SymbolRecord] = field(default_factory=list)


@dataclass
class LocationRecord:
    """A normalized location record for compact output."""

    file: str
    range: Range


@dataclass
class DiagnosticRecord:
    """A normalized diagnostic record for compact output."""

    file: str
    line: int
    character: int
    end_line: int
    end_character: int
    severity: int
    severity_name: str
    code: str | int | None
    source: str
    message: str
    tags: list[int] = field(default_factory=list)
    data: dict[str, Any] | None = None


@dataclass
class CallHierarchyRecord:
    """A normalized call hierarchy record for compact output."""

    file: str
    name: str
    kind: int
    kind_name: str
    range: Range
    from_ranges: list[Range] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict with Range objects serialized."""
        return {
            "file": self.file,
            "name": self.name,
            "kind": self.kind,
            "kind_name": self.kind_name,
            "range": self.range.to_dict(),
            "from_ranges": [r.to_dict() for r in self.from_ranges],
        }


SEVERITY_MAP = {
    1: "Error",
    2: "Warning",
    3: "Information",
    4: "Hint",
}


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

    def transform_symbols(
        self, symbols: list[dict[str, Any]], depth: int = -1
    ) -> list[SymbolRecord]:
        """Transform LSP symbols to SymbolRecord list with depth-controlled traversal.

        Handles both workspace symbols (with location wrapper) and
        document symbols (hierarchical structure with children).

        Args:
            symbols: LSP symbol list
            depth: Maximum traversal depth. -1 = unlimited, 0 = top-level only

        Returns:
            List of normalized SymbolRecord objects with nested children
        """
        records: list[SymbolRecord] = []

        for sym in symbols:
            record = self._transform_symbol(sym, depth, parent_name=None)
            records.append(record)

        return records

    def _transform_symbol(
        self, sym: dict[str, Any], depth: int, parent_name: str | None
    ) -> SymbolRecord:
        """Transform a single symbol with optional children traversal.

        Args:
            sym: LSP symbol dict
            depth: Remaining traversal depth (-1 = unlimited)
            parent_name: Name of parent symbol (None for top-level)

        Returns:
            Normalized SymbolRecord with nested children
        """
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
        range_val = Range.from_dict(range_obj)

        # Optional fields
        detail = sym.get("detail")
        container = sym.get("containerName")
        tags = sym.get("tags", []) or []

        # Preserve selectionRange if present
        selection_range: Range | None = None
        if "selectionRange" in sym:
            selection_range = Range.from_dict(sym["selectionRange"])

        # Preserve data field if present
        data = sym.get("data")

        # Process children if depth allows
        children: list[SymbolRecord] = []
        if depth != 0:
            raw_children = sym.get("children")
            if raw_children:
                child_depth = depth - 1 if depth > 0 else -1
                for child_sym in raw_children:
                    child_record = self._transform_symbol(child_sym, child_depth, name)
                    children.append(child_record)

        return SymbolRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            detail=detail,
            container=container,
            tags=tags,
            selection_range=selection_range,
            data=data,
            parent=parent_name,
            children=children,
        )

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
            range_val = Range.from_dict(range_obj)

            records.append(
                LocationRecord(
                    file=file_path,
                    range=range_val,
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
                line = f"  {rec.name} ({rec.kind_name}) [{rec.range.to_compact()}]"
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

        Handles nested children recursively.

        Args:
            rec: SymbolRecord to convert

        Returns:
            Dictionary with only present fields
        """
        obj: dict[str, Any] = {
            "file": rec.file,
            "name": rec.name,
            "kind_name": rec.kind_name,
            "range": rec.range.to_compact(),
        }
        if rec.detail is not None:
            obj["detail"] = rec.detail
        if rec.container is not None:
            obj["container"] = rec.container
        if rec.tags:
            obj["tags"] = rec.tags
        if rec.selection_range is not None:
            obj["selection_range"] = rec.selection_range.to_compact()
        if rec.data is not None:
            obj["data"] = rec.data
        if rec.parent is not None:
            obj["parent"] = rec.parent
        # Always include children (empty list if no children)
        obj["children"] = [CompactFormatter._symbol_to_dict(child) for child in rec.children]
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
        """Format SymbolRecord list as flat CSV with parent column.

        Flattens hierarchical symbols - each symbol becomes one row
        with parent name in parent column.

        Args:
            records: List of SymbolRecord objects

        Returns:
            CSV string with headers
        """
        if not records:
            return ""

        output = io.StringIO()
        fieldnames = [
            "file", "name", "kind_name", "range", "selection_range", "detail", "tags", "parent"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        # Flatten all records (including nested children)
        def flatten_records(recs: list[SymbolRecord]) -> list[SymbolRecord]:
            flat: list[SymbolRecord] = []
            for rec in recs:
                flat.append(rec)
                if rec.children:
                    flat.extend(flatten_records(rec.children))
            return flat

        flat_records = flatten_records(records)

        for rec in flat_records:
            row = {
                "file": rec.file,
                "name": rec.name,
                "kind_name": rec.kind_name,
                "range": rec.range.to_compact(),
                "selection_range": rec.selection_range.to_compact() if rec.selection_range else "",
                "detail": rec.detail or "",
                "tags": "|".join(str(t) for t in rec.tags) if rec.tags else "",
                "parent": rec.parent or "",
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
                lines.append(f"  [{rec.range.to_compact()}]")
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
        result = [{"file": rec.file, "range": rec.range.to_compact()} for rec in records]
        return json.dumps(result, indent=2)

    def locations_to_yaml(self, records: list[LocationRecord]) -> str:
        """Format LocationRecord list as compact YAML.

        Args:
            records: List of LocationRecord objects

        Returns:
            YAML string
        """
        result = [{"file": rec.file, "range": rec.range.to_compact()} for rec in records]
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
            writer.writerow({"file": rec.file, "range": rec.range.to_compact()})

        return output.getvalue()

    def transform_diagnostics(
        self,
        diagnostics: list[dict[str, Any]],
        file_path: str | None = None,
    ) -> list[DiagnosticRecord]:
        """Transform LSP diagnostics to DiagnosticRecord list.

        Args:
            diagnostics: List of LSP Diagnostic objects
            file_path: Optional known file path (for single-file diagnostics)

        Returns:
            List of normalized DiagnosticRecord objects
        """
        records: list[DiagnosticRecord] = []

        for diag in diagnostics:
            range_obj = diag.get("range", {})
            start = range_obj.get("start", {})
            end = range_obj.get("end", {})

            records.append(
                DiagnosticRecord(
                    file=file_path or "",
                    line=(start.get("line", 0) or 0) + 1,
                    character=(start.get("character", 0) or 0) + 1,
                    end_line=(end.get("line", 0) or 0) + 1,
                    end_character=(end.get("character", 0) or 0) + 1,
                    severity=diag.get("severity", 1),
                    severity_name=SEVERITY_MAP.get(diag.get("severity", 1), "Unknown"),
                    code=diag.get("code"),
                    source=diag.get("source", ""),
                    message=diag.get("message", ""),
                    tags=diag.get("tags", []),
                )
            )

        return records

    def diagnostics_to_text(self, records: list[DiagnosticRecord]) -> str:
        """Format DiagnosticRecord list as compact text.

        Args:
            records: List of DiagnosticRecord objects

        Returns:
            Formatted text string
        """
        if not records:
            return "No diagnostics found."

        lines: list[str] = []
        for rec in records:
            code_str = f" [{rec.code}]" if rec.code else ""
            source_str = f" ({rec.source})" if rec.source else ""
            line = (
                f"{rec.severity_name}: {rec.message}{code_str}{source_str} "
                f"at {rec.line}:{rec.character}-{rec.end_line}:{rec.end_character}"
            )
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _diagnostic_to_dict(rec: DiagnosticRecord) -> dict[str, Any]:
        """Convert DiagnosticRecord to dict, omitting null/empty fields.

        Args:
            rec: DiagnosticRecord to convert

        Returns:
            Dictionary with only present fields
        """
        obj: dict[str, Any] = {
            "file": rec.file,
            "line": rec.line,
            "character": rec.character,
            "end_line": rec.end_line,
            "end_character": rec.end_character,
            "severity": rec.severity,
            "severity_name": rec.severity_name,
            "message": rec.message,
        }
        if rec.code is not None:
            obj["code"] = rec.code
        if rec.source:
            obj["source"] = rec.source
        if rec.tags:
            obj["tags"] = rec.tags
        return obj

    def diagnostics_to_json(self, records: list[DiagnosticRecord]) -> str:
        """Format DiagnosticRecord list as compact JSON.

        Args:
            records: List of DiagnosticRecord objects

        Returns:
            JSON string
        """
        result = [self._diagnostic_to_dict(rec) for rec in records]
        return json.dumps(result, indent=2)

    def diagnostics_to_yaml(self, records: list[DiagnosticRecord]) -> str:
        """Format DiagnosticRecord list as compact YAML.

        Args:
            records: List of DiagnosticRecord objects

        Returns:
            YAML string
        """
        result = [self._diagnostic_to_dict(rec) for rec in records]
        return yaml.safe_dump(result, default_flow_style=False, sort_keys=False)

    def diagnostics_to_csv(self, records: list[DiagnosticRecord]) -> str:
        """Format DiagnosticRecord list as CSV.

        Args:
            records: List of DiagnosticRecord objects

        Returns:
            CSV string with headers
        """
        if not records:
            return ""

        output = io.StringIO()
        fieldnames = [
            "file", "line", "character", "end_line", "end_character",
            "severity", "severity_name", "code", "source", "message", "tags"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for rec in records:
            row = {
                "file": rec.file,
                "line": rec.line,
                "character": rec.character,
                "end_line": rec.end_line,
                "end_character": rec.end_character,
                "severity": str(rec.severity),
                "severity_name": rec.severity_name,
                "code": str(rec.code) if rec.code is not None else "",
                "source": rec.source,
                "message": rec.message,
                "tags": "|".join(str(t) for t in rec.tags) if rec.tags else "",
            }
            writer.writerow(row)

        return output.getvalue()

    def _transform_call_hierarchy_item(
        self, call: dict[str, Any], item: dict[str, Any]
    ) -> CallHierarchyRecord:
        """Transform a single call hierarchy item to CallHierarchyRecord.

        Args:
            call: LSP call dict containing fromRanges
            item: The target item dict (from 'from' or 'to' field)

        Returns:
            Normalized CallHierarchyRecord
        """
        uri = item.get("uri", "")
        range_obj = item.get("range", {})

        # Normalize URI to relative path
        file_path = normalize_uri_to_relative(uri, self._workspace)

        # Extract fields
        name = item.get("name", "")
        kind = item.get("kind", 0)
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
        range_val = Range.from_dict(range_obj)

        # Extract fromRanges
        from_ranges_raw = call.get("fromRanges", [])
        from_ranges = [Range.from_dict(r) for r in from_ranges_raw]

        return CallHierarchyRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            from_ranges=from_ranges,
        )

    def transform_call_hierarchy_incoming(
        self, calls: list[dict[str, Any]]
    ) -> list[CallHierarchyRecord]:
        """Transform LSP incoming calls to CallHierarchyRecord list.

        Args:
            calls: List of LSP CallHierarchyIncomingCall objects

        Returns:
            List of normalized CallHierarchyRecord objects sorted by file/name
        """
        records: list[CallHierarchyRecord] = []

        for call in calls:
            # Get the 'from' item (may be 'from_' in Python-normalized form)
            from_item = call.get("from_") or call.get("from", {})
            record = self._transform_call_hierarchy_item(call, from_item)
            records.append(record)

        # Sort by file then name
        records.sort(key=lambda r: (r.file, r.name))
        return records

    def transform_call_hierarchy_outgoing(
        self, calls: list[dict[str, Any]]
    ) -> list[CallHierarchyRecord]:
        """Transform LSP outgoing calls to CallHierarchyRecord list.

        Args:
            calls: List of LSP CallHierarchyOutgoingCall objects

        Returns:
            List of normalized CallHierarchyRecord objects sorted by file/name
        """
        records: list[CallHierarchyRecord] = []

        for call in calls:
            to_item = call.get("to", {})
            record = self._transform_call_hierarchy_item(call, to_item)
            records.append(record)

        # Sort by file then name
        records.sort(key=lambda r: (r.file, r.name))
        return records
