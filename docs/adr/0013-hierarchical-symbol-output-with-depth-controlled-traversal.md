# 13. Hierarchical symbol output with depth-controlled traversal

Date: 2026-04-24

## Status

Accepted

Amends [2. LLM-optimized compact output format](0002-llm-optimized-compact-output-format.md)
Amends [12. Output formatter position preservation and raw lsp response](0012-output-formatter-position-preservation-and-raw-lsp-response.md)

Amends [2. LLM-optimized compact output format](0002-llm-optimized-compact-output-format.md)

Amends [12. Output formatter position preservation and raw LSP response](0012-output-formatter-position-preservation-and-raw-lsp-response.md)

Clarified by [14. Text format tree structure and field omission for document symbols](0014-text-format-tree-structure-and-field-omission-for-document-symbols.md)

## Context

LSP `DocumentSymbol` responses contain hierarchical `children` arrays that the current formatter flattens, losing method/function relationships to their parent classes. ADR-0002 prioritized token efficiency with flat output, but document symbols are inherently tree-structured. The `-v` (verbose) flag controls field inclusion, not hierarchy depth, creating UX confusion.

Constraints:
- LLM consumption is the primary use case (token efficiency matters)
- Must support both nested (YAML/JSON) and flat (CSV) formats
- Backward compatibility is acceptable to break for cleaner semantics

## Decision

Replace `-v` with `--depth` option and implement recursive traversal with format-aware output.

**Interface contract:**
```python
def transform_symbols(
    symbols: list[DocumentSymbol],
    depth: int = 1,  # 0=top-only, N=N levels, -1=unlimited
    file_path: str = ""
) -> list[dict]: ...
```

**Depth semantics:**
- `--depth 0`: Top-level symbols only (classes, modules, top-level functions)
- `--depth 1` (default): Classes + their direct children (methods, nested functions)
- `--depth N`: Traverse N levels deep
- `--depth -1`: Unlimited depth (full tree)

**Format-specific output patterns:**
- **YAML/JSON**: Nested structure with `children` arrays; parent path stated once at each level
- **TEXT**: Indentation-based tree with `├──`/`└──` visual connectors
- **CSV**: Flat rows with explicit `parent` column (hierarchy denormalized)

**Field selection:**
- Include: `name`, `kind_name` (string, not numeric), `range`, `selection_range`, `detail`, `tags`, `children` (when depth permits)
- Range format: compact string `"line:char-line:char"` (preserved from ADR-0012 for TEXT/CSV; structured Position objects for JSON/YAML per ADR-0012)

**Rejected alternatives:**

- Keep `-v` alongside `--depth`
  - Cons: Two options controlling overlapping concerns; `-v` was specifically for field verbosity, now subsumed by depth-based hierarchy

- Default depth 0 (top-level only)
  - Cons: Most LLM queries want "class and its methods," not just "class"

- Default depth 2+ or unlimited
  - Cons: Deep nesting wastes tokens when most use cases need 1-2 levels; `--depth -1` available for full traversal

- Flat YAML/JSON with parent references
  - Cons: Less token-efficient (parent repeated per child); tree structure is natural for document symbols

- Dot-notation names (`Class.method`)
  - Cons: Complicates name extraction; separate `parent` column in CSV is cleaner

## Consequences

**Positive:**
- Hierarchical relationships preserved for LLM context understanding
- Single `--depth` option replaces confusing `-v` semantics
- Default depth 1 matches common "class + methods" exploration pattern
- Format-aware output: nested where natural (YAML/JSON), flat where required (CSV)

**Negative:**
- Breaking change: `-v` flag removed (migration: use `--depth` instead)
- Slightly more complex formatter (recursive traversal vs flat mapping)
- YAML/JSON payloads larger with nested structure vs flat array

**Risks:**
- Scripts using `-v` will fail (mitigate: clear release notes, major version bump consideration)
- Infinite recursion if LSP returns cyclic references (mitigate: track seen symbol IDs, though LSP spec prohibits cycles)

**System boundaries:**
- `SymbolTransformer`: Traverses DocumentSymbol tree, enforces depth limit
- `FormatRenderer`: Serializes transformed output per format rules
- CLI layer: Validates `--depth` argument, passes to formatter
- `--raw` bypass: Preserves existing ADR-0012 passthrough semantics, ignores `--depth`
