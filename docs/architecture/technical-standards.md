# Technical Standards: llm-lsp-cli

## Code Organization

### File Size Limits

- **Target:** 200-400 lines per file
- **Maximum:** 800 lines (requires justification)
- **Current exceptions:** cli.py (being refactored), daemon.py (730+), lsp/client.py (720+)

### Module Structure

```
src/llm_lsp_cli/
├── commands/                 # CLI command handlers only
│   ├── daemon.py             # ~200 lines
│   ├── lsp.py                # ~800 lines (acceptable: many LSP methods)
│   └── config.py             # ~100 lines
├── domain/                   # Business logic, no framework deps
│   ├── entities/
│   ├── value_objects/
│   ├── services/
│   └── repositories/
├── infrastructure/           # I/O, external services
├── lsp/                      # LSP protocol implementation
├── ipc/                      # Inter-process communication
├── output/                   # Output formatting
└── config/                   # Configuration management
```

### Import Rules

**Order:**
1. Standard library
2. Third-party (typer, pydantic)
3. Local application (llm_lsp_cli)

**Constraints:**
- Domain layer MUST NOT import from CLI, Application, or Infrastructure layers
- CLI layer SHOULD minimize direct imports from Infrastructure
- Use explicit imports over wildcard imports

## Naming Conventions

### Commands

| Type | Pattern | Example |
|------|---------|---------|
| LSP commands | hyphenated-lowercase | `document-symbol`, `incoming-calls` |
| Daemon commands | simple verb | `start`, `stop`, `restart`, `status` |
| Config commands | simple verb | `list`, `init` |
| Utility | simple noun/verb | `version` |

### Python Code

- **Functions/variables:** `snake_case`
- **Classes:** `CamelCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`
- **Type variables:** `PascalCase` (e.g., `T`, `FormattableRecord`)

### LSP Constants

All LSP method names MUST use `LSPConstants` class with `Final[str]` annotations (ADR-0028). `Final` enables the type checker to narrow class attributes to `Literal` types, which is required for `@overload` matching on `send_request`.

```python
from llm_lsp_cli.lsp.constants import LSPConstants

method = LSPConstants.DEFINITION  # Literal["textDocument/definition"]

# LSPConstants definition:
class LSPConstants:
    DEFINITION: Final[str] = "textDocument/definition"
    HOVER: Final[str] = "textDocument/hover"
    # ... all method names
```

**Rule:** `LSPConstants` attributes MUST be `Final[str]`, not `str`. Non-Final `str` prevents overload resolution and forces the type checker to treat the value as an opaque `str` rather than a `Literal`.

## Dependency Direction

### Clean Architecture Enforcement

```
Domain Layer (innermost)
    ↑
Application Layer
    ↑
CLI Layer (outer)
    ↑
Infrastructure Layer (implements interfaces)
```

**Rules:**
1. Inner layers define interfaces (abstract classes, Protocols)
2. Outer layers implement interfaces
3. Dependencies point inward only
4. Domain layer has zero external dependencies (except Python stdlib)

### Testing Implications

- Domain layer tests MUST run without:
  - Typer
  - LSP server
  - Filesystem I/O (use mocks)
- Application layer tests MAY use:
  - In-memory repositories
  - Mock LSP clients
- CLI tests MAY use:
  - Click/Typer testing utilities
  - Subprocess invocation

## CLI Command Structure

### Two-Level Hierarchy Requirement

All commands MUST follow `<group> <command>` pattern:

```python
# commands/lsp.py
import typer

app = typer.Typer(name="lsp", help="LSP operations")

@app.command()
def definition(...): ...

@app.command("document-symbol")
def document_symbol(...): ...
```

### Main Entry Point

```python
# cli.py
from llm_lsp_cli.commands import daemon, lsp, config

app = typer.Typer(...)
app.add_typer(daemon.app, name="daemon")
app.add_typer(lsp.app, name="lsp")
app.add_typer(config.app, name="config")
```

### Global Options

Define global options once, allow per-command override:

```python
@dataclass
class GlobalOptions:
    workspace: str | None = None
    language: str | None = None
    output_format: OutputFormat = OutputFormat.JSON
```

## Error Handling

