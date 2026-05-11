# 28. CLI Layer Typed Request Gateway

Date: 2026-05-10

## Status

Accepted

extends [26. IPC Layer Generic Types with Method Registry](0026-ipc-layer-generic-types-with-method-registry.md)

## Context

ADR-0026 established `@overload` declarations on `DaemonClient.request` and `UNIXClient.request` using IPC Pydantic models (`TextDocumentPositionParams`, etc.). However, the CLI command layer still calls `send_request` with `dict[str, object]` params and receives `dict[str, object]` responses, forcing 12 call sites in `lsp.py` to manually extract and re-validate data.

Three problems block direct reuse of the IPC models for `send_request` overloads:

1. **Param format mismatch**: The daemon's `_handle_lsp_method` expects flat camelCase params (`workspacePath`, `filePath`, `line`, `column`). The IPC models use nested LSP-style structure (`textDocument.uri`, `position.line`). Subclassing `TextDocumentPositionParams` with an added `workspacePath` field would serialize to the wrong wire format.

2. **DaemonClient overloads are unreachable from CLI**: `send_request` casts the method to `MethodName`, which matches the fallback overload returning `object`. The specific overloads returning typed results (e.g., `list[Location]`) are never triggered.

3. **Daemon wraps responses in keyed dicts**: The daemon returns `{"locations": [...]}`, `{"hover": ...}`, etc., not the bare typed values. The `DaemonClient.request` overloads incorrectly claim to return `list[Location]` for `textDocument/definition` when the actual return is `dict[str, object]`.

4. **LSPConstants uses `str` not `Final`**: `LSPConstants.DEFINITION: str` prevents the type checker from narrowing to `Literal["textDocument/definition"]`, so `@overload` with `Literal` would not match at call sites.

## Decision

Make `send_request` a typed gateway at the CLI-IPC boundary: accept daemon RPC param models, unwrap response dicts, validate inner values, and return typed Pydantic results.

**1. Daemon RPC param models**: Define flat camelCase models in `ipc/cli_params.py` that match the daemon's expected wire format. These are distinct from the LSP-nested IPC models in `ipc/models.py`.

```python
class DaemonPositionParams(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
    workspace_path: str = Field(alias="workspacePath")
    file_path: str = Field(alias="filePath")
    line: int = 0
    column: int = 0

class DaemonFileParams(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
    workspace_path: str = Field(alias="workspacePath")
    file_path: str = Field(alias="filePath")

class DaemonWorkspaceParams(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
    workspace_path: str = Field(alias="workspacePath")

class DaemonRenameParams(DaemonPositionParams):
    new_name: str = Field(alias="newName")

class DaemonSymbolQueryParams(DaemonWorkspaceParams):
    query: str
```

These serialize via `model_dump(mode="json", by_alias=True)` to the exact flat format the daemon expects.

**2. `@overload` on `send_request`**: Each method gets a typed overload accepting daemon RPC params and returning the inner validated type, not the wrapper dict.

```python
@overload
def send_request(
    method: Literal["textDocument/definition"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> list[Location]: ...

@overload
def send_request(
    method: Literal["textDocument/hover"],
    params: DaemonPositionParams,
    language: str | None = None,
) -> Hover | None: ...
```

**3. `LSPConstants` as `Final`**: Change class attributes from `str` to `Final[str]` so the type checker narrows to `Literal` at call sites, enabling overload matching.

**4. Response unwrapping and validation**: The `send_request` implementation extracts the inner value from the wrapper dict using the daemon's `RESPONSE_KEYS` mapping, then validates with the appropriate Pydantic model. Validation failure raises an error (no fallback to dict).

**5. Fix `DaemonClient.request` overloads**: Correct the return types to reflect that the daemon wraps results in keyed dicts, or add unwrapping logic to the implementation so the overloads are accurate.

**Rejected: Extend `TextDocumentPositionParams` with `workspacePath`**
- Pros: Reuses existing models, single param schema
- Cons: Serializes to nested LSP format that the daemon cannot parse; forces CLI callers to understand LSP-style nesting (`textDocument.uri`, `position.line`) when they have flat `workspace_path`, `file_path`, `line`, `column`
- Why not: Wrong wire format; layering violation that pushes LSP abstractions into the CLI layer

**Rejected: Keep `dict[str, object]` params, overloads only on returns**
- Pros: Minimal param change, no new models
- Cons: Params remain untyped; half the type safety goal unmet; `object` still propagates from call sites
- Why not: Incomplete solution; the params side has the most `object` propagation

**Rejected: Refactor daemon to accept nested LSP params**
- Pros: Single set of models; unified wire format
- Cons: Large daemon refactor; breaks backward compatibility; conflates CLI-to-daemon protocol with daemon-to-LSP protocol
- Why not: Two different protocols with two different schemas; forcing them into one model creates coupling

## Consequences

**Positive:**
- Full compile-time type safety from CLI command to output layer
- `object` propagation eliminated from `send_request` return path
- No `cast()`, `type_helpers`, or re-validation in CLI commands
- Daemon RPC params are explicit and validated at the CLI boundary
- `LSPConstants` as `Final` enables overload matching for free

**Negative:**
- New param model definitions in `ipc/cli_params.py` (5 models)
- `send_request` gains response validation responsibility (appropriate for a boundary function)
- `LSPConstants` becomes immutable (Final) -- no runtime mutation of method names

**Risks:**
- Daemon RPC param models could drift from daemon's expected format -- mitigate with integration tests against `RESPONSE_KEYS`
- Validation failure now raises instead of falling back to dict -- mitigate: correct behavior per ADR-0027; formatter should accept only Pydantic models
- `DaemonClient.request` overloads need correction for the wrapper dict issue -- mitigate: fix in same PR or mark as known tech debt
