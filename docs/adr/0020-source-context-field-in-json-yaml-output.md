# 20. Source context field in JSON/YAML output

Date: 2026-04-28

## Status

Accepted

Amends [2. LLM-optimized compact output format](0002-llm-optimized-compact-output-format.md)

## Context

ADR-0002 established compact output formats for LLM consumption, but outputs lacked explicit identification of their data source. When an LLM processes multiple LSP command results, it needs to know:

1. Which LSP server produced the results (e.g., Basedpyright vs Pyright)
2. Which command generated the output (e.g., workspace-symbol vs references)
3. Which file the command operated on (for file-level commands)

TEXT format addressed this with a first-line header (e.g., "Basedpyright: definition of src/main.py"), but JSON/YAML outputs had no equivalent mechanism. This created an asymmetry where TEXT consumers had context that JSON/YAML consumers lacked.

Design pressures:
- LLMs consuming JSON/YAML need to identify output source without external context
- The source information should be immediately visible (first field)
- CSV format should remain unchanged (flat tabular structure)
- Single-record outputs (hover) need the same source context

## Decision

Add a `_source` field as the FIRST field in all JSON/YAML outputs. This field provides context identification for LLM consumers.

**Field specification:**
- Name: `_source` (underscore prefix indicates metadata, not data)
- Position: Always first field in the output object
- Format: `"<ServerName>: <command> [of <file>]"`
- Scope: JSON and YAML formats only (TEXT uses header line, CSV unchanged)

**Output structure by command type:**

| Command Type | Structure | `_source` Example |
|-------------|-----------|-------------------|
| Workspace-level (workspace-symbol, workspace-diagnostics) | `{"_source": "...", "files": [...]}` | `"Basedpyright: workspace-symbol"` |
| File-level list (definition, references, diagnostics, etc.) | `{"_source": "...", "items": [...]}` | `"Basedpyright: definition of src/main.py"` |
| Single record (hover) | `{"_source": "...", ...other fields}` | `"Basedpyright: hover of src/main.py"` |

**Format examples:**

```yaml
_source: "Basedpyright: workspace-symbol"
files:
  - file: src/main.py
    symbols:
      - name: MyClass
        kind_name: Class
        range: "1:1-50:1"
```

```json
{
  "_source": "Basedpyright: definition of src/main.py",
  "items": [
    {"file": "src/types.py", "line": 10, "kind_name": "Class"}
  ]
}
```

```
# TEXT format (unchanged - uses header line)
Basedpyright: definition of src/main.py
src/types.py:10:0 MyClass (Class)
```

**Rejected alternatives:**

- Add `_source` to TEXT format as a field
  - Rejected: TEXT already has a header line that serves this purpose; adding a field would be redundant

- Add `_source` to CSV as a column
  - Rejected: CSV is flat tabular format; metadata column would complicate parsing and not fit the use case

- Use nested structure `{"meta": {"source": "..."}, "data": [...]}`
  - Rejected: Adds nesting depth; LLMs must traverse further to find the source; first-field approach is more direct

- Omit `_source` entirely
  - Rejected: LLMs processing multiple outputs lose context about which command produced which result

## Consequences

**Positive:**
- LLMs can identify output source without external context
- Consistent context availability across TEXT and JSON/YAML formats
- First-field placement ensures immediate visibility
- Enables better traceability when debugging LLM interactions

**Negative:**
- Breaking change: existing JSON/YAML consumers must handle new `_source` field
- Slight output size increase (~30-50 characters per output)

**Risks:**
- Consumers unaware of the field may be confused (mitigate: documentation, underscore prefix convention)
- Field name collision with data fields (mitigate: underscore prefix reserves the namespace)

**Invariants:**
- `_source` is always the first field in JSON/YAML output
- TEXT format uses first-line header, never `_source` field
- CSV format never includes `_source`
- Format is deterministic: same input always produces same `_source` string

**Affected components:**
- `output/dispatcher.py`: Added `_source` parameter to `format()`, `format_list()`, `format_grouped()`
- `commands/lsp.py`: Passes `_source` header to dispatcher for all LSP commands
