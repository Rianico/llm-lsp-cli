# 26. IPC Layer Generic Types with Method Registry

Date: 2026-05-06

## Status

Accepted

Clarifies [25. IPC Layer as Designated Any Containment Zone](0025-ipc-layer-as-designated-any-containment-zone.md)

extends CLI layer [28. CLI Layer Typed Request Gateway](0028-cli-layer-typed-request-gateway.md)

## Context

ADR-0025 established the IPC layer as a "Designated Any Layer" permitting `Any` usage for raw JSON-RPC handling. However, callers of `UNIXClient.request()` currently receive `Any`, forcing the application layer to use `cast()` and violating Clean Architecture's Dependency Rule (inner layers depending on outer layer types).

Current state:
- `ipc/protocol.py` uses `dict[str, Any]` for raw JSON-RPC (acceptable per ADR-0025)
- `UNIXClient.request()` returns `Any`, requiring `cast()` at call sites
- `daemon_client.py` must cast IPC responses before returning to CLI layer
- No compile-time verification that method names match expected parameter/result types

The goal is to achieve type safety across the IPC boundary while preserving the designated `Any` containment zone for raw JSON-RPC parsing.

## Decision

Implement a method registry with generic types and `@overload` decorators to enforce compile-time type safety for all IPC methods while keeping raw JSON-RPC handling contained to the infrastructure layer.

**Architecture:**
```
ipc/
├── protocol.py          # Raw JSON-RPC (dict[str, Any]) - Designated Any Zone
├── models.py            # Pydantic models for all method params/results
├── method_registry.py   # METHOD_TYPES: dict[str, tuple[type[Params], type[Result]]]
└── unix_client.py       # @overload decorators for type-safe request()
```

**Key Patterns:**
1. **Method Registry**: Maps method names to `(ParamsType, ResultType)` tuples for runtime validation
2. **Literal Method Names**: `MethodName` type alias enables IDE autocomplete and exhaustiveness checking
3. **@overload Decorators**: Each method gets a typed overload for compile-time safety while preserving generic `request()` implementation
4. **Pydantic Validation**: All params/results validated at IPC boundary before crossing to inner layers

**Rejected: Runtime-Only Validation with `object`**
- Pros: Simpler implementation, no overload maintenance
- Cons: Callers must handle `object` everywhere; errors caught late at usage sites
- Why not: Defeats purpose of static type checking; propagates uncertainty to inner layers

**Rejected: Typed Client Subclasses**
- Pros: Clean separation of method-specific clients
- Cons: Fragments the API; requires multiple client instances or complex inheritance
- Why not: Overload approach keeps single `request()` API while adding type safety

## Consequences

**Positive:**
- Compile-time type checking for all IPC method calls
- `cast()` calls eliminated from `daemon_client.py` and CLI layer
- Method registry enables IDE autocomplete for method names
- Runtime validation catches malformed data at boundary with clear errors
- Inner layers receive validated Pydantic models only

**Negative:**
- `@overload` declarations duplicate method type information (mitigated: registry is single source of truth)
- Adding new methods requires updating registry + overloads (mitigated: compile-time enforcement)

**Risks:**
- Registry becomes stale if not updated with new methods (mitigated: type checker catches mismatches)
- Overhead of Pydantic validation at IPC boundary (mitigated: negligible vs IPC I/O latency)
