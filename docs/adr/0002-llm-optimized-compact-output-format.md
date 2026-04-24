# 2. LLM-optimized compact output format

Date: 2026-04-12

## Status

Accepted

Amended by [13. Hierarchical symbol output with depth-controlled traversal](0013-hierarchical-symbol-output-with-depth-controlled-traversal.md)

## Context

The llm-lsp-cli serves LLM consumers (via RTK token optimization). Current output is human-readable but verbose, causing:
- High token usage when LLMs consume output
- Inefficient information density
- Redundant data (kind_name when LLMs know SymbolKind mapping)
- Nested structures that complicate LLM parsing

Current format issues:
- JSON: Nested `{"symbols": [{"location": {"uri": ..., "range": {...}}}]}` structure
- Text: Verbose `SymbolName (Kind) in file://... [range]` format
- CSV: Separate columns for start_line, start_char, end_line, end_char
- Full URIs when relative paths suffice

## Decision

Transform output to LLM-optimized compact format prioritizing token efficiency and information density.

**Key changes:**
1. **File-centric grouping** — Symbols grouped by source file
2. **Flat JSON structure** — Array with `file` field, not nested objects
3. **Compact range format** — `"1:1-50:1"` instead of nested objects
4. **Relative paths** — Strip `file://` prefix and workspace root
5. **Numeric kind only** — Omit `kind_name` (LLMs know the mapping)
6. **Omit null fields** — Skip optional fields instead of `"field": null`

**Format specifications:**

Text format:
```
utils.py:
  MyClass (5) [1:1-50:1]
  my_function (12) [55:1-80:1] -> None
```

JSON format:
```json
[
  {"file": "utils.py", "name": "MyClass", "kind": 5, "range": "1:1-50:1"},
  {"file": "utils.py", "name": "my_function", "kind": 12, "range": "55:1-80:1", "detail": "-> None"}
]
```

CSV format:
```
file,name,kind,range,detail,container,tags
utils.py,MyClass,5,1:1-50:1,,
utils.py,my_function,12,55:1-80:1,-> None,,
```

**Backward compatibility:**
- Add `--raw` flag for legacy verbose format
- Breaking change accepted for default output

Rejected alternatives:
- Keep verbose default with `--compact` opt-in: Poor default for LLM use case
- Nested `{files: {...}}` structure: LLMs handle flat arrays better
- Include kind_name for readability: Redundant, wastes tokens

## Consequences

**Positive:**
- 40-60% token reduction in JSON output
- 30-50% token reduction in text output
- Consistent structure across formats
- Easier for LLMs to parse flat arrays
- Better information density

**Negative:**
- Breaking change for existing tooling
- Humans must use `--raw` for readable output
- Loss of explicit kind names in output

**Risks:**
- Migration friction for existing scripts (mitigated by `--raw` flag)
- Path normalization complexity across platforms
- Range format parsing required by consumers

**Affected commands:**
- `workspace_symbol` — grouped by file
- `document_symbol` — hierarchical
- `references` — grouped by file
- `diagnostics` — compact format
