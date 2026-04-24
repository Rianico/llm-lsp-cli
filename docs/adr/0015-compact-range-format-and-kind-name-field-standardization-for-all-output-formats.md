# 15. Compact range format and kind_name field standardization for all output formats

Date: 2026-04-24

## Status

Accepted

Supercedes [14. Text format tree structure and field omission for document symbols](0014-text-format-tree-structure-and-field-omission-for-document-symbols.md)

## Context

ADR-0014 and ADR-0013 established hierarchical output with `--depth` control, but implementation deviates from the design specification in three critical ways:

1. **Range format inconsistency**: JSON/YAML emit structured Position objects (`{"start": {"line": 22, "character": 6}}`) instead of compact strings (`"22:6-22:16"`)
2. **Redundant kind field**: All formats include numeric `kind` (5) alongside `kind_name`; design specifies `kind_name` only
3. **TEXT format uses numeric kind**: Shows `(5)` instead of human-readable `(Class)`

Constraints:
- Token efficiency is primary goal (compact strings save 60-70% vs structured objects)
- LLMs parse `"line:char-line:char"` effortlessly
- Human readability favors `kind_name` over numeric constants
- All formats must behave consistently (no format-specific field variations)

## Decision

Standardize ALL output formats (JSON, YAML, TEXT, CSV) to use compact range strings and `kind_name` exclusively.

**Range format specification:**
- Format: `"start_line:start_char-end_line:end_char"`
- Example: `"22:6-22:16"` (single line), `"22:0-231:12"` (multi-line)
- Applied to: `range` and `selection_range` fields in all formats
- Zero-based indexing per LSP 3.17 specification

**Field standardization:**
- Include: `kind_name` (human-readable: "Class", "Method", "Function")
- Exclude: numeric `kind` field entirely (not "both", not "optional")

**Format-specific application:**

```yaml
# YAML (nested structure, compact ranges, kind_name only)
- name: UNIXServer
  kind_name: Class
  range: "22:0-231:12"
  selection_range: "22:6-22:16"
  detail: null
  tags: []
  children:
    - name: __init__
      kind_name: Method
      range: "25:4-37:53"
```

```json
// JSON (same structure, compact ranges, kind_name only)
{
  "name": "UNIXServer",
  "kind_name": "Class",
  "range": "22:0-231:12",
  "selection_range": "22:6-22:16"
}
```

```
# TEXT (tree structure, kind_name in parens)
unix_server.py
└── UNIXServer (Class) [22:0-231:12] sel:22:6-22:16
    ├── __init__ (Method) [25:4-37:53] sel:25:8-25:16
```

```csv
# CSV (flat, parent column, compact ranges)
file,name,kind_name,range,selection_range,detail,tags,parent
unix_server.py,UNIXServer,Class,22:0-231:12,22:6-22:16,,,
```

**System boundaries:**
- `CompactFormatter` (JSON/YAML/CSV): Serializes with compact ranges, excludes numeric `kind`
- `SymbolTransformer`: Emits nodes with `kind_name`, no `kind` field
- `TextRenderer`: Formats tree with `kind_name` in parentheses

**Interface contract:**
```python
@dataclass(frozen=True)
class SymbolNode:
    name: str
    kind_name: str  # NOT kind: int
    range: str      # compact: "line:char-line:char"
    selection_range: str | None
    detail: str | None
    tags: list[str]
    children: tuple[SymbolNode, ...]
    depth: int
```

**Rejected alternatives:**

- Keep structured Position objects for JSON/YAML "for type safety"
  - Cons: 3x token overhead; adds no semantic value; LLMs parse strings fine

- Include both `kind` and `kind_name` for "flexibility"
  - Cons: Violates token efficiency goal; consumers can map names if needed; no use case requires numeric

- Use numeric kind in TEXT for "compactness"
  - Cons: "(5)" vs "(Class)" difference is 3 tokens; readability loss outweighs gain

- Format-specific range representations (compact for TEXT, objects for JSON)
  - Cons: Inconsistent consumer experience; no technical reason to differ

## Consequences

**Positive:**
- 60-70% token reduction on range fields vs structured Position objects
- Consistent field schema across all output formats
- Human-readable output without consulting SymbolKind constants
- Simplified consumer parsing (single string split vs nested object traversal)

**Negative:**
- Breaking change: consumers parsing structured range objects must update
- Breaking change: consumers relying on numeric `kind` field must map from `kind_name`

**Risks:**
- Range parsing errors if line/character values contain colons (mitigate: LSP spec defines line/char as integers)
- Unknown SymbolKind values result in "Unknown" kind_name (acceptable fallback)

**Invariants enforced:**
- No format emits numeric `kind` field
- All range fields are compact strings, never objects
- `kind_name` mapping is deterministic: same numeric input = same string output