### Exception Hierarchy

```
CLIError (base)
├── DaemonStartupError
├── DaemonCrashedError
├── ConfigError
└── LSPError
```

### Error Reporting

- CLI layer: Print user-friendly messages to stderr
- Application layer: Raise domain-specific exceptions
- Domain layer: Raise business rule violations

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error / Daemon already running |
| Non-zero | typer.Exit(code) for specific failures |

## Output Formatting

### Protocol-Based Dispatch

All output MUST implement `FormattableRecord` Protocol:

```python
class FormattableRecord(Protocol):
    def to_compact_dict(self) -> dict[str, Any]: ...
    def get_csv_headers(self) -> list[str]: ...
    def get_csv_row(self) -> list[str]: ...
    def get_text_line(self) -> str: ...
```

### Output Formats

- `json`: Compact, flat arrays
- `yaml`: Human-readable structured
- `csv`: Tabular with headers
- `text`: Human-readable plain text

## Configuration Patterns

### Layered Configuration (ADR-0021)

Configuration uses three-tier priority with deep merge:

```
Defaults (code) → Global (~/.config/llm-lsp-cli/config.yaml) → Project (./.llm-lsp-cli.yaml)
```

**Merge Rules:**
- Deep merge for nested dicts (recursive)
- List replacement (not concatenation)
- Top-level scalars: override

**File Locations:**
- Global: XDG Base Directory compliant (`$XDG_CONFIG_HOME/llm-lsp-cli/config.yaml`)
- Project: `./.llm-lsp-cli.yaml` (current directory only, no parent traversal)

**Implementation Pattern:**
```python
# config/merge.py - Pure function, no I/O
def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries. Override takes precedence."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

**Clean Architecture Compliance:**
- `deep_merge()` is pure function (testable without filesystem)
- `ConfigManager` stays in infrastructure layer
- Domain defines config structure via Pydantic models
- Auto-initialization with first-run notice (zero-friction for uvx users)

## Diagnostic Cache

The diagnostic cache implements mtime-based invalidation for LSP diagnostic responses (ADR-0008).

### FileState Dataclass

Location: `src/llm_lsp_cli/lsp/cache.py`

```python
@dataclass
class FileState:
    mtime: float = 0.0              # File modification time (ground truth)
    document_version: int = 0       # LSP document version
    last_result_id: str | None      # Server's diagnostic version
    is_open: bool = False           # Whether didOpen was sent
    diagnostics: list[dict]         # Cached diagnostic items
    uri: str = ""                   # Original file URI
```

### DiagnosticCache Key Methods

| Method | Purpose |
|--------|---------|
| `is_stale(uri, incoming_mtime) -> bool` | Returns `incoming_mtime > stored_mtime` |
| `on_did_open(uri, mtime)` | Sets `is_open=True`, increments version |
| `update_diagnostics(uri, diagnostics, result_id)` | Stores after LSP response |
| `get_diagnostics(uri) -> list[dict]` | Returns cached or empty list |

### Cache Invariants

1. **mtime is ground truth** - Staleness determined solely by mtime comparison
2. **Monotonic document_version** - Never decrements, increments on didChange
3. **No didClose** - Files remain open for session (per ADR-0008)
4. **previousResultId optimization** - Server can return "unchanged" if nothing changed

### Cache HIT Logging (ADR-0009)

Cache HIT messages logged at INFO level:

```
[cache HIT] src/main.py | resultId=abc123 | mtime=1745400000.0 | v=1 | open=True | diags=5
```

### Diagnostic Log File

When started with `--diagnostic-log`, full LSP messages written to `diagnostics.log`:

```bash
llm-lsp-cli daemon start --diagnostic-log
```

- Logger: `llm_lsp_cli.lsp.diagnostic`
- File: `$PWD/.llm-lsp-cli/diagnostics.log`

## Type Annotations

All Python code MUST include comprehensive type annotations. The project maintains dual compliance with **mypy (strict mode)** and **basedpyright (recommended mode)**.

### Type Checker Configuration

**pyrightconfig.json:**
```json
{
  "typeCheckingMode": "recommended",
  "include": ["src", "tests"],
  "extraPaths": ["src"],
  "stubPath": "typings"
}
```

**pyproject.toml (mypy):**
```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

