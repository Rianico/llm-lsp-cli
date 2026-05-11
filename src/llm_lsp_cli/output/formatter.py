"""Compact formatter for LLM-optimized LSP output.

This module transforms LSP response data into compact output formats.
Consumes validated Pydantic models from lsp/types.py (ADR-0027).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from llm_lsp_cli.output.path_resolver import normalize_uri_to_absolute
from llm_lsp_cli.utils.formatter import SYMBOL_KIND_MAP, get_diagnostic_tag_name
from llm_lsp_cli.utils.type_helpers import (
    get_dict,
    get_int,
    get_list,
    get_optional_dict,
    get_optional_int,
    get_optional_str,
    get_str,
)

if TYPE_CHECKING:
    from llm_lsp_cli.lsp.types import (
        CallHierarchyIncomingCall,
        CallHierarchyOutgoingCall,
        DocumentSymbol,
        SymbolInformation,
    )
    from llm_lsp_cli.lsp.types import (
        Range as LspRange,
    )


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
    def from_dict(cls, range_obj: object) -> Range:
        """Create Range from LSP range dict."""
        start = get_dict(range_obj, "start")
        end = get_dict(range_obj, "end")
        return cls(
            start=Position(
                line=get_int(start, "line", 0),
                character=get_int(start, "character", 0),
            ),
            end=Position(
                line=get_int(end, "line", 0),
                character=get_int(end, "character", 0),
            ),
        )

    @classmethod
    def from_pydantic(cls, range_obj: LspRange) -> Range:
        """Create Range from LSP Range Pydantic model.

        This is the designated bridge from lsp.types.Range (Pydantic) to
        output.formatter.Range (dataclass) per ADR-0027.

        Args:
            range_obj: Validated LSP Range Pydantic model

        Returns:
            Range dataclass instance
        """
        return cls(
            start=Position(
                line=range_obj.start.line,
                character=range_obj.start.character,
            ),
            end=Position(
                line=range_obj.end.line,
                character=range_obj.end.character,
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
    data: object = None
    parent: str | None = None
    children: list[SymbolRecord] = field(default_factory=list)

    def to_compact_dict(self) -> dict[str, object]:
        """Convert to dict with compact range format, omitting null/empty fields."""
        return CompactFormatter.symbol_to_dict(self)

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
            selection_range=(self.selection_range.to_compact() if self.selection_range else None),
        )


@dataclass
class LocationRecord:
    """A normalized location record for compact output."""

    file: str
    range: Range

    def to_compact_dict(self) -> dict[str, object]:
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
    data: object = None

    def to_compact_dict(self) -> dict[str, object]:
        """Convert to dict with compact range format, omitting null/empty fields."""
        return CompactFormatter.diagnostic_to_dict(self)

    def get_csv_headers(self) -> list[str]:
        """Return CSV headers for diagnostic records."""
        return ["file", "range", "severity_name", "code", "message", "tags"]

    def get_csv_row(self) -> dict[str, str]:
        """Return a CSV row for this diagnostic."""
        return {
            "file": self.file,
            "range": self.range.to_compact(),
            "severity_name": self.severity_name,
            "code": str(self.code) if self.code is not None else "",
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

    def to_compact_dict(self) -> dict[str, object]:
        """Convert to dict with compact range format.

        Omits 'kind' int field for token efficiency (kind_name provides human-readable value).
        Range fields use compact format "start_line:start_char-end_line:end_char".
        """
        obj: dict[str, object] = {
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

    def to_compact_dict(self) -> dict[str, object]:
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

    def to_compact_dict(self) -> dict[str, object]:
        """Convert to dict with compact range format, omitting null fields."""
        obj: dict[str, object] = {
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

    def to_compact_dict(self) -> dict[str, object]:
        """Convert to dict with compact range format, omitting null fields."""
        obj: dict[str, object] = {
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

    _workspace: Path

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
        self,
        symbols: Sequence[object],
        depth: int = -1,
    ) -> list[SymbolRecord]:
        """Transform LSP symbols to SymbolRecord list with depth-controlled traversal.

        Handles both workspace symbols (with location wrapper) and
        document symbols (hierarchical structure with children).

        Accepts both Pydantic models (DocumentSymbol, SymbolInformation) and
        dict-based inputs for backward compatibility (ADR-0027).

        Args:
            symbols: LSP symbol list (Pydantic models or dicts)
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
        self,
        sym: object,
        depth: int,
        parent_name: str | None,
    ) -> SymbolRecord:
        """Transform a single symbol with optional children traversal.

        Args:
            sym: LSP symbol (Pydantic model or dict)
            depth: Remaining traversal depth (-1 = unlimited)
            parent_name: Name of parent symbol (None for top-level)

        Returns:
            Normalized SymbolRecord with nested children
        """
        # Check if input is a Pydantic model
        from llm_lsp_cli.lsp.types import DocumentSymbol as LspDocumentSymbol
        from llm_lsp_cli.lsp.types import SymbolInformation as LspSymbolInformation

        if isinstance(sym, LspDocumentSymbol):
            return self._transform_document_symbol(sym, depth, parent_name)
        elif isinstance(sym, LspSymbolInformation):
            return self._transform_symbol_information(sym, parent_name)
        elif isinstance(sym, dict):
            # Dict-based input (legacy path)
            return self._transform_symbol_dict(cast(dict[str, object], sym), depth, parent_name)
        else:
            # Unknown type - return empty record
            return SymbolRecord(
                file="",
                name="",
                kind=0,
                kind_name="Unknown",
                range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
            )

    def _transform_document_symbol(
        self,
        sym: DocumentSymbol,
        depth: int,
        parent_name: str | None,
    ) -> SymbolRecord:
        """Transform a DocumentSymbol Pydantic model.

        Args:
            sym: DocumentSymbol Pydantic model
            depth: Remaining traversal depth (-1 = unlimited)
            parent_name: Name of parent symbol (None for top-level)

        Returns:
            Normalized SymbolRecord with nested children
        """
        # Extract URI from range if available (DocumentSymbol doesn't have uri)
        # Use workspace as fallback
        file_path = str(self._workspace)

        # Extract fields from Pydantic model
        name = sym.name
        kind = sym.kind
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
        range_val = Range.from_pydantic(sym.range)

        # Optional fields
        detail = sym.detail
        tags = sym.tags or []

        # Preserve selectionRange if present
        selection_range: Range | None = None
        if sym.selection_range:
            selection_range = Range.from_pydantic(sym.selection_range)

        # Process children if depth allows
        children: list[SymbolRecord] = []
        if depth != 0 and sym.children:
            child_depth = depth - 1 if depth > 0 else -1
            for child_sym in sym.children:
                child_record = self._transform_symbol(child_sym, child_depth, name)
                children.append(child_record)

        return SymbolRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            detail=detail,
            container=None,
            tags=tags,
            selection_range=selection_range,
            data=None,
            parent=parent_name,
            children=children,
        )

    def _transform_symbol_information(
        self,
        sym: SymbolInformation,
        parent_name: str | None,
    ) -> SymbolRecord:
        """Transform a SymbolInformation Pydantic model (workspace symbol format).

        Args:
            sym: SymbolInformation Pydantic model
            parent_name: Name of parent symbol (from containerName)

        Returns:
            Normalized SymbolRecord
        """
        # Extract URI from location
        if sym.location is None:
            # Fallback to workspace if no location
            file_path = str(self._workspace)
            range_val = Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=0),
            )
        else:
            uri = sym.location.uri
            file_path = normalize_uri_to_absolute(uri, self._workspace)
            range_val = Range.from_pydantic(sym.location.range)

        # Extract fields from Pydantic model
        name = sym.name
        kind = sym.kind
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")

        # Optional fields
        container = sym.container_name
        tags = sym.tags or []

        return SymbolRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            detail=None,
            container=container,
            tags=tags,
            selection_range=None,
            data=None,
            parent=parent_name,
            children=[],
        )

    def _transform_symbol_dict(
        self,
        sym: dict[str, object],
        depth: int,
        parent_name: str | None,
    ) -> SymbolRecord:
        """Transform a dict-based symbol (legacy path).

        Args:
            sym: LSP symbol dict
            depth: Remaining traversal depth (-1 = unlimited)
            parent_name: Name of parent symbol (None for top-level)

        Returns:
            Normalized SymbolRecord with nested children
        """
        # Get location - handle both workspace and document symbol formats
        location = get_dict(sym, "location") if "location" in sym else sym
        uri = get_str(location, "uri", "")
        range_obj = get_dict(location, "range")
        if not range_obj:
            range_obj = get_dict(sym, "range")

        # Normalize URI to relative path
        file_path = normalize_uri_to_absolute(uri, self._workspace)

        # Extract fields
        name = get_str(sym, "name", "")
        kind = get_int(sym, "kind", 0)
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
        range_val = Range.from_dict(range_obj)

        # Optional fields
        detail = get_optional_str(sym, "detail")
        container = get_optional_str(sym, "containerName")
        tags_raw = get_list(sym, "tags")
        tags = [t for t in tags_raw if isinstance(t, int)]

        # Preserve selectionRange if present
        selection_range: Range | None = None
        sel_range_obj = get_optional_dict(sym, "selectionRange")
        if sel_range_obj:
            selection_range = Range.from_dict(sel_range_obj)

        # Preserve data field if present
        data: object = sym.get("data")

        # Process children if depth allows
        children: list[SymbolRecord] = []
        if depth != 0:
            raw_children = get_list(sym, "children")
            if raw_children:
                child_depth = depth - 1 if depth > 0 else -1
                for child_sym in raw_children:
                    if isinstance(child_sym, dict):
                        child_record = self._transform_symbol_dict(
                            cast(dict[str, object], child_sym), child_depth, name
                        )
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

    def transform_locations(self, locations: Sequence[object]) -> list[LocationRecord]:
        """Transform LSP locations to LocationRecord list.

        Accepts both Pydantic Location models and dict-based inputs (ADR-0027).

        Args:
            locations: LSP location list (Pydantic models or dicts)

        Returns:
            List of normalized LocationRecord objects
        """
        records: list[LocationRecord] = []

        for loc in locations:
            # Check if input is a Pydantic model
            from llm_lsp_cli.lsp.types import Location as LspLocation

            if isinstance(loc, LspLocation):
                # Pydantic model path
                uri = loc.uri
                file_path = normalize_uri_to_absolute(uri, self._workspace)
                range_val = Range.from_pydantic(loc.range)
            else:
                # Dict-based input (legacy path)
                uri = get_str(loc, "uri", "")
                range_obj = get_dict(loc, "range")
                file_path = normalize_uri_to_absolute(uri, self._workspace)
                range_val = Range.from_dict(range_obj)

            records.append(
                LocationRecord(
                    file=file_path,
                    range=range_val,
                )
            )

        return records

    @staticmethod
    def symbol_to_dict(rec: SymbolRecord) -> dict[str, object]:
        """Convert SymbolRecord to dict, omitting null/empty fields.

        Handles nested children recursively.

        Args:
            rec: SymbolRecord to convert

        Returns:
            Dictionary with only present fields (excludes file - it's at top level)
        """
        obj: dict[str, object] = {
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
        obj["children"] = [CompactFormatter.symbol_to_dict(child) for child in rec.children]
        return obj

    def transform_diagnostics(
        self,
        diagnostics: Sequence[object],
        file_path: str | None = None,
    ) -> list[DiagnosticRecord]:
        """Transform LSP diagnostics to DiagnosticRecord list.

        Accepts both Pydantic Diagnostic models and dict-based inputs (ADR-0027).

        Args:
            diagnostics: List of LSP Diagnostic objects (Pydantic models or dicts)
            file_path: Optional known file path (for single-file diagnostics)

        Returns:
            List of normalized DiagnosticRecord objects
        """
        records: list[DiagnosticRecord] = []

        for diag in diagnostics:
            # Check if input is a Pydantic model
            from llm_lsp_cli.lsp.types import Diagnostic as LspDiagnostic

            if isinstance(diag, LspDiagnostic):
                # Pydantic model path
                range_val = Range.from_pydantic(diag.range)
                severity = diag.severity if diag.severity is not None else 1
                code = diag.code
                source = diag.source or ""
                message = diag.message
                tags = diag.tags or []
            else:
                # Dict-based input (legacy path)
                range_obj = get_dict(diag, "range")
                range_val = Range.from_dict(range_obj)

                severity = get_int(diag, "severity", 1)
                code = get_optional_int(diag, "code")
                if code is None:
                    code_str = get_optional_str(diag, "code")
                    code = code_str
                source = get_str(diag, "source", "")
                message = get_str(diag, "message", "")
                tags = [t for t in get_list(diag, "tags") if isinstance(t, int)]

            records.append(
                DiagnosticRecord(
                    file=file_path or "",
                    range=range_val,
                    severity=severity,
                    severity_name=SEVERITY_MAP.get(severity, "Unknown"),
                    code=code,
                    source=source,
                    message=message,
                    tags=tags,
                )
            )

        return records

    @staticmethod
    def diagnostic_to_dict(rec: DiagnosticRecord) -> dict[str, object]:
        """Convert DiagnosticRecord to dict, omitting null/empty fields.

        Translates tags to names and uses compact range format.
        Omits severity integer (keeps severity_name only).
        Omits source field (it's at top level as _source).
        Excludes file - it's at top level.

        Args:
            rec: DiagnosticRecord to convert

        Returns:
            Dictionary with only present fields (excludes file and source)
        """
        obj: dict[str, object] = {
            "range": rec.range.to_compact(),
            "severity_name": rec.severity_name,
            "message": rec.message,
        }
        if rec.code is not None:
            obj["code"] = rec.code
        # Note: source is omitted - it's hoisted to top level as _source
        if rec.tags:
            obj["tags"] = [get_diagnostic_tag_name(t) for t in rec.tags]
        return obj

    def _transform_call_hierarchy_item(self, call: object, item: object) -> CallHierarchyRecord:
        """Transform a single call hierarchy item to CallHierarchyRecord.

        Args:
            call: LSP call dict containing fromRanges
            item: The target item dict (from 'from' or 'to' field)

        Returns:
            Normalized CallHierarchyRecord
        """
        uri = get_str(item, "uri", "")
        range_obj = get_dict(item, "range")

        # Normalize URI to relative path
        file_path = normalize_uri_to_absolute(uri, self._workspace)

        # Extract fields
        name = get_str(item, "name", "")
        kind = get_int(item, "kind", 0)
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
        range_val = Range.from_dict(range_obj)

        # Extract selectionRange if present
        selection_range: Range | None = None
        sel_range_obj = get_optional_dict(item, "selectionRange")
        if sel_range_obj:
            selection_range = Range.from_dict(sel_range_obj)

        # Extract fromRanges
        from_ranges_raw = get_list(call, "fromRanges")
        from_ranges = [
            Range.from_dict(cast(dict[str, object], r))
            for r in from_ranges_raw
            if isinstance(r, dict)
        ]

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
        self, calls: Sequence[object]
    ) -> list[CallHierarchyRecord]:
        """Transform LSP incoming calls to CallHierarchyRecord list.

        Accepts both Pydantic CallHierarchyIncomingCall models and dict-based inputs (ADR-0027).

        Args:
            calls: List of LSP CallHierarchyIncomingCall objects (Pydantic models or dicts)

        Returns:
            List of normalized CallHierarchyRecord objects sorted by file/name
        """
        records: list[CallHierarchyRecord] = []

        for call in calls:
            # Check if input is a Pydantic model
            from llm_lsp_cli.lsp.types import (
                CallHierarchyIncomingCall as LspCallHierarchyIncomingCall,
            )

            if isinstance(call, LspCallHierarchyIncomingCall):
                # Pydantic model path - access from_ field
                record = self._transform_call_hierarchy_incoming_pydantic(call)
            else:
                # Dict-based input (legacy path)
                # Get the 'from' item (may be 'from_' in Python-normalized form)
                from_item: object = None
                if isinstance(call, dict):
                    call_dict = cast(dict[str, object], call)
                    from_item = call_dict.get("from_") or call_dict.get("from", {})
                # Cast call to object to avoid type narrowing issues
                record = self._transform_call_hierarchy_item(cast(object, call), from_item)
            records.append(record)

        # Sort by file then name
        records.sort(key=lambda r: (r.file, r.name))
        return records

    def _transform_call_hierarchy_incoming_pydantic(
        self, call: CallHierarchyIncomingCall
    ) -> CallHierarchyRecord:
        """Transform a CallHierarchyIncomingCall Pydantic model.

        Args:
            call: CallHierarchyIncomingCall Pydantic model

        Returns:
            Normalized CallHierarchyRecord
        """
        # Access the from_ field (aliased from 'from')
        item = call.from_
        uri = item.uri
        file_path = normalize_uri_to_absolute(uri, self._workspace)

        name = item.name
        kind = item.kind
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
        range_val = Range.from_pydantic(item.range)

        # Extract selectionRange if present
        selection_range: Range | None = None
        if item.selection_range:
            selection_range = Range.from_pydantic(item.selection_range)

        # Extract fromRanges
        from_ranges = [Range.from_pydantic(r) for r in call.from_ranges]

        return CallHierarchyRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            selection_range=selection_range,
            from_ranges=from_ranges,
        )

    def transform_call_hierarchy_outgoing(
        self, calls: Sequence[object]
    ) -> list[CallHierarchyRecord]:
        """Transform LSP outgoing calls to CallHierarchyRecord list.

        Accepts both Pydantic CallHierarchyOutgoingCall models and dict-based inputs (ADR-0027).

        Args:
            calls: List of LSP CallHierarchyOutgoingCall objects (Pydantic models or dicts)

        Returns:
            List of normalized CallHierarchyRecord objects sorted by file/name
        """
        records: list[CallHierarchyRecord] = []

        for call in calls:
            # Check if input is a Pydantic model
            from llm_lsp_cli.lsp.types import (
                CallHierarchyOutgoingCall as LspCallHierarchyOutgoingCall,
            )

            if isinstance(call, LspCallHierarchyOutgoingCall):
                # Pydantic model path
                record = self._transform_call_hierarchy_outgoing_pydantic(call)
            else:
                # Dict-based input (legacy path)
                to_item = get_dict(call, "to")
                record = self._transform_call_hierarchy_item(call, to_item)
            records.append(record)

        # Sort by file then name
        records.sort(key=lambda r: (r.file, r.name))
        return records

    def _transform_call_hierarchy_outgoing_pydantic(
        self, call: CallHierarchyOutgoingCall
    ) -> CallHierarchyRecord:
        """Transform a CallHierarchyOutgoingCall Pydantic model.

        Args:
            call: CallHierarchyOutgoingCall Pydantic model

        Returns:
            Normalized CallHierarchyRecord
        """
        item = call.to
        uri = item.uri
        file_path = normalize_uri_to_absolute(uri, self._workspace)

        name = item.name
        kind = item.kind
        kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
        range_val = Range.from_pydantic(item.range)

        # Extract selectionRange if present
        selection_range: Range | None = None
        if item.selection_range:
            selection_range = Range.from_pydantic(item.selection_range)

        # Extract fromRanges
        from_ranges = [Range.from_pydantic(r) for r in call.from_ranges]

        return CallHierarchyRecord(
            file=file_path,
            name=name,
            kind=kind,
            kind_name=kind_name,
            range=range_val,
            selection_range=selection_range,
            from_ranges=from_ranges,
        )

    def transform_completions(
        self, items: Sequence[object], file_path: str
    ) -> list[CompletionRecord]:
        """Transform LSP completion items to CompletionRecord list.

        Accepts both Pydantic CompletionItem models and dict-based inputs (ADR-0027).

        Args:
            items: List of LSP completion items (Pydantic models or dicts)
            file_path: File path for the completion request

        Returns:
            List of normalized CompletionRecord objects
        """
        records: list[CompletionRecord] = []

        for item in items:
            # Check if input is a Pydantic model
            from llm_lsp_cli.lsp.types import CompletionItem as LspCompletionItem
            from llm_lsp_cli.lsp.types import MarkupContent as LspMarkupContent

            if isinstance(item, LspCompletionItem):
                # Pydantic model path
                label = item.label
                kind = item.kind if item.kind is not None else 0
                kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
                detail = item.detail

                # Handle documentation (str | MarkupContent | None)
                documentation: str | None = None
                if item.documentation is not None:
                    if isinstance(item.documentation, LspMarkupContent):
                        documentation = item.documentation.value
                    else:
                        documentation = item.documentation

                # Extract range from textEdit.range
                range_val: Range | None = None
                if item.text_edit is not None:
                    range_val = Range.from_pydantic(item.text_edit.range)

                # Position extraction not supported in Pydantic model path
                # (data field is not defined in CompletionItem)
                position_val: Range | None = None
            else:
                # Dict-based input (legacy path)
                # Extract all values BEFORE isinstance checks to avoid type narrowing issues
                label = get_str(item, "label", "")
                kind = get_int(item, "kind", 0)
                kind_name = SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")
                detail = get_optional_str(item, "detail")
                documentation = None
                doc_raw = get_optional_dict(item, "documentation")
                text_edit = get_optional_dict(item, "textEdit")
                data_obj = get_optional_dict(item, "data")

                # Process documentation
                if doc_raw:
                    documentation = get_str(doc_raw, "value", "")
                elif isinstance(item, dict):
                    item_dict = cast(dict[str, object], item)
                    doc_val = item_dict.get("documentation")
                    if isinstance(doc_val, str):
                        documentation = doc_val

                # Extract range from textEdit.range
                range_val = None
                if text_edit:
                    range_obj = get_optional_dict(text_edit, "range")
                    if range_obj:
                        range_val = Range.from_dict(range_obj)

                # Extract position from data.position
                position_val = None
                if data_obj:
                    pos = get_optional_dict(data_obj, "position")
                    if pos:
                        # Position is a single point, create a Range with same start/end
                        line = get_int(pos, "line", 0)
                        char = get_int(pos, "character", 0)
                        position_val = Range(
                            start=Position(line=line, character=char),
                            end=Position(line=line, character=char),
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

    def transform_hover(self, hover: object, file_path: str) -> HoverRecord | None:
        """Transform LSP hover response to HoverRecord.

        Accepts both Pydantic Hover models and dict-based inputs (ADR-0027).

        Args:
            hover: LSP hover response (Pydantic model, dict, or None)
            file_path: File path for the hover request

        Returns:
            HoverRecord or None if hover is None
        """
        if hover is None:
            return None

        # Check if input is a Pydantic model
        from llm_lsp_cli.lsp.types import Hover as LspHover
        from llm_lsp_cli.lsp.types import MarkupContent as LspMarkupContent

        if isinstance(hover, LspHover):
            # Pydantic model path
            content: str
            if isinstance(hover.contents, LspMarkupContent):
                content = hover.contents.value
            elif isinstance(hover.contents, str):
                content = hover.contents
            elif isinstance(hover.contents, list):
                # Handle array of MarkedString
                first = hover.contents[0] if hover.contents else None
                if first is not None and hasattr(first, "value"):
                    content = first.value or ""
                else:
                    content = ""
            else:
                content = ""

            # Extract range if present
            range_val: Range | None = None
            if hover.range is not None:
                range_val = Range.from_pydantic(hover.range)
        else:
            # Dict-based input (legacy path)
            # Extract all values BEFORE isinstance checks to avoid type narrowing issues
            contents = get_dict(hover, "contents")
            range_obj = get_optional_dict(hover, "range")

            # Extract content from contents
            if contents:
                content = get_str(contents, "value", "")
            elif isinstance(hover, dict):
                hover_dict = cast(dict[str, object], hover)
                contents_val = hover_dict.get("contents")
                if isinstance(contents_val, dict):
                    content = get_str(cast(dict[str, object], contents_val), "value", "")
                elif isinstance(contents_val, list) and contents_val:
                    # Handle array of MarkedString
                    contents_list = cast(list[object], contents_val)
                    first_raw = contents_list[0]
                    if isinstance(first_raw, dict):
                        content = get_str(cast(dict[str, object], first_raw), "value", "")
                    elif isinstance(first_raw, str):
                        content = first_raw
                    else:
                        content = ""
                elif isinstance(contents_val, str):
                    content = contents_val
                else:
                    content = ""
            else:
                content = ""

            # Extract range if present
            range_val = None
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

    def to_compact_dict(self) -> dict[str, object]:
        """Convert to compact dict representation."""
        ...


_T = TypeVar("_T", bound=_HasFile)


def _group_records_by_file(
    records: list[_T],
    items_key: str,
) -> list[dict[str, object]]:
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
    result: list[dict[str, object]] = []
    for file_path in sorted(groups.keys()):
        result.append(
            {
                "file": file_path,
                items_key: [r.to_compact_dict() for r in groups[file_path]],
            }
        )

    return result


def group_symbols_by_file(symbols: list[SymbolRecord]) -> list[dict[str, object]]:
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
) -> list[dict[str, object]]:
    """Group DiagnosticRecords by file path for workspace-diagnostics output.

    Groups are sorted alphabetically by file path.

    Args:
        diagnostics: List of DiagnosticRecord objects to group

    Returns:
        List of group dicts with 'file' and 'diagnostics' keys.
        Each diagnostic is converted via to_compact_dict().
    """
    return _group_records_by_file(diagnostics, "diagnostics")


