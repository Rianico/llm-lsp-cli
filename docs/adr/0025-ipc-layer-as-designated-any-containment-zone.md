# 25. IPC Layer as Designated Any Containment Zone

Date: 2026-05-06

## Status

Accepted

Clarifies [24. Transport Layer Type Boundary Enforcement](0024-transport-layer-type-boundary-enforcement.md)

Is clarified by [26. IPC Layer Generic Types with Method Registry](0026-ipc-layer-generic-types-with-method-registry.md)

## Context

ADR-0024 established `transport.py` as the designated type boundary for LSP communication, but the IPC layer (`ipc/protocol.py`, `ipc/unix_client.py`, `ipc/unix_server.py`) also handles dynamic JSON-RPC data. Current state:

1. IPC layer uses `dict[str, Any]` for JSON-RPC params/results (inherently dynamic)
2. IPC is infrastructure layer - should contain `Any` internally, not propagate it
3. Application/domain layers must receive concrete types via Pydantic validation
4. 725+ type diagnostics need clear boundary rules for cleanup

The Clean Architecture dependency rule requires: inner layers (domain/application) must not depend on `Any` from outer layers (infrastructure).

## Decision

Formalize the **Designated Any Layer** pattern: ONLY `lsp/transport.py` and `ipc/*` may use `Any` internally. All data crossing into application/domain layers MUST be Pydantic-validated concrete types.

**Boundary Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                     DESIGNATED ANY LAYER                     │
│                     (Infrastructure Only)                    │
├─────────────────────────────────────────────────────────────┤
│  ipc/protocol.py:     parse_message() -> dict[str, Any]      │
│  ipc/unix_client.py:  request() -> Any                       │
│  lsp/transport.py:    send_request() -> object               │
│           ↓                                                  │
│  TypedLSPTransport (Pydantic validation)                     │
│           ↓                                                  │
│  Domain/Application Layers (concrete types ONLY)             │
└─────────────────────────────────────────────────────────────┘
```

**Rules:**
1. `Any` is permitted ONLY in `transport.py` and `ipc/*`
2. IPC layer may use file-level pyright suppressions for JSON-RPC dynamism
3. Application/domain layers MUST use concrete types (no Any)
4. Validation happens at infrastructure boundary before data enters inner layers

**Rejected: Force `object` instead of `Any` in IPC layer**
- Pros: Forces validation even for raw JSON-RPC
- Cons: IPC layer deals with arbitrary JSON; `object` offers no benefit over `Any` here
- Why not: IPC layer is internal plumbing; `Any` is acceptable with documented boundaries

## Consequences

**Positive:**
- Clear architectural boundary for type safety cleanup
- IPC layer can handle dynamic JSON-RPC without fighting the type checker
- Inner layers guaranteed concrete types via Pydantic validation
- 725 diagnostics have clear remediation path: fix in place if in designated layer, validate if crossing boundary

**Negative:**
- IPC layer remains loosely typed internally
- Must audit all `Any` usage to ensure no leakage to inner layers

**Risks:**
- Accidental `Any` propagation to application layer (mitigate: type checker enforcement)
- Future developers may not understand boundary (mitigate: this ADR + code comments)

## Accepted Boundary Exceptions

Per the type safety cleanup, the following `Any` diagnostics remain outside the designated infrastructure layer. These are accepted as legitimate boundary cases where suppression is not warranted because runtime validation provides safety.

### 1. Typer Context Object (`commands/shared.py`)

Typer's `ctx.obj` is typed as `Any` by the library design. The code uses `isinstance()` validation:

```python
obj: object = ctx.obj
if isinstance(obj, GlobalOptions):
    return obj
return GlobalOptions()
```

**Rationale:** Library constraint; cannot change upstream typing. Runtime validation ensures type safety.

### 2. Dynamic Method Dispatch (`daemon.py`)

The daemon uses `getattr()` for dynamic LSP method dispatch:

```python
registry_func = getattr(self._registry, registry_method)
result = await registry_func(**kwargs)
```

**Rationale:** Dynamic dispatch is intentional for RPC-style method routing. Method names are validated at runtime via registry lookup.

### 3. JSON/YAML Parsing Boundaries

Several files use `json.loads()` or `yaml.safe_load()` which return `Any`:

- `infrastructure/config/loader.py` - Config file parsing (infrastructure layer, acceptable)
- `infrastructure/config/repository/json_server_def_repo.py` - Server definition loading (infrastructure layer, acceptable)
- `domain/services/backup_manager.py` - Manifest JSON parsing

**Rationale:** JSON/YAML parsing inherently returns dynamic data. Pydantic validation or `isinstance()` checks occur immediately after parsing.

### 4. Configuration Dictionary Operations (`config/manager.py`, `commands/shared.py`)

Dictionary operations on config data produce `Any` when using `.get()` with default values:

```python
languages_raw: object = config_data.get("languages", {})
```

**Rationale:** The config schema is deliberately flexible. `isinstance()` validation follows immediately.

### 5. YAML Representation (`utils/yaml_formatter.py`)

The YAML formatter uses `list[Any]` for sequence representation:

```python
def _represent_sequence(dumper: yaml.SafeDumper, data: list[Any]) -> yaml.SequenceNode:
```

**Rationale:** YAML serialization must handle arbitrary data types. The `Any` here is scoped to the representation layer, not propagated to callers.

### Summary

| Location | Count | Category | Rationale |
|----------|-------|----------|-----------|
| `daemon.py` | 5 | Dynamic dispatch | Intentional RPC routing |
| `config/manager.py` | 4 | Config parsing | Immediate Pydantic validation |
| `commands/shared.py` | 4 | Typer ctx.obj | Library constraint |
| `utils/yaml_formatter.py` | 1 | YAML serialization | Scoped to representation |
| `domain/services/backup_manager.py` | 1 | JSON parsing | Immediate isinstance validation |
| `infrastructure/config/loader.py` | 1 | Config parsing | Infrastructure layer (acceptable) |
| `infrastructure/ipc/auth/uid_validator.py` | 6 | Socket operations | Infrastructure layer (acceptable) |
| `infrastructure/config/repository/` | 1 | JSON parsing | Infrastructure layer (acceptable) |

**Total:** 24 Any diagnostics (down from 409, 91% reduction)
