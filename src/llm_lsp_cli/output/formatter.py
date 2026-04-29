"""Compact formatter for LLM-optimized LSP output."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeVar

from llm_lsp_cli.output.path_resolver import normalize_uri_to_relative
from llm_lsp_cli.utils.formatter import SYMBOL_KIND_MAP, get_diagnostic_tag_name


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
        # LSP uses 0-based indexing, but editors/humans expect 1-based
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

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format, omitting null/empty fields."""
        return CompactFormatter._symbol_to_dict(self)

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for symbol records."""
        return ["file", "name", "kind_name", "range", "selection_range", "detail", "tags", "parent"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this symbol."""
        return {
            "file": self.file,
            "name": self.name,
            "kind_name": self.kind_name,
            "range": self.range.to_compact(),
            "selection_range": self.selection_range.to_compact() if self.selection_range else "",
            "detail": self.detail or "",
            "tags": "|".join(str(t) for t in self.tags) if self.tags else "",
            "parent": self.parent or "",
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation.

        Format: "name (kind_name), range: <range>, selection_range: <selection_range>"
        Omit selection_range if not present.
        """
        from llm_lsp_cli.output.text_renderer import format_symbol_text_line

        return format_symbol_text_line(
            name=self.name,
            kind_name=self.kind_name,
            range_str=self.range.to_compact(),
            selection_range=(
                self.selection_range.to_compact() if self.selection_range else None
            ),
        )


@dataclass
class LocationRecord:
    """A normalized location record for compact output."""

    file: str
    range: Range

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format."""
        return {"file": self.file, "range": self.range.to_compact()}

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for location records."""
        return ["file", "range"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this location."""
        return {
            "file": self.file,
            "range": self.range.to_compact(),
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation."""
        return f"{self.file}: {self.range.to_compact()}"


@dataclass
class DiagnosticRecord:
    """A normalized diagnostic record for compact output."""

    file: str
    range: Range
    severity: int
    severity_name: str
    code: str | int | None
    source: str
    message: str
    tags: list[int] = field(default_factory=list)
    data: dict[str, Any] | None = None

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format, omitting null/empty fields."""
        return CompactFormatter._diagnostic_to_dict(self)

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for diagnostic records."""
        return ["file", "range", "severity_name", "code", "source", "message", "tags"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this diagnostic."""
        return {
            "file": self.file,
            "range": self.range.to_compact(),
            "severity_name": self.severity_name,
            "code": str(self.code) if self.code is not None else "",
            "source": self.source,
            "message": self.message,
            "tags": "|".join(get_diagnostic_tag_name(t) for t in self.tags) if self.tags else "",
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation.

        Format: "severity: message, code: <code>, range: <range>, tags: [<tags>]"
        Omit code, tags if not present.
        """
        parts: list[str] = [f"{self.severity_name}: {self.message}"]
        if self.code is not None and self.code != "":
            parts.append(f"code: {self.code}")
        parts.append(f"range: {self.range.to_compact()}")
        if self.tags:
            tag_names = [get_diagnostic_tag_name(t) for t in self.tags]
            parts.append(f"tags: [{', '.join(tag_names)}]")
        return ", ".join(parts)


@dataclass
class CallHierarchyRecord:
    """A normalized call hierarchy record for compact output."""

    file: str
    name: str
    kind: int
    kind_name: str
    range: Range
    selection_range: Range | None = None
    from_ranges: list[Range] = field(default_factory=list)

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format.

        Omits 'kind' int field for token efficiency (kind_name provides human-readable value).
        Range fields use compact format "start_line:start_char-end_line:end_char".
        """
        obj: dict[str, Any] = {
            "file": self.file,
            "name": self.name,
            "kind_name": self.kind_name,
            "range": self.range.to_compact(),
        }
        if self.selection_range is not None:
            obj["selection_range"] = self.selection_range.to_compact()
        if self.from_ranges:
            obj["from_ranges"] = [r.to_compact() for r in self.from_ranges]
        return obj

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for call hierarchy records."""
        return ["file", "name", "kind_name", "range", "selection_range", "from_ranges"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this call hierarchy record."""
        from_ranges_str = (
            "|".join(r.to_compact() for r in self.from_ranges) if self.from_ranges else ""
        )
        return {
            "file": self.file,
            "name": self.name,
            "kind_name": self.kind_name,
            "range": self.range.to_compact(),
            "selection_range": self.selection_range.to_compact() if self.selection_range else "",
            "from_ranges": from_ranges_str,
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation."""
        return f"{self.file}: {self.name} ({self.kind_name}) [{self.range.to_compact()}]"


@dataclass
class RenameEditRecord:
    """A normalized rename edit record for compact output.

    Implements FormattableRecord for consistent output formatting.
    """

    file: str
    range: Range
    old_text: str
    new_text: str

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format."""
        return {
            "file": self.file,
            "range": self.range.to_compact(),
            "old_text": self.old_text,
            "new_text": self.new_text,
        }

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for rename edit records."""
        return ["file", "range", "old_text", "new_text"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this rename edit."""
        return {
            "file": self.file,
            "range": self.range.to_compact(),
            "old_text": self.old_text,
            "new_text": self.new_text,
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation."""
        return f"{self.file}:{self.range.to_compact()} '{self.old_text}' -> '{self.new_text}'"


@dataclass
class CompletionRecord:
    """A normalized completion record for compact output.

    Implements FormattableRecord for consistent output formatting.
    """

    file: str
    label: str
    kind: int
    kind_name: str
    detail: str | None = None
    documentation: str | None = None
    range: Range | None = None  # from textEdit.range
    position: Range | None = None  # from data.position (as single point)

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format, omitting null fields."""
        obj: dict[str, Any] = {
            "file": self.file,
            "label": self.label,
            "kind_name": self.kind_name,
        }
        if self.detail is not None:
            obj["detail"] = self.detail
        if self.documentation is not None:
            obj["documentation"] = self.documentation
        if self.range is not None:
            obj["range"] = self.range.to_compact()
        if self.position is not None:
            obj["position"] = self.position.to_compact()
        return obj

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for completion records."""
        return ["file", "label", "kind_name", "detail", "documentation", "range", "position"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this completion."""
        return {
            "file": self.file,
            "label": self.label,
            "kind_name": self.kind_name,
            "detail": self.detail or "",
            "documentation": self.documentation or "",
            "range": self.range.to_compact() if self.range else "",
            "position": self.position.to_compact() if self.position else "",
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation."""
        range_str = f" [{self.range.to_compact()}]" if self.range else ""
        detail_str = f" - {self.detail}" if self.detail else ""
        return f"{self.file}: {self.label}{detail_str}{range_str}"


@dataclass
class HoverRecord:
    """A normalized hover record for compact output.

    Implements FormattableRecord for consistent output formatting.
    """

    file: str
    content: str
    range: Range | None = None

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to dict with compact range format, omitting null fields."""
        obj: dict[str, Any] = {
            "file": self.file,
            "content": self.content,
        }
        if self.range is not None:
            obj["range"] = self.range.to_compact()
        return obj

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for hover records."""
        return ["file", "content", "range"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this hover."""
        return {
            "file": self.file,
            "content": self.content,
            "range": self.range.to_compact() if self.range else "",
        }

    def get_text_line(self) -> str:
        """Return a single-line text representation."""
        range_str = f" [{self.range.to_compact()}]" if self.range else ""
        return f"{self.file}: {self.content}{range_str}"


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

    @staticmethod
    def _symbol_to_dict(rec: SymbolRecord) -> dict[str, Any]:
        """Convert SymbolRecord to dict, omitting null/empty fields.

        Handles nested children recursively.

        Args:
            rec: SymbolRecord to convert

        Returns:
            Dictionary with only present fields (excludes file - it's at top level)
        """
        obj: dict[str, Any] = {
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
            range_val = Range.from_dict(range_obj)

            records.append(
                DiagnosticRecord(
                    file=file_path or "",
                    range=range_val,
                    severity=diag.get("severity", 1),
                    severity_name=SEVERITY_MAP.get(diag.get("severity", 1), "Unknown"),
                    code=diag.get("code"),
                    source=diag.get("source", ""),
                    message=diag.get("message", ""),
                    tags=diag.get("tags", []) or [],
                )
            )

        return records

    @staticmethod
    def _diagnostic_to_dict(rec: DiagnosticRecord) -> dict[str, Any]:
        """Convert DiagnosticRecord to dict, omitting null/empty fields.

        Translates tags to names and uses compact range format.
        Omits severity integer (keeps severity_name only).
        Excludes file - it's at top level.

        Args:
            rec: DiagnosticRecord to convert

        Returns:
            Dictionary with only present fields (excludes file)
        """
        obj: dict[str, Any] = {
            "range": rec.range.to_compact(),
            "severity_name": rec.severity_name,
            "message": rec.message,
        }
        if rec.code is not None:
            obj["code"] = rec.code
        if rec.source:
            obj["source"] = rec.source
        if rec.tags:
            obj["tags"] = [get_diagnostic_tag_name(t) for t in rec.tags]
        return obj

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

        # Extract selectionRange if present
        selection_range: Range | None = None
        if "selectionRange" in item:
            selection_range = Range.from_dict(item["selectionRange"])

        # Extract fromRanges
        from_ranges_raw = call.get("fromRanges", [])
        from_ranges = [Range.from_dict(r) for r in from_ranges_raw]

        return CallHierarchyRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            selection_range=selection_range,
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

    def transform_completions(
        self, items: list[dict[str, Any]], file_path: str
    ) -> list[CompletionRecord]:
        """Transform LSP completion items to CompletionRecord list.

        Args:
            items: List of LSP completion items
            file_path: File path for the completion request

        Returns:
            List of normalized CompletionRecord objects
        """
        records: list[CompletionRecord] = []

        for item in items:
            label = item.get("label", "")
            kind = item.get("kind", 0)
            kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
            detail = item.get("detail")
            documentation = item.get("documentation")

            # Handle dict documentation (MarkupContent)
            if isinstance(documentation, dict):
                documentation = documentation.get("value")

            # Extract range from textEdit.range
            range_val: Range | None = None
            text_edit = item.get("textEdit")
            if text_edit and isinstance(text_edit, dict):
                range_obj = text_edit.get("range")
                if range_obj:
                    range_val = Range.from_dict(range_obj)

            # Extract position from data.position
            position_val: Range | None = None
            data = item.get("data")
            if data and isinstance(data, dict):
                pos = data.get("position")
                if pos:
                    # Position is a single point, create a Range with same start/end
                    position_val = Range(
                        start=Position(
                            line=pos.get("line", 0) or 0,
                            character=pos.get("character", 0) or 0,
                        ),
                        end=Position(
                            line=pos.get("line", 0) or 0,
                            character=pos.get("character", 0) or 0,
                        ),
                    )

            records.append(
                CompletionRecord(
                    file=file_path,
                    label=label,
                    kind=kind,
                    kind_name=kind_name,
                    detail=detail,
                    documentation=documentation,
                    range=range_val,
                    position=position_val,
                )
            )

        return records

    def transform_hover(
        self, hover: dict[str, Any] | None, file_path: str
    ) -> HoverRecord | None:
        """Transform LSP hover response to HoverRecord.

        Args:
            hover: LSP hover response object or None
            file_path: File path for the hover request

        Returns:
            HoverRecord or None if hover is None
        """
        if hover is None:
            return None

        # Extract content from contents
        contents = hover.get("contents", {})
        if isinstance(contents, dict):
            content = contents.get("value", "")
        elif isinstance(contents, list) and contents:
            # Handle array of MarkedString
            first = contents[0]
            content = first.get("value", "") if isinstance(first, dict) else str(first)
        else:
            content = str(contents) if contents else ""

        # Extract range if present
        range_val: Range | None = None
        range_obj = hover.get("range")
        if range_obj:
            range_val = Range.from_dict(range_obj)

        return HoverRecord(
            file=file_path,
            content=content,
            range=range_val,
        )


# =============================================================================
# Grouping Functions for Workspace Output
# =============================================================================


class _HasFile(Protocol):
    """Protocol for records with a file attribute and compact dict conversion."""

    file: str

    def to_compact_dict(self) -> dict[str, Any]:
        """Convert to compact dict representation."""
        ...


_T = TypeVar("_T", bound=_HasFile)


def _group_records_by_file(
    records: list[_T],
    items_key: str,
) -> list[dict[str, Any]]:
    """Group records by file path.

    This is the shared implementation for grouping SymbolRecords and
    DiagnosticRecords by their file attribute.

    Args:
        records: List of records with a 'file' attribute
        items_key: Key name for items in output ('symbols' or 'diagnostics')

    Returns:
        List of group dicts with 'file' and items_key keys,
        sorted alphabetically by file path.
    """
    if not records:
        return []

    # Group by file
    groups: dict[str, list[_T]] = {}
    for record in records:
        file_path = record.file
        if file_path not in groups:
            groups[file_path] = []
        groups[file_path].append(record)

    # Sort by file path and build result
    result: list[dict[str, Any]] = []
    for file_path in sorted(groups.keys()):
        result.append({
            "file": file_path,
            items_key: [r.to_compact_dict() for r in groups[file_path]],
        })

    return result


def group_symbols_by_file(symbols: list[SymbolRecord]) -> list[dict[str, Any]]:
    """Group SymbolRecords by file path for workspace-symbol output.

    Groups are sorted alphabetically by file path.

    Args:
        symbols: List of SymbolRecord objects to group

    Returns:
        List of group dicts with 'file' and 'symbols' keys.
        Each symbol is converted via to_compact_dict().
    """
    return _group_records_by_file(symbols, "symbols")


def group_diagnostics_by_file(
    diagnostics: list[DiagnosticRecord],
) -> list[dict[str, Any]]:
    """Group DiagnosticRecords by file path for workspace-diagnostics output.

    Groups are sorted alphabetically by file path.

    Args:
        diagnostics: List of DiagnosticRecord objects to group

    Returns:
        List of group dicts with 'file' and 'diagnostics' keys.
        Each diagnostic is converted via to_compact_dict().
    """
    return _group_records_by_file(diagnostics, "diagnostics")
