# 23. LSP Response Types with Pydantic Models

Date: 2026-05-04

## Status

Accepted

Amended by [24. Transport Layer Type Boundary Enforcement](0024-transport-layer-type-boundary-enforcement.md)

## Context

The LSP protocol layer currently uses `TypedDict` for type definitions (`lsp/types.py`). While this provides static type hints, it offers no runtime validation. The codebase has 763+ type diagnostics stemming from `dict[str, Any]` response types and `cast()` proliferation at call sites.

Current pain points:
- No runtime validation of LSP server responses
- `cast()` calls scattered across the codebase to satisfy type checkers
- Optional fields handled awkwardly with `total=False`
- No single source of truth for LSP type validation

This violates Clean Architecture principles: the boundary between infrastructure (LSP transport) and application layers is weakly typed, forcing inner layers to handle raw untyped dictionaries.

## Decision

Convert all LSP types from `TypedDict` to Pydantic `BaseModel` and introduce a typed transport adapter layer.

**Type Conversion Pattern:**
```python
class Position(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    line: int
    character: int

class InitializeResult(BaseModel):
    capabilities: ServerCapabilities
    server_info: dict[str, str] | None = Field(None, alias="serverInfo")
```

**Typed Transport Adapter:**
```python
class TypedLSPTransport:
    def __init__(self, transport: StdioTransport):
        self._transport = transport

    async def send_initialize(self, params: InitializeParams) -> InitializeResult:
        response = await self._transport.send_request("initialize", params.model_dump())
        return InitializeResult.model_validate(response)
```

**Key Design Choices:**
- Use `ConfigDict(populate_by_name=True)` to support both snake_case Python fields and camelCase JSON
- Validation happens at the infrastructure boundary (typed transport)
- Inner layers receive validated Pydantic models, not raw dicts
- Progressive migration: convert types first, then migrate callers incrementally

**Rejected Alternatives:**

- Keep TypedDict + manual validation: Duplicates effort; no single source of truth
- Type overloads on `send_request()`: Complicates transport; violates single responsibility
- Runtime checking with `beartype`: Adds dependency; Pydantic already in use for config

## Consequences

**Positive:**
- Full static + runtime type safety for LSP responses
- Eliminates `cast()` calls and `reportAny` diagnostics
- Validation centralized at boundary, not scattered across call sites
- camelCase JSON preserved via Field aliases (LSP spec compatibility)

**Negative:**
- Pydantic model instantiation overhead (negligible vs LSP I/O latency)
- Migration requires touching all LSP request call sites
- Slightly more verbose type definitions

**Risks:**
- LSP spec extensions may require model updates (mitigate: use `extra="ignore"` for forward compatibility)
- Incomplete migration leaves mixed TypedDict/Pydantic interfaces (mitigate: phased acceptance criteria)

**Affected Components:**
- Modified: `lsp/types.py` (convert to Pydantic)
- New: `lsp/typed_transport.py` (adapter layer)
- Modified: All callers of `send_request()` (migrate to typed methods)