### Annotation Requirements

**Function signatures** MUST annotate all parameters and return types:
```python
# Correct
def process_items(items: list[dict[str, Any]]) -> list[ProcessedItem]:
    ...

# Incorrect - missing return type
def process_items(items: list[dict[str, Any]]):
    ...

# Incorrect - implicit Any
for lang_name, lang_conf in config.items():  # reportAny
    ...
```

**Variable annotations** are required when type cannot be inferred:
```python
# Required - inference fails
config: dict[str, LanguageConfig] = get_config()

# Optional - inference succeeds
name = "llm-lsp-cli"  # str inferred
```

### Prohibited Patterns

**Avoid explicit `Any`** - use specific types or Protocols:
```python
# Avoid
def handler(data: Any) -> Any:
    ...

# Prefer
def handler(data: LSPRequest) -> LSPResponse:
    ...
```

**Avoid untyped dict iteration** - annotate the container:
```python
# Avoid
for key, value in config.items():
    ...

# Prefer
config: dict[str, LanguageConfig] = load_config()
for lang_name, lang_conf in config.items():
    ...
```

### Framework-Specific Suppression Patterns

When framework patterns conflict with strict type checking, use **file-level suppression** over global configuration changes. This preserves checking elsewhere while acknowledging intentional framework usage.

**Typer CLI Default Initializers:**
```python
# pyright: reportCallInDefaultInitializer=false
"""LSP commands for llm-lsp-cli."""

import typer

@app.command()
def definition(
    file: str = typer.Argument(..., help="File path"),  # OK: Typer pattern
    ...
):
    ...
```

**Rationale:** Typer's dependency injection uses default initializers as a DSL for CLI argument definition. This is framework-intentional behavior, not a type safety issue. File-level suppression documents this explicitly while preserving the check for non-CLI code.

**Alternative Rejected:** Global suppression in `pyrightconfig.json` would disable the check across the entire codebase, losing protection against accidental default initializers in domain/application layers.

### Typeshed for Third-Party Stubs

When type stubs are missing for third-party libraries, check typeshed before creating local stubs.

**Resolution Priority:**
1. **Package bundled stubs** - Many modern packages include `py.typed` marker
2. **typeshed stubs** - Install from typeshed via `types-<package>`:
   ```bash
   uv add --dev types-requests types-pyyaml
   ```
3. **Stub-only packages** - Search PyPI for official stub packages
4. **Local stubs in `typings/`** - Only when typeshed does not exist:
   ```
   typings/
   └── some_package/
       └── __init__.pyi
   ```

**Configuration:**
```toml
[tool.mypy]
# Let mypy find typeshed stubs automatically
ignore_missing_imports = false  # Fail on truly missing stubs

[tool.pyright]
stubPath = "typings"  # Local stubs only; typeshed resolved via typeshedPath
```

**Example - Adding typeshed stubs:**
```bash
# Check what stubs are available
uv pip search types-requests  # or check typeshed GitHub

# Add to dev dependencies
uv add --dev types-requests types-urllib3

# Re-run type check
uv run mypy src/
```

### Generic Type Patterns

Use generic types to avoid duplicating logic for different concrete types. Prefer `typing.TypeVar`, `typing.Generic`, and `typing.ParamSpec` over copy-paste implementations.

**TypeVar for Container Types:**
```python
from typing import TypeVar

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)  # For read-only containers

def first(items: list[T]) -> T | None:
    """Works with any list element type."""
    return items[0] if items else None

def find_by_id(items: list[T], id: str, getter: Callable[[T], str]) -> T | None:
    """Generic lookup by ID extractor."""
    for item in items:
        if getter(item) == id:
            return item
    return None
```

**Generic Classes for Reusable Containers:**
```python
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

class LRUCache(Generic[K, V]):
    """Generic LRU cache for any key-value types."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._cache: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> V | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: K, value: V) -> None:
        ...
```

**ParamSpec for Decorators:**
```python
from typing import ParamSpec, TypeVar
import functools

P = ParamSpec("P")
R = TypeVar("R")

def log_execution(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that preserves signature of wrapped function."""
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.debug(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_execution
def fetch_data(url: str, timeout: int = 30) -> dict[str, Any]:
    ...  # Type checker knows: (str, int) -> dict[str, Any]
```

