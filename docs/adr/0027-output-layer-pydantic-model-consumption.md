# 27. Output Layer Pydantic Model Consumption

Date: 2026-05-09

## Status

Accepted

consumes types from [23. LSP Response Types with Pydantic Models](0023-lsp-response-types-with-pydantic-models.md)

extends boundary pattern from [24. Transport Layer Type Boundary Enforcement](0024-transport-layer-type-boundary-enforcement.md)

## Context

ADR-0023 introduced Pydantic models for LSP types and ADR-0024 enforced the transport boundary. However, the output formatter layer (`output/formatter.py`, `utils/formatter.py`, `utils/type_helpers.py`) still receives `object`-typed dicts from LSP responses and extracts fields via `type_helpers.py` helper functions. This creates 120+ `reportUnknownVariableType`, `reportUnknownArgumentType`, and `reportUnknownMemberType` warnings in src/ alone.

The `type_helpers.py` pattern (isinstance + get on `object`-typed data) is a pre-ADR-0023 bridge that should be retired. When `isinstance(data, dict)` narrows to `dict[Unknown, Unknown]`, basedpyright cannot infer value types, producing cascading unknown-type warnings at every `.get()` call. This is not a checker limitation -- it reflects that the code genuinely lacks type information at these points.

Current warning distribution (src/ only, 247 total):
- `reportUnannotatedClassAttribute`: 99 (Pydantic `model_config` missing annotation)
- `reportUnknownVariableType`: 53 (isinstance narrowing on object-typed dicts)
- `reportUnknownArgumentType`: 44 (downstream of unknown variables)
- `reportUnknownMemberType`: 23 (dict.get() on unknown-keyed dicts)
- `reportUnusedCallResult`: 14 (discarded return values)
- Other: 14

## Decision

Complete the type boundary chain by having the output formatter consume validated Pydantic models from `lsp/types.py` instead of raw `object`-typed dicts. This eliminates the `type_helpers.py` bridge pattern and resolves 120+ unknown-type warnings structurally.

**Fix categories in dependency order:**

1. **Mechanical annotations (99 warnings):** Add `model_config: ConfigDict` annotation to all Pydantic model subclasses. basedpyright requires class attribute annotations on non-final classes; `model_config = ConfigDict(...)` without annotation triggers `reportUnannotatedClassAttribute`.

2. **Unused call results (14 warnings):** Assign discarded return values to `_` per project convention.

3. **Structural: formatter Pydantic consumption (120+ warnings):** Refactor `CompactFormatter` and `format_*` functions to accept typed Pydantic models (`Location`, `DocumentSymbol`, `Diagnostic`, `CallHierarchyItem`, etc.) instead of `object`. This eliminates the `type_helpers.py` extraction pattern for LSP response data.

4. **Remaining infrastructure annotations (14 warnings):** Add class attribute annotations for `_config_file`, `_lock`, `_cache`, etc. in infrastructure classes.

**Migration approach for category 3:**

The daemon's `RequestHandler` already validates LSP responses through `TypedLSPTransport` (ADR-0024). The validated Pydantic models should be passed directly to the output formatter instead of serializing back to dicts. The formatter's `transform_*` methods should accept the corresponding Pydantic model type:

```
transform_symbols(symbols: list[DocumentSymbol | SymbolInformation]) -> list[SymbolRecord]
transform_locations(locations: list[Location | LocationLink]) -> list[LocationRecord]
transform_diagnostics(diagnostics: list[Diagnostic], ...) -> list[DiagnosticRecord]
```

The `type_helpers.py` module remains for non-LSP boundary cases (config parsing, IPC deserialization) where `object`-typed data is unavoidable, but its usage in the formatter layer should be eliminated.

**Rejected: File-level suppression for type_helpers.py**
- Pros: Zero code changes, warnings silenced
- Cons: Hides 25 real type-safety gaps; contradicts project rule against suppressions outside designated zones
- Why not: The warnings are correct -- the code lacks type information. Fix the code.

**Rejected: Annotate type_helpers.py with TypeGuard**
- Pros: Helps basedpyright narrow types within helper functions
- Cons: TypeGuard only narrows the checked value, not dict value types; `.get()` still returns unknown
- Why not: The root problem is `dict[Unknown, Unknown]` from `isinstance(data, dict)` where `data: object`. TypeGuard cannot recover the key/value types.

## Consequences

**Positive:**
- 247 src/ warnings resolved without suppressions
- Formatter layer gains compile-time type safety matching the transport layer
- `type_helpers.py` usage scope reduced to genuine boundary cases
- Pydantic model consumption pattern is consistent end-to-end

**Negative:**
- Formatter method signatures change (breaking change for internal callers)
- Daemon must pass Pydantic models to formatter instead of dicts
- Slightly more import coupling between `lsp/types.py` and `output/`

**Risks:**
- Dual-path complexity during migration (some callers pass dicts, some pass models) -- mitigate with incremental migration and deprecation warnings
- Pydantic model import cycles between `lsp/` and `output/` -- mitigate: `output/` imports from `lsp/types.py`, not the reverse; dependency direction is correct
