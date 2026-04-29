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
