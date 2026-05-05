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

All LSP method names MUST use `LSPConstants` class:

```python
from llm_lsp_cli.lsp.constants import LSPConstants

method = LSPConstants.DEFINITION  # "textDocument/definition"
```

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
- Domain defines structure via Pydantic models
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
    model_config = ConfigDict(populate_by_name=True)

    line: int
    character: int
```

**Required Configuration:**
- Always use `ConfigDict(populate_by_name=True)` to support both snake_case Python fields and camelCase JSON
- Use `Field(..., alias="camelCase")` for fields that differ between Python naming and LSP spec
- Use `Field(default=None)` for optional fields instead of `total=False`

**CamelCase Aliasing Example:**
```python
class InitializeResult(BaseModel):
    """Result of initialize request."""
    model_config = ConfigDict(populate_by_name=True)

    capabilities: ServerCapabilities
    server_info: dict[str, str] | None = Field(None, alias="serverInfo")
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

### Migration Strategy

When migrating from TypedDict to Pydantic:

1. **Phase 1:** Convert type definitions in `lsp/types.py`
2. **Phase 2:** Create typed transport adapter in `lsp/typed_transport.py`
3. **Phase 3:** Update callers incrementally, removing `cast()` calls
4. **Phase 4:** Verify with both mypy and basedpyright

**Forward Compatibility:**
Use `ConfigDict(extra="ignore")` if LSP spec extensions might add unknown fields:
```python
class ServerCapabilities(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
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