**Bounded TypeVar for Domain Constraints:**
```python
from typing import TypeVar
from abc import ABC, abstractmethod

class FormattableRecord(ABC):
    @abstractmethod
    def to_compact_dict(self) -> dict[str, Any]: ...

T = TypeVar("T", bound=FormattableRecord)

def format_records(records: list[T], fmt: OutputFormat) -> str:
    """Works with any FormattableRecord subtype."""
    if fmt == OutputFormat.JSON:
        return json.dumps([r.to_compact_dict() for r in records])
    ...
```

**Avoid When Not Needed:**
```python
# Unnecessary - no type reuse
T = TypeVar("T")
def only_for_str(items: list[str]) -> str: ...  # Just use str directly

# Prefer - simpler and clearer
def only_for_str(items: list[str]) -> str: ...
```

### Refactoring with Type Safety

When fixing type diagnostics at scale:

1. **Categorize first** - Separate simple annotations from architectural changes
2. **Fix simple first** - Parameter/return types, variable annotations
3. **Defer architecture** - Import cycles, module reorganization require separate review
4. **Verify both tools** - Run both mypy and basedpyright after changes
5. **Test coverage** - All tests must pass; type changes should not alter runtime behavior

### Deferral Criteria

Defer type fixes to architecture review when they require:
- Moving types to resolve import cycles
- Creating new Protocols or abstract base classes
- Reorganizing module structure
- Breaking circular dependencies

Document deferred items in `.lsz/deferred-diagnostics.md` with justification.

## LSP Type Safety Patterns

For LSP protocol types, use Pydantic models instead of TypedDict to achieve both static and runtime type safety (ADR-0023).

### Pydantic Model Conventions

**Basic Pattern:**
```python
from pydantic import BaseModel, Field, ConfigDict

class Position(BaseModel):
    """Position in a text document."""
    model_config: ConfigDict = ConfigDict(populate_by_name=True)

    line: int
    character: int
```

**Required Configuration:**
- Always annotate `model_config` with type `ConfigDict` to satisfy basedpyright `reportUnannotatedClassAttribute` (ADR-0027)
- Always use `ConfigDict(populate_by_name=True)` to support both snake_case Python fields and camelCase JSON
- Use `Field(..., alias="camelCase")` for fields that differ between Python naming and LSP spec
- Use `Field(default=None)` for optional fields instead of `total=False`

**CamelCase Aliasing Example:**
```python
class InitializeResult(BaseModel):
    """Result of initialize request."""
    model_config: ConfigDict = ConfigDict(populate_by_name=True)

    capabilities: ServerCapabilities
    server_info: dict[str, str] | None = Field(None, alias="serverInfo")
```

### Class Attribute Annotation (ADR-0027)

basedpyright's `reportUnannotatedClassAttribute` fires on any class attribute without an explicit type annotation on non-final classes. This includes `model_config` in Pydantic model subclasses and instance attributes assigned in `__init__`.

**Fix pattern for Pydantic `model_config`:**
```python
# WRONG - triggers reportUnannotatedClassAttribute
class Position(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

# CORRECT - explicit annotation satisfies basedpyright
class Position(BaseModel):
    model_config: ConfigDict = ConfigDict(populate_by_name=True)
```

**Fix pattern for infrastructure class attributes:**
```python
# WRONG - unannotated class attributes
class JsonServerDefinitionRepository:
    def __init__(self, config_file: Path) -> None:
        self._config_file = config_file
        self._cache = None
        self._lock = threading.Lock()

# CORRECT - annotate all class attributes
class JsonServerDefinitionRepository:
    _config_file: Path
    _cache: dict[str, ServerDefinition] | None
    _lock: threading.Lock

    def __init__(self, config_file: Path) -> None:
        self._config_file = config_file
        self._cache = None
        self._lock = threading.Lock()
```

### Typed Transport Adapter Pattern

Create typed wrapper methods for LSP requests to centralize validation at the boundary:

