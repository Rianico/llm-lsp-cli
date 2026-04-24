# 12. Output formatter position preservation and raw LSP response

Date: 2026-04-24

## Status

Accepted

Amended by [13. Hierarchical symbol output with depth-controlled traversal](0013-hierarchical-symbol-output-with-depth-controlled-traversal.md)

## Context

ADR-0002 introduced compact output format for LLM token efficiency, but introduced three issues:

1. **Position information loss in structured formats**: YAML output (and JSON to some extent) flattens LSP Range objects into compact strings like `"1:1-50:1"`. This loses the original start/end Position structure, making it impossible for consumers to reliably parse line/character values.

2. **`--raw` flag misalignment**: The `--raw` option claims to output "legacy verbose format" but actually applies transformations (filtering, CSV conversion, path normalization) rather than emitting the original LSP server response unchanged.

3. **Inconsistent data preservation**: Some LSP response fields (selectionRange, tags, data) are discarded during transformation, limiting downstream utility.

These issues affect all output paths: symbols, locations, diagnostics, and call hierarchy.

## Decision

Refactor the output formatter into two distinct pipelines with clear contracts:

**1. Compact Pipeline (default)**
- Transforms LSP responses to `*Record` dataclasses for token efficiency
- Preserves full position data in structured formats (JSON/YAML): emit `{start: {line, character}, end: {line, character}}` instead of compact strings
- Maintains compact range strings only for TEXT and CSV formats where structure is implied by columns
- Preserves all LSP fields in Record classes (selectionRange, tags, data, etc.)

**2. Raw Pipeline (`--raw` flag)**
- Outputs the original LSP server response with zero transformation
- No filtering, no path normalization, no field omission
- Respects output format for serialization only (JSON/YAML pretty-printing allowed)
- Passthrough semantics: what the server sends is what the user receives

**Implementation boundaries:**
- `CompactFormatter`: Responsible only for transformation, not serialization
- `RawFormatter`: Passes through LSP response unchanged
- CLI layer: Selects pipeline based on `--raw` flag
- Output utilities: Handle format-specific serialization (JSON, YAML, CSV, TEXT)

**Rejected alternatives:**

- Keep current `--raw` behavior (partial transformation)
  - Pros: No breaking change
  - Cons: Violates principle of least surprise; "raw" implies unmodified

- Add `--original` flag alongside `--raw`
  - Pros: Backward compatible
  - Cons: Confusing UX; `--raw` is the semantically correct name

- Preserve compact range strings in YAML/JSON
  - Pros: Token efficient
  - Cons: Forces consumers to parse strings; LSP spec already defines Position structure

## Consequences

**Positive:**
- Structured formats (JSON/YAML) now contain parseable position data
- `--raw` flag semantics align with user expectations
- Full LSP response data available when needed
- Clear separation between transformation and passthrough concerns

**Negative:**
- Breaking change: `--raw` output format changes from filtered/converted to pure passthrough
- Slightly larger YAML/JSON payload for compact format (Position objects vs strings)
- More complex formatter tests (two pipelines to validate)

**Risks:**
- Scripts depending on current `--raw` behavior may break (mitigate with clear release notes)
- Position object nesting increases token count slightly (acceptable trade-off for data integrity)

**Affected components:**
- `CompactFormatter` transformation methods
- CLI command handlers for references, symbols, diagnostics, call hierarchy
- Output serialization utilities
- All format output: TEXT, JSON, YAML, CSV