def group_locations_by_file(
    records: list[LocationRecord],
) -> list[dict[str, object]]:
    """Group LocationRecords by file path for references output.

    Groups are sorted alphabetically by file path. References within each
    group are sorted by range start position (line, character).

    Args:
        records: List of LocationRecord objects to group

    Returns:
        List of group dicts with 'file' and 'references' keys.
        Each reference is a dict with 'range' key (compact format).
    """
    if not records:
        return []

    # Group by file
    groups: dict[str, list[LocationRecord]] = {}
    for record in records:
        file_path = record.file
        if file_path not in groups:
            groups[file_path] = []
        groups[file_path].append(record)

    # Sort by file path and build result with sorted references
    result: list[dict[str, object]] = []
    for file_path in sorted(groups.keys()):
        # Sort references by range start position
        sorted_records = sorted(
            groups[file_path],
            key=lambda r: (r.range.start.line, r.range.start.character),
        )
        result.append(
            {
                "file": file_path,
                "references": [{"range": r.range.to_compact()} for r in sorted_records],
            }
        )

    return result


# =============================================================================
# Rename Grouping
# =============================================================================


@dataclass
class RenameFileRecord:
    """Grouped rename edits for a single file.

    Used by group_rename_edits_by_file to represent all edits in one file.
    """

    file: str
    ranges: list[str] = field(default_factory=list)