```python
class TypedLSPTransport:
    """Adapter that provides typed LSP request methods."""

    def __init__(self, transport: StdioTransport):
        self._transport = transport

    async def send_initialize(self, params: InitializeParams) -> InitializeResult:
        response = await self._transport.send_request("initialize", params.model_dump())
        return InitializeResult.model_validate(response)
```

**Benefits:**
- Validation happens at infrastructure boundary, not scattered across call sites
- Inner layers receive validated Pydantic models
- No `cast()` calls needed
- camelCase JSON preserved via Field aliases

### LSP Transport Type Boundary (ADR-0024)

Enforce a strict type boundary between raw transport and typed adapters:

**Boundary Rules:**
1. **ONLY `TypedLSPTransport` may import or use `StdioTransport`** - No other code may directly access the raw transport
2. **`StdioTransport.send_request()` returns `object` not `Any`** - Forces validation at call sites
3. **Pydantic validation happens at the boundary** - Inner layers receive validated models only
4. **`StdioTransport` is not exported from `lsp/__init__.py`** - Prevents accidental direct usage

**Architecture:**
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

**Migration Checklist:**
- [ ] Change `StdioTransport.send_request()` return type from `Any` to `object`
- [ ] Remove all file-level pyright suppressions from `transport.py`
- [ ] Update `LSPClient` to use `TypedLSPTransport` exclusively
- [ ] Remove `StdioTransport` from `lsp/__init__.py` exports
- [ ] Verify no other code imports `StdioTransport` directly

### Designated Any Layer (ADR-0025)

Formalize the **Designated Any Layer** pattern to contain `Any` usage within infrastructure boundaries:

**Rule:** ONLY `lsp/transport.py` and `ipc/*` may use `Any` internally. All data crossing into application/domain layers MUST be Pydantic-validated concrete types.

**Permitted Locations:**
| File | Justification |
|------|---------------|
| `lsp/transport.py` | Raw LSP JSON-RPC communication |
| `ipc/protocol.py` | JSON-RPC message parsing/building |
| `ipc/unix_client.py` | IPC request/response handling |
| `ipc/unix_server.py` | IPC request handling |

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

**Suppression Pattern for Designated Layer:**
```python
# ipc/protocol.py
# pyright: reportExplicitAny=false
# pyright: reportAny=false
"""JSON-RPC 2.0 protocol definitions.

LSP responses are inherently dynamic; Any is contained to this layer.
All data is validated via Pydantic before crossing to inner layers.
"""
```

**Cleanup Rules for 725 Diagnostics:**
1. **In designated layer** (`transport.py`, `ipc/*`): Fix with annotations or file-level suppression
2. **Outside designated layer**: Add concrete types; defer to architecture review if requires Protocol creation
3. **Never propagate Any** to application/domain layers

### File-Level Suppression Zones

File-level pyright suppressions (`# pyright: reportX=false` at file top) are permitted ONLY in designated zones. All other files MUST fix underlying type issues.

**Permitted Zones:**

| Zone | Files | Justification |
|------|-------|---------------|
| **Transport Layer** | `lsp/transport.py` | Raw LSP JSON-RPC; `Any` contained per ADR-0024 |
| **IPC Layer** | `ipc/protocol.py`, `ipc/unix_client.py`, `ipc/unix_server.py`, `ipc/method_registry.py` | JSON-RPC dynamism contained per ADR-0025/0026 |
| **Third-Party Stubs** | `typings/**/*.pyi` | External library stubs; types defined by upstream |
| **Tests (limited)** | `tests/conftest.py` | `reportMissingTypeStubs` for pytest fixtures only |
| **CLI Commands** | `commands/lsp.py`, `commands/daemon.py`, `commands/config.py` | `reportCallInDefaultInitializer` for Typer patterns only |

**Prohibited Zones (MUST NOT have file-level suppressions):**

| Zone | Examples | Reason |
|------|----------|--------|
| **Domain Layer** | `domain/entities/*.py`, `domain/services/*.py`, `domain/value_objects/*.py` | Core business logic must be fully typed |
| **Application Layer** | `daemon_client.py`, `daemon.py` (core) | Orchestration must use concrete types |
| **General Infrastructure** | `infrastructure/config/*.py`, `server/*.py` | Use Pydantic validation, not suppressions |
| **Output Formatters** | `output/*.py` | Protocol-based; types known at compile time |
| **Utils** | `utils/*.py` | Pure functions with known signatures |

