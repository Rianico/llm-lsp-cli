# 14. Text format tree structure and field omission for document symbols

Date: 2026-04-24

## Status

Clarifies [13. Hierarchical symbol output with depth-controlled traversal](0013-hierarchical-symbol-output-with-depth-controlled-traversal.md)

Superceded by [15. Compact range format and kind_name field standardization for all output formats](0015-compact-range-format-and-kind-name-field-standardization-for-all-output-formats.md)

## Context

ADR-0013 specified hierarchical output with `--depth` and format-aware rendering, but TEXT format implementation has gaps:

1. **Depth flag ignored**: TEXT format shows all symbols regardless of `--depth` value
2. **Missing fields**: selectionRange, tags, and detail omitted despite being valuable for LLM context
3. **Flat output**: No visual hierarchy; parent/child relationships invisible
4. **Redundant file field**: CLI displays file path on first line (`file.py:`), yet each symbol repeats it
5. **Inconsistent range format**: ADR-0002 specified compact `"line:char-line:char"` but implementation varies

Constraints:
- LLM token efficiency remains primary (compact ranges, no null fields)
- Must respect `--depth` uniformly across all formats
- Visual tree structure aids human readability without harming LLM parsing

## Decision

Standardize TEXT format as indentation-based tree with complete field display and depth-aware traversal.

**Tree structure specification:**
```
file.py:
  ├── MyClass (5) [1:1-50:1] sel[1:5-1:12] @deprecated
  │   ├── __init__ (9) [10:1-25:1] sel[10:5-10:13]
  │   └── method (6) [30:1-45:1] sel[30:5-30:11]
  └── helper (12) [55:1-80:1] sel[55:1-55:8]
```

**Rendering rules:**
- Indent: 2 spaces per depth level
- Connector: `├──` for intermediate siblings, `└──` for last sibling
- Prefix: `│   ` for continuing parent branches, `    ` for terminated branches
- Fields: `name (kind) [range] sel[selection_range] [tags] [detail]`
- Range format: compact `"line:char-line:char"` (ADR-0002)
- Omitted: `file` field (redundant with CLI header), `null` fields

**Depth enforcement:**
- `--depth 0`: Only symbols at depth 0 (no indent, no children)
- `--depth 1`: Depth 0 + their direct children (1 indent level)
- Recursion stops at specified depth; deeper children excluded

**System boundaries:**
- `SymbolTransformer.transform()`: Depth-limited traversal, returns tree nodes
- `TextRenderer.render()`: Format-aware serialization, handles tree connectors
- `CLIPipeline`: Validates `--depth`, passes to transformer

**Interface contracts:**
```python
@dataclass(frozen=True)
class SymbolNode:
    name: str
    kind: int
    kind_name: str
    range: str  # compact format
    selection_range: str | None
    detail: str | None
    tags: list[str]
    children: tuple[SymbolNode, ...]  # immutable
    depth: int

def transform_symbols(
    symbols: list[DocumentSymbol],
    depth_limit: int,
    current_depth: int = 0
) -> tuple[SymbolNode, ...]: ...

def render_text(nodes: tuple[SymbolNode, ...], base_indent: str = "") -> str: ...
```

**Rejected alternatives:**

- Keep flat TEXT output with `--depth` only affecting JSON/YAML
  - Cons: Inconsistent UX; depth is a structural filter, not a format option

- Use single indent without tree connectors (`  - Name`)
  - Cons: Harder to trace parentage; connectors add clarity at minimal token cost

- Include file field per symbol for machine parseability
  - Cons: 30-40% token overhead; CLI header suffices; LLMs infer from context

- Use structured Position objects in TEXT format
  - Cons: Multi-line output per symbol; compact strings are scannable

- Show full kind name instead of numeric
  - Cons: "Class" vs "5" wastes tokens; LLMs map SymbolKind constants

## Consequences

**Positive:**
- Consistent `--depth` behavior across all output formats
- Visual hierarchy aids human debugging without LLM token penalty
- Complete field coverage (selectionRange, tags) improves LLM context
- File field omission reduces token count 15-20% for multi-symbol files

**Negative:**
- TEXT format implementation more complex (tree rendering logic)
- Breaking change: scripts parsing TEXT output will need updates

**Risks:**
- Deep trees with `--depth -1` produce wide output (mitigate: default depth 1)
- Tag string formatting must handle unknown SymbolTag values gracefully

**Invariants enforced:**
- Transformation is pure: same input + depth = same output
- Immutable data flow: SymbolNode tuples frozen, no mutation during render
- Depth limit strictly enforced: no child rendered beyond limit
