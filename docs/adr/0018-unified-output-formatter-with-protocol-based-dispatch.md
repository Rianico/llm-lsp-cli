# 18. Unified output formatter with protocol-based dispatch

Date: 2026-04-26

## Status

Accepted

Amends [12. Output formatter position preservation and raw LSP response](0012-output-formatter-position-preservation-and-raw-lsp-response.md)

## Context

ADR-0012 established dual pipelines (Compact and Raw) but left format dispatch scattered across CLI commands. Each command implements its own if/elif/else chain for JSON/YAML/CSV/TEXT handling. This caused a production bug: `incoming-calls -o csv` returns JSON because CSV falls through to the default case.

The root cause is violation of the Dependency Rule: CLI commands (outer layer) contain format implementation details that should belong to an inner layer. Adding new record types or formats requires N command updates, leading to missed cases.

Design pressures:
- Type safety: Record types must declare their format capabilities explicitly
- Extensibility: New formats should not require CLI changes
- Testability: Format logic must be unit-testable without CLI integration

## Decision

Centralize format dispatch through a single `OutputDispatcher` using a Protocol-based Strategy pattern. Records implement `FormattableRecord` Protocol; dispatcher selects the appropriate serialization strategy.

**System Boundaries:**
- CLI Layer: Calls `dispatcher.format_list(records, format)`, handles empty results and user messages
- Dispatcher Layer: Single entry point, match/case on OutputFormat, delegates to record methods
- Record Layer: Dataclasses implement `FormattableRecord` with 4 methods: `to_compact_dict()`, `get_csv_headers()`, `get_csv_row()`, `get_text_line()`
- Raw Pipeline: Separate path bypassing normalization entirely (ADR-0012 unchanged)

**Invariants:**
- Records preserve raw LSP data integrity (severity: int, tags: list[int], etc.)
- Output methods transform for consumption; no transformation at construction
- Empty result messaging belongs to CLI, not dispatcher
- `--raw` flag uses separate `RawFormatter` that operates on original LSP dict

**Rejected alternatives:**

- Visitor pattern: Requires double-dispatch, adds indirection without benefit for static record types
- Methods on dataclass: Ties formatting to data structure; harder to test format logic in isolation
- Keep scattered if/elif: Perpetuates the bug source; violates Open/Closed principle

## Consequences

**Positive:**
- Bug elimination: Single match/case in dispatcher prevents fall-through bugs
- Type safety: Protocol ensures records declare all format capabilities
- Extensibility: New format requires one dispatcher method, zero CLI changes
- Testability: Dispatcher and records testable without CLI dependencies

**Negative:**
- Record types must implement 4 methods (boilerplate offset by Protocol clarity)
- Slight indirection cost at dispatch point (negligible for CLI tool)

**Risks:**
- Protocol methods could drift from actual output needs (mitigate: format tests enforce contract)
- Developers may add format logic outside dispatcher (mitigate: code review, linter rule)

**Affected components:**
- New: `output/protocol.py`, `output/dispatcher.py`
- Modified: `output/formatter.py` (records implement Protocol), `cli.py` (replace if/elif chains)