**Suppression Removal Priority:**

1. **Domain layer first** - Zero tolerance for suppressions in business logic
2. **Application layer second** - Fix with proper annotations or `_param` prefix
3. **Infrastructure third** - Replace with Pydantic models at boundaries
4. **CLI last** - Framework patterns justified; general code fixed

**Example - Removing Suppressions:**

```python
# BEFORE (with suppression)
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

def process_config(data: dict) -> list:  # Missing type params
    result = []
    for key, value in data.items():
        result.append(f"{key}: {value}")
    return result

# AFTER (suppressions removed)
def process_config(data: dict[str, object]) -> list[str]:  # Concrete types
    result: list[str] = []
    for key, value in data.items():
        result.append(f"{key}: {value}")
    return result
```

**Diagnostic Quick Fixes:**

| Diagnostic | Fix Pattern | Example |
|------------|-------------|---------|
| `reportUnusedParameter` | Rename to `_param` | `def fn(_unused: str)` |
| `reportUnknownVariableType` | Annotate variable | `result: list[str] = []` |
| `reportUnknownArgumentType` | Use Pydantic model | `Model.model_validate(data)` |
| `reportAny` | Annotate container | `data: dict[str, object]` |
| `reportMissingTypeStubs` | Add typeshed stubs | `uv add --dev types-X` |
| `reportUnannotatedClassAttribute` | Add type annotation | `model_config: ConfigDict = ConfigDict(...)` |
| `reportImplicitStringConcatenation` | Use explicit `+` | `"a" + "b"` not `"a" "b"` |
| `reportPrivateUsage` | Make public or use Protocol | Extract interface |
| `reportUnusedCallResult` | Assign to `_` | `_ = some_list.append(item)` |

### Handling Type Diagnostics and Suppressions

**NO INLINE SUPPRESSIONS** - Never use `# pyright: ignore` or `# type: ignore` to hide diagnostics.

When a type diagnostic appears, fix the underlying issue:

| Diagnostic | Root Cause | Fix |
|------------|------------|-----|
| `reportUnusedParameter` | Parameter in interface not used | Use `_param` prefix convention |
| `reportArgumentType` | Type mismatch at call site | Use Pydantic models for params |
| `reportReturnType` | Return type doesn't match signature | Align signatures or fix types |
| `reportAny` | Implicit Any from untyped container | Annotate container before iteration |
| `reportExplicitAny` | Explicit Any usage | Replace with concrete type or Protocol |
| `reportUnannotatedClassAttribute` | Class attribute without type annotation | Add annotation (e.g., `model_config: ConfigDict = ...`) |
| `reportUnusedCallResult` | Call result discarded | Assign to `_` if intentional |

**`_` Prefix Convention for Unused Parameters:**
```python
# Correct - indicates intentionally unused
async def _handle_notification(
    self, method: str, _params: dict[str, Any]
) -> None:
    pass  # params intentionally not processed

# Wrong - suppression hides the issue
async def _handle_notification(
    self, method: str, params: dict[str, Any]  # pyright: ignore[reportUnusedParameter]
) -> None:
    pass
```

**Always Use Pydantic Models for LSP Params:**
```python
# Correct - typed, validated
from llm_lsp_cli.lsp.types import TextDocumentIdentifier

params = TextDocumentIdentifier(uri=uri).model_dump(mode="json")
result = await self._transport.send_request("textDocument/definition", params)

# Wrong - suppression hides type mismatch
params = {"textDocument": {"uri": uri}}  # dict[str, str], not dict[str, object]
result = await self._transport.send_request(
    "textDocument/definition",
    params,  # pyright: ignore[reportArgumentType]
)
```

**Type Safety Principles:**
1. **Fix, don't suppress** - Every diagnostic indicates a real issue
2. **Use concrete types** - Replace `Any` with specific types or Protocols
3. **Validate at boundaries** - Pydantic models validate external data
4. **Type flows inward** - Inner layers receive validated models, never raw dicts