def group_rename_edits_by_file(
    records: list[RenameEditRecord],
) -> tuple[str, str, list[RenameFileRecord]]:
    """Group RenameEditRecord objects by file path.

    Hoists old_text/new_text to command level and groups ranges by file.
    Files are sorted alphabetically. Ranges within each file are sorted
    by start position.

    Args:
        records: List of RenameEditRecord objects to group

    Returns:
        Tuple of (old_text, new_text, file_records) where file_records
        is a list of RenameFileRecord objects sorted by file path.
        Returns ("", "", []) for empty input.
    """
    if not records:
        return "", "", []

    # All records should have the same old_text/new_text
    old_text = records[0].old_text
    new_text = records[0].new_text

    # Group by file
    groups: dict[str, list[RenameEditRecord]] = {}
    for record in records:
        file_path = record.file
        if file_path not in groups:
            groups[file_path] = []
        groups[file_path].append(record)

    # Sort by file path and build result with sorted ranges
    file_records: list[RenameFileRecord] = []
    for file_path in sorted(groups.keys()):
        # Sort ranges by start position
        sorted_records = sorted(
            groups[file_path],
            key=lambda r: (r.range.start.line, r.range.start.character),
        )
        ranges = [r.range.to_compact() for r in sorted_records]
        file_records.append(RenameFileRecord(file=file_path, ranges=ranges))

    return old_text, new_text, file_records
