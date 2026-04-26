# 17. Diagnostic output compact range format with tag translation

Date: 2026-04-26

## Status

Accepted

Amends [15. Compact range format and kind_name field standardization for all output formats](0015-compact-range-format-and-kind-name-field-standardization-for-all-output-formats.md)

## Context

ADR-0015 established compact range format for symbols but left diagnostics using legacy 4-field position representation (`line`, `character`, `end_line`, `end_character`). This creates inconsistency and misses token optimization opportunities for the LLM-targeted output format.

Additional design pressure: diagnostic tags (LSP DiagnosticTag) are integers in the protocol (1=Unnecessary, 2=Deprecated) but human-readable names are more useful for LLM consumption. The current output preserves raw integers, requiring consumers to maintain LSP constant mappings.

Constraints:
- LSP data integrity must be preserved internally (severity/tags remain as ints in dataclasses)
- Output transformation happens at format time, not at LSP reception
- Consistency with ADR-0015: same compact range format, same bare format principle
- Token efficiency: single string `"10:5-15:20"` vs 4 separate numeric fields

## Decision

Extend compact range format to diagnostics with human-readable tag translation, maintaining separation between internal LSP representation and output formatting.

**Range format specification:**
- Format: `"start_line:start_char-end_line:end_char"` (identical to ADR-0015)
- Applied to: `range` field replacing 4 position fields in all output formats
- Bare format: no brackets (consistent with updated symbol/location format)

**DiagnosticRecord refactor:**
```python
@dataclass
class DiagnosticRecord:
    file: str
    range: Range              # Compact range object
    severity: int             # Kept for internal filtering/sorting
    severity_name: str
    code: str | int | None
    source: str
    message: str
    tags: list[int]           # Kept as ints internally
    data: dict[str, Any] | None = None
```

**Tag translation:**
```python
DIAGNOSTIC_TAG_MAP: dict[int, str] = {
    1: "Unnecessary",
    2: "Deprecated",
}
```
- Output shows tag names only: `["Unnecessary", "Deprecated"]`
- Unknown tags: `Unknown(N)` pattern (consistent with symbol kind fallback)

**Output format changes:**

| Format | Before | After |
|--------|--------|-------|
| JSON/YAML | 4 position fields + severity int | `range: "10:5-15:20"`, severity_name only |
| TEXT | `10:5-15:20` in message | bare range appended |
| CSV | line,char,end_line,end_character,severity | range,severity_name |

**System boundaries:**
- `DiagnosticRecord`: Internal LSP data preserved (severity/tags as ints)
- `DiagnosticFormatter`: Output transformation (compact ranges, tag names)
- `DIAGNOSTIC_TAG_MAP`: LSP constant mapping isolated in one location

**Interface contracts:**
```python
# Internal (dataclass)
diagnostic.severity  # int: 1=Error, 2=Warning, etc.
diagnostic.tags      # list[int]: [1, 2]

# Output (dict/text/csv)
obj["severity_name"]  # "Error" | "Warning" | "Information" | "Hint"
obj["tags"]           # ["Unnecessary", "Deprecated"] | omitted if empty
obj["range"]          # "10:5-15:20"
```

**Rejected alternatives:**

- Remove `severity` int entirely from dataclass
  - Cons: Breaks internal filtering/sorting by severity level
  - Why not: LSP data integrity principle requires preserving original values

- Keep tags as integers in output with separate `tag_names` field
  - Cons: Redundant data; consumers need only human-readable values
  - Why not: Token efficiency goal; no use case requires numeric tags in output

- Apply compact range but keep brackets `[10:5-15:20]` in TEXT format
  - Cons: Inconsistent with bare format applied to symbols/locations
  - Why not: Consistency across all TEXT output formats

## Consequences

**Positive:**
- Consistent compact range format across symbols, locations, and diagnostics
- 50-60% token reduction on diagnostic position fields
- Human-readable diagnostic tags without LSP constant knowledge
- Clear separation: LSP dataclasses preserve protocol integrity, formatters optimize for consumption

**Negative:**
- Breaking change: consumers parsing 4 position fields must update
- Breaking change: consumers expecting numeric severity/tags must adapt

**Risks:**
- Range parsing errors if line/character values contain colons (mitigated: LSP spec defines as integers)
- Unknown DiagnosticTag values show as "Unknown(N)" (acceptable fallback matching symbol kind pattern)

**Invariants enforced:**
- No output format emits numeric `severity` or `tags`
- All range fields are compact strings, never objects or 4 separate fields
- Internal dataclasses preserve full LSP data for programmatic use