### Output Layer Pydantic Model Consumption (ADR-0027)

The output formatter layer MUST consume validated Pydantic models from `lsp/types.py`, not raw `object`-typed dicts. This completes the type boundary chain established by ADR-0023/0024/0025.

**Current anti-pattern (pre-ADR-0027):**
```python
# output/formatter.py receives object-typed data and extracts with type_helpers
def transform_symbols(self, symbols: list[dict[str, object]]) -> list[SymbolRecord]:
    for sym in symbols:
        name = _get_str(sym, "name", "")  # object -> str extraction
        kind = _get_int(sym, "kind", 0)   # object -> int extraction
        ...
```

This pattern causes 120+ `reportUnknownVariableType`, `reportUnknownArgumentType`, and `reportUnknownMemberType` warnings because `isinstance(data, dict)` narrows to `dict[Unknown, Unknown]`, and `.get()` calls return unknown types.

**Target pattern (ADR-0027):**
```python
# output/formatter.py receives typed Pydantic models
from llm_lsp_cli.lsp.types import DocumentSymbol, SymbolInformation

def transform_symbols(
    self, symbols: list[DocumentSymbol | SymbolInformation]
) -> list[SymbolRecord]:
    for sym in symbols:
        name = sym.name           # str, no extraction needed
        kind = sym.kind           # int, no extraction needed
        ...
```

**type_helpers.py scope reduction:**

The `type_helpers.py` helper functions (`get_str`, `get_int`, `get_dict`, etc.) remain available for genuine boundary cases where `object`-typed data is unavoidable:
- Config parsing (infrastructure layer, before Pydantic validation)
- IPC deserialization of untyped params
- YAML/JSON file loading

They MUST NOT be used in the output formatter layer, where the data originates from validated Pydantic models in `lsp/types.py`.

**Dependency direction:**
```
lsp/types.py (defines Pydantic models)
    ↑
output/formatter.py (consumes Pydantic models)
    ↑
daemon.py / commands (passes validated models to formatter)
```

This direction is correct: `output/` imports from `lsp/types.py`, not the reverse.

### IPC Generic Type Registry (ADR-0026)

Use method registry with `@overload` decorators for compile-time type safety in IPC layer (ADR-0026).

**Method Registry Pattern:**
```python
# ipc/method_registry.py
from typing import Literal, TypeAlias
from pydantic import BaseModel

# Type alias for method type pairs
MethodTypePair: TypeAlias = tuple[type[BaseModel], type[BaseModel]]

# Registry mapping method names to (ParamsType, ResultType)
METHOD_TYPES: dict[str, MethodTypePair] = {
    "ping": (EmptyParams, PingResult),
    "textDocument/definition": (TextDocumentPositionParams, list[Location]),
    # ... additional methods
}

# Type literal for valid method names (enables IDE autocomplete)
MethodName: TypeAlias = Literal[
    "ping",
    "textDocument/definition",
    # ... all method names
]
```

**@overload Pattern for Type-Safe Client:**
```python
# ipc/unix_client.py
from typing import overload

class UNIXClient:
    @overload
    async def request(
        self, method: Literal["ping"], params: EmptyParams
    ) -> PingResult: ...

    @overload
    async def request(
        self, method: Literal["textDocument/definition"],
        params: TextDocumentPositionParams
    ) -> list[Location]: ...

    # Generic implementation
    async def request(
        self, method: str, params: BaseModel
    ) -> BaseModel | list[BaseModel] | None:
        """Send request and validate response using method registry."""
        # Implementation with runtime validation
```

**Benefits:**
- Compile-time type checking for all IPC method calls
- Method registry enables IDE autocomplete for method names
- Runtime validation catches malformed data at boundary
- Inner layers receive validated Pydantic models (no `cast()` needed)

**Rules:**
1. All IPC methods MUST have `@overload` declarations in `unix_client.py`
2. Method registry MUST define all daemon and LSP proxy methods
3. Pydantic models MUST cover all method params/results in `ipc/models.py`
4. Adding new methods requires updating both registry and overloads

### CLI Typed Request Gateway (ADR-0028)

