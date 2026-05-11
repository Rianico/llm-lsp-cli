# 24. Transport Layer Type Boundary Enforcement

Date: 2026-05-05

## Status

Accepted

Amends [23. LSP Response Types with Pydantic Models](0023-lsp-response-types-with-pydantic-models.md)

Clarified by [25. IPC Layer as Designated Any Containment Zone](0025-ipc-layer-as-designated-any-containment-zone.md)

defines boundary enforced by [27. Output Layer Pydantic Model Consumption](0027-output-layer-pydantic-model-consumption.md)

## Context

ADR-0023 established Pydantic models and a typed transport adapter pattern, but did not mandate strict boundary enforcement. Current issues:

1. `StdioTransport.send_request()` returns `Any`, requiring 6 pyright suppressions in `transport.py`
2. `LSPClient` directly instantiates `StdioTransport`, bypassing the typed boundary
3. `cast()` calls proliferate at call sites due to `Any` propagation
4. Inner layers receive untyped data, violating Clean Architecture dependency rules

The type boundary between infrastructure (raw LSP transport) and application layers remains permeable.

## Decision

Enforce a strict type boundary: ONLY `TypedLSPTransport` may access `StdioTransport`. Change return type from `Any` to `object` to force validation at the boundary.

**Boundary Architecture:**
```
┌─────────────────────────────────────────┐
│           TYPE BOUNDARY                 │
├─────────────────────────────────────────┤
│  StdioTransport.send_request() → object │
│              ↓                          │
│  TypedLSPTransport (validation)         │
│              ↓                          │
│  Pydantic Models → Inner Layers         │
└─────────────────────────────────────────┘
```

**Implementation:**
- `StdioTransport.send_request()` returns `object` not `Any`
- Remove all file-level pyright suppressions from `transport.py`
- `LSPClient` uses `TypedLSPTransport` exclusively
- `StdioTransport` removed from public exports in `lsp/__init__.py`

**Rejected Alternatives:**

- Keep `Any` with more suppressions
  - Pros: No code changes
  - Cons: Continues violating Clean Architecture; untyped data leaks inward
  - Why not: Band-aid solution; root cause is wrong return type

- JSONValue union type instead of `object`
  - Pros: More specific than `object`
  - Cons: Complex recursive type; Pydantic accepts `object` anyway
  - Why not: `object` is simpler and achieves same enforcement

## Consequences

**Positive:**
- Type safety enforced at architecture level, not just by convention
- `Any` propagation eliminated; no `cast()` calls needed
- Inner layers receive validated Pydantic models only
- Tests can mock `TypedLSPTransport` without dealing with raw JSON

**Negative:**
- `LSPClient` refactor required to use typed transport
- Temporary suppression needed during migration

**Risks:**
- Existing direct `StdioTransport` usage may break (mitigate: grep validation before merge)
- Performance concern: `model_validate()` at every call (mitigate: negligible vs LSP I/O latency)

**Affected Components:**
- Modified: `lsp/transport.py` (return `object`, remove suppressions)
- Modified: `lsp/client.py` (use `TypedLSPTransport`)
- Modified: `lsp/__init__.py` (remove `StdioTransport` from exports)