The `send_request` function in `commands/shared.py` is a typed gateway at the CLI-IPC boundary. It accepts daemon RPC param models (flat camelCase), sends the request via `DaemonClient`, unwraps the keyed response dict, validates the inner value, and returns a typed Pydantic result.

**Two Param Schemas:**

The CLI-to-daemon and daemon-to-LSP channels use different param formats:

| Channel | Format | Models | Example |
|---------|--------|--------|---------|
| CLI -> Daemon | Flat camelCase | `ipc/cli_params.py` | `workspacePath`, `filePath`, `line`, `column` |
| Daemon -> LSP | Nested LSP | `ipc/models.py` | `textDocument.uri`, `position.line` |

**Daemon RPC Param Models:**

Define flat camelCase models that match the daemon's expected wire format:

```python
# ipc/cli_params.py
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

**@overload Pattern for send_request:**

```python
# commands/shared.py
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

# Fallback for unknown methods
@overload
def send_request(
    method: str,
    params: object,
    language: str | None = None,
) -> object: ...

def send_request(
    method: str,
    params: object,
    language: str | None = None,
) -> object:
    # Send request, unwrap response dict, validate inner value
```

**Call Site Migration:**

```python
# BEFORE: dict[str, object] params, dict[str, object] response
response = send_request(
    LSPConstants.DEFINITION,
    {"workspacePath": context.workspace_path, "filePath": str(context.file_path),
     "line": line_index, "column": column_index},
    language=context.language,
)
locations_raw = get_list_of_dicts(response, "locations")
locations = [Location.model_validate(loc) for loc in locations_raw]

# AFTER: typed params, typed return
locations = send_request(
    LSPConstants.DEFINITION,
    DaemonPositionParams(
        workspace_path=context.workspace_path, file_path=str(context.file_path),
        line=line_index, column=column_index,
    ),
    language=context.language,
)
# locations is list[Location] - no extraction or re-validation needed
```

**Rules:**
1. `send_request` MUST have `@overload` declarations for every daemon method
2. Daemon RPC params MUST use flat camelCase models from `ipc/cli_params.py`
3. `send_request` MUST unwrap response dicts (using `RESPONSE_KEYS` mapping) and validate inner values
4. CLI commands MUST NOT call `type_helpers` or `model_validate` on `send_request` results
5. Adding new daemon methods requires updating `LSPConstants`, `DaemonClient` overloads, `send_request` overloads, and daemon RPC params

**Anti-pattern: Extending LSP-nested models with workspacePath**

Do NOT extend `TextDocumentPositionParams` with `workspacePath`. The daemon expects flat camelCase params (`workspacePath`, `filePath`, `line`, `column`), not nested LSP-style params (`textDocument.uri`, `position.line`). Subclassing LSP models for CLI params produces the wrong wire format and forces CLI callers to understand LSP-style nesting.

### Migration Strategy

When migrating from TypedDict/object to Pydantic:

1. **Phase 1:** Convert type definitions in `lsp/types.py` (ADR-0023, complete)
2. **Phase 2:** Create typed transport adapter in `lsp/typed_transport.py` (ADR-0024, complete)
3. **Phase 3:** Migrate output formatter to consume Pydantic models (ADR-0027, in progress)
4. **Phase 4:** Update callers incrementally, removing `type_helpers` usage in formatter
5. **Phase 5:** Verify with both mypy and basedpyright
6. **Phase 6:** Add typed `send_request` gateway with daemon RPC param models (ADR-0028, planned)

**Forward Compatibility:**
Use `ConfigDict(extra="ignore")` if LSP spec extensions might add unknown fields:
```python
class ServerCapabilities(BaseModel):
    model_config: ConfigDict = ConfigDict(populate_by_name=True, extra="ignore")
    # ... fields
```

## Refactoring Standards

### When to Refactor

- File exceeds 800 lines
- Function exceeds 50 lines
- Nesting exceeds 4 levels
- Same logic repeated 3+ times

### Refactoring Process

1. Verify existing behavior with tests
2. Extract to new file/module
3. Update imports
4. Verify tests pass
5. Update architecture documentation

### No Backward Compatibility

Clean breaks preferred over deprecation:
- Update documentation
- Update skill files
- Version bump indicates breaking change
