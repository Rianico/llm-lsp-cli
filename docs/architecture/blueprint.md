# Architecture Blueprint: llm-lsp-cli

## System Overview

A CLI tool that interacts with language servers to provide code intelligence features for LLM-assisted development. The architecture follows Clean Architecture principles with clear dependency boundaries.

```
+------------------+     UNIX Socket      +-------------------+     stdio     +----------------+
|   CLI Client     | <-----------------> |    LSP Daemon     | <-----------> |   LSP Server   |
| (llm-lsp-cli)    |   (JSON-RPC 2.0)    |   (long-running)  |   (LSP 3.17)  | (pyright, etc) |
+------------------+                     +-------------------+               +----------------+
```

## Layer Boundaries

### Layer 1: CLI Layer (Outer/Presentation)

**Responsibilities:**
- Command routing and argument parsing
- User-facing output formatting
- Error message presentation

**Constraints:**
- MUST NOT contain business logic
- MUST NOT directly call LSP client or infrastructure
- MUST delegate to Application Layer via explicit interfaces

**Current Structure:**
```
src/llm_lsp_cli/
├── cli.py                    # Main entry, app registration only
└── commands/
    ├── daemon.py             # Daemon lifecycle commands
    ├── lsp.py                # LSP action commands
    └── config.py             # Configuration commands
```

### Layer 2: Application Layer

**Responsibilities:**
- Use case orchestration
- Request/response coordination
- Cross-cutting concerns (logging, auth)

**Components:**
- `daemon_client.py`: DaemonClient for transparent auto-start
- `daemon.py`: RequestHandler, DocumentSyncContext
- `ipc/`: JSON-RPC protocol, transport

### Layer 3: Domain Layer (Inner/Core)

**Responsibilities:**
- Business rules and invariants
- Domain entities and value objects
- Domain services

**Components:**
```
domain/
├── entities/                 # ServerDefinition
├── value_objects/            # WorkspacePath, LogLevel
├── services/                 # RenameService, BackupManager, PathValidator
└── repositories/             # ServerRegistryRepo
```

**Key Invariants:**
- Files stay open for session lifetime (no didClose)
- mtime-based cache invalidation is ground truth
- All file modifications backed up before application

### Layer 4: Infrastructure Layer (Outer)

**Responsibilities:**
- External service integration
- I/O operations (filesystem, network)
- Framework-specific implementations

**Components:**
```
infrastructure/
├── config/                   # Config loading, XDG paths
├── ipc/auth/                 # Token/UID validation
├── lsp/                      # ProgressHandler
└── logging/
```

**LSP Transport Type Boundary:**

The LSP transport layer enforces a strict type boundary (ADR-0024):

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

**Boundary Rules:**
1. ONLY `TypedLSPTransport` may import or use `StdioTransport`
2. `StdioTransport.send_request()` returns `object` not `Any`
3. Pydantic validation happens at the boundary, not scattered
4. Inner layers receive validated Pydantic models only
5. `StdioTransport` is not exported from `lsp/__init__.py`

## Configuration System

The configuration system implements a three-tier priority model with deep merge semantics (ADR-0021).

### Configuration Priority

```
Defaults (code) → Global (~/.config/llm-lsp-cli/config.yaml) → Project (./.llm-lsp-cli.yaml)
     Lowest                    Medium                                 Highest
```

| Layer | Source | Merge Behavior |
|-------|--------|----------------|
| Defaults | `DEFAULT_CONFIG` dict in code | Base layer, always present |
| Global | XDG config dir (`~/.config/llm-lsp-cli/config.yaml`) | Deep merge over defaults |
| Project | Current directory (`.llm-lsp-cli.yaml`) | Deep merge over global |

### Merge Strategy

**Deep merge** for nested dictionaries:
```python
# Default: languages.python.command = "basedpyright"
# Project config: languages.python.args = ["--pythonversion", "3.12"]
# Result: languages.python has both command AND args
```

**List replacement** (not concatenation):
```python
# Default: args = ["--stdio"]
# Project config: args = ["--tcp"]
# Result: args = ["--tcp"] (replaced, not merged)
```

### Auto-Initialization

**Zero-friction flow for uvx users:**
1. Missing global config → Auto-created with defaults
2. First-run notice displayed (one-time, yellow console output)
3. Project config optional → Discovered if exists

**Discovery scope:**
- Project config: Current directory only (no parent traversal)
- Global config: XDG Base Directory compliant

### Configuration Architecture

```
+------------------+      loads       +-----------------------+
| ConfigManager    | ---------------> |  DEFAULT_CONFIG       |
| (Infrastructure) |                  |  (Domain constant)    |
+------------------+                  +-----------------------+
         |
         | delegates
         v
+------------------+      pure        +-----------------------+
| deep_merge()     | <-------------> |  Config merge logic   |
| (Pure function)  |    function     |  (No I/O, testable)   |
+------------------+                  +-----------------------+
         |
         | file I/O
         v
+------------------+                  +-----------------------+
| ConfigLoader     | <-------------> |  Filesystem           |
| (Infrastructure) |                  |  (XDG paths)          |
+------------------+                  +-----------------------+
```

**Clean Architecture alignment:**
- `deep_merge()` is pure function (no side effects, no framework deps)
- `ConfigManager` stays in infrastructure layer
- Domain layer defines config structure via Pydantic models (`ClientConfig`)
- Testable without filesystem via dependency injection

## Workspace Detection with root_markers

Workspace and language detection uses per-language `root_markers` configuration instead of hardcoded patterns. This enables user-customizable project root detection following Neovim's LSP pattern.

### root_markers Schema

```python
class LanguageServerConfig(BaseModel):
    command: str
    args: list[str] = []
    env: dict[str, str] = {}
    root_markers: list[str] = []  # Files/dirs indicating project root
```

Default markers per language:
- **python**: `pyproject.toml`, `setup.py`, `requirements.txt`, `.git`
- **typescript**: `tsconfig.json`, `package.json`, `.git`
- **rust**: `Cargo.toml`, `.git`
- **go**: `go.mod`, `.git`
- **json**: `.git`, `package.json`
- **yaml**: `.git`, `.yamllint`

### Detection Algorithm

```
Input: file_path, explicit_workspace?, explicit_language?
│
├─ explicit_workspace AND explicit_language?
│   └─ Return (explicit_workspace, explicit_language)
│
├─ explicit_language?
│   ├─ Get language's root_markers from config
│   ├─ Search upward from file_path for any marker
│   └─ Return (found_root or cwd, explicit_language)
│
└─ Auto-detect
    ├─ Detect language from file extension
    │   ├─ Extension found?
    │   │   ├─ Get that language's root_markers
    │   │   └─ Find root, return (root, language)
    │   └─ Extension not found?
    │       └─ Search all languages' markers from cwd
    │           ├─ Found? Return (root, that_language)
    │           └─ Not found? Return (cwd, None)
    └─ Handle None language → unsupported notification
```

**Component Architecture:**
```
+------------------+      uses       +-----------------------+
| RootDetector     | -------------> |  ClientConfig         |
| (Domain Service) |                |  (root_markers)       |
+------------------+                +-----------------------+
         |
         | implements
         v
+------------------+      pure       +-----------------------+
| find_root_by_    | <------------> |  Path traversal       |
| markers()        |   function     |  (testable)           |
+------------------+                +-----------------------+
```

**Design Decisions:**
- **Per-language markers** over global: Allows Python projects to use `pyproject.toml` while Go projects use `go.mod`
- **Flat list syntax** over nested priority: Simpler implementation covers 95% of use cases
- **File extension priority** over marker-only: `main.py` in a repo with both `Cargo.toml` and `.git` → python, not rust
- **Graceful degradation**: Missing root_markers config → empty list → falls back to CWD

### Unsupported File Types

When no language server is configured for a file type:
```
Unsupported file type: 'txt'. Configured languages: python, typescript, rust, go, java, cpp, csharp, json, yaml.
To add support, configure a language server in .llm-lsp-cli.yaml
```
Exit code: 0 (informational, not error)

## Output Formatter Architecture

The output formatting system uses a Protocol-based Strategy pattern with centralized dispatch to eliminate format logic duplication across CLI commands.

### Architecture

```
+------------------+      implements      +-----------------------+
|  Record Types    | ------------------> |  FormattableRecord    |
|  (dataclasses)   |                     |  (Protocol)           |
+------------------+                     +-----------------------+
          |                                         ^
          | uses                                    | uses
          v                                         |
+------------------+      delegates      +-----------------------+
| CLI Commands     | ------------------> |  OutputDispatcher     |
| (lsp.py)         |                     |  (match/case)         |
+------------------+                     +-----------------------+
```

### Record Types

All LSP responses are normalized to record types implementing `FormattableRecord`:

| Record Type | Commands | ADR |
|-------------|----------|-----|
| `LocationRecord` | references (grouped), definition | ADR-0018 |
| `SymbolRecord` | document-symbol, workspace-symbol | ADR-0013 |
| `DiagnosticRecord` | diagnostics, workspace-diagnostics | ADR-0017 |
| `CallHierarchyRecord` | incoming-calls, outgoing-calls | ADR-0011 |
| `RenameEditRecord` | rename | ADR-0019 |
| `CompletionRecord` | completion | Design-CompactRange |
| `HoverRecord` | hover | Design-CompactRange |

### Protocol Contract

```python
class FormattableRecord(Protocol):
    def to_compact_dict(self) -> dict[str, Any]: ...
    def get_csv_headers(self) -> list[str]: ...
    def get_csv_row(self) -> dict[str, str]: ...
    def get_text_line(self) -> str: ...
```

### Design Invariants

1. **Compact Range Format**: All range fields use `"line:char-line:char"` (ADR-0015)
2. **Human-Readable Names**: Use `kind_name` not numeric `kind` (ADR-0015)
3. **No Format Logic in CLI**: Commands delegate to `OutputDispatcher`
4. **Raw Pipeline Separate**: `--raw` flag bypasses normalization entirely (ADR-0012)

### Dispatcher Pattern

```python
# CLI commands use single dispatch point
dispatcher = OutputDispatcher()
records = formatter.transform_locations(locations)
typer.echo(dispatcher.format_list(records, context.output_format))
```

Benefits:
- Single match/case eliminates fall-through bugs
- Type safety via Protocol
- Extensibility: new formats need one dispatcher method
- Testability: format logic unit-testable without CLI

## Workspace-Level Output Grouping

Workspace-level commands (`workspace-symbol`, `workspace-diagnostics`, `references`) return results spanning multiple files. The output system supports file-grouped presentation for improved LLM context.

### Grouped Output Structure

**JSON/YAML Format:**
```json
[
  {
    "file": "src/main.py",
    "symbols": [
      {"name": "MyClass", "kind_name": "Class", "range": "1:1-50:1"}
    ]
  }
]
```

**TEXT Format (hierarchical):**
```
Basedpyright: workspace-symbol
src/main.py:
  ├── MyClass (Class) [1:1-50:1]
  └── helper (Function) [55:1-80:1]
src/utils.py:
  └── process (Function) [10:1-25:1]
```

**References Format (compact, one line per file):**
```
src/llm_lsp_cli/daemon.py, ranges: [15:1-15:20, 42:5-42:24]
src/llm_lsp_cli/daemon_client.py, ranges: [8:1-8:19, 100:9-100:27]
```

### Architecture

```
+------------------+      groups by file      +-----------------------+
| CompactFormatter | -----------------------> |  Grouped Output       |
|                  |  group_symbols_by_file() |  [{file, items}, ...] |
+------------------+                          +-----------------------+
                                                         |
+------------------+      delegates                      v
| OutputDispatcher | <-------------------+  +-----------------------+
|                  |  format_grouped()    |  |  format_grouped()   |
+------------------+                     |  +-----------------------+
          |                              |
          v                              |
+-----------------------+                |
| JSON/YAML: grouped    |                |
| TEXT: hierarchical    | <--------------+
| CSV: flat (unchanged) |
+-----------------------+
```

### Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `server_name.py` | Resolve server display name from initialize response | `output/server_name.py` |
| `header_builder.py` | Build alert header with server name and command context | `output/header_builder.py` |
| `CompactFormatter.group_*_by_file()` | Group records by file path (symbols, diagnostics, locations) | `output/formatter.py` |
| `OutputDispatcher.format_grouped()` | Format grouped data by output type | `output/dispatcher.py` |
| `OutputDispatcher.format_references_csv()` | Format grouped references as CSV with pipe-separated ranges | `output/dispatcher.py` |
| `text_renderer.py` | Hierarchical TEXT rendering for grouped output | `output/text_renderer.py` |

### Alert Header Pattern

All LSP commands display an alert header indicating the server and command context:

```
<Server>: <command> [of <file>]
```

Examples:
- File-level: `Basedpyright: diagnostics of src/main.py`
- Workspace-level: `Basedpyright: workspace-diagnostics`

The header is prepended to TEXT output only (JSON/YAML remain machine-parseable).

### Design Invariants

1. **CSV Stays Flat**: CSV format does not support nesting; uses existing flat structure with file column
2. **References CSV Uses Pipe Separator**: Ranges are pipe-separated (e.g., `1:5-1:10|5:1-5:20`) to avoid CSV quoting
3. **Memory-Based Grouping**: Records collected in memory before grouping (acceptable for typical workspace sizes)
4. **Server Name Resolution Chain**: `serverInfo.name` → command basename mapping → command basename fallback
5. **Relative Paths**: All file paths normalized to workspace-relative for consistency

## Dependency Rule

Dependencies point inward:
```
CLI Layer -> Application Layer -> Domain Layer <- Infrastructure Layer
```

Domain Layer has NO dependencies on outer layers. Infrastructure implements interfaces defined by inner layers.

## Command Organization

### Two-Level Hierarchy

```
llm-lsp-cli <group> <command>
```

| Group | Commands | Purpose |
|-------|----------|---------|
| `daemon` | start, stop, restart, status | Process lifecycle |
| `lsp` | definition, references, document-symbol, ... | LSP operations |
| `config` | list, init | Configuration management |

### Naming Conventions

- **LSP commands:** Hyphenated lowercase matching LSP method names
  - `document-symbol` (not `document_symbol`)
  - `incoming-calls` (not `incoming_calls`)
- **Daemon commands:** Simple verbs (start, stop, restart, status)
- **Config commands:** Simple verbs (list, init)

## Data Flow: LSP Request

```
1. CLI: llm-lsp-cli lsp definition file.py 10 5
2. commands/lsp.py: Delegate to _execute_lsp_command()
3. daemon_client.py: DaemonClient.request() -> auto-start if needed
4. ipc/unix_client.py: Send JSON-RPC over socket
5. daemon.py: RequestHandler._handle_lsp_method()
6. daemon.py: DocumentSyncContext.__aenter__() -> didOpen if needed
7. lsp/client.py: LSPClient.request_diagnostics(uri, mtime)
8. lsp/cache.py: DiagnosticCache.is_stale(uri, incoming_mtime)
9. Response flows back through layers
```

## Data Flow: Configuration Loading

```
1. CLI/ Daemon: ConfigManager.load()
2. config/manager.py: Load DEFAULT_CONFIG as base
3. config/manager.py: If missing, auto-create global config
4. config/merge.py: deep_merge(base, global_config)
5. config/manager.py: If exists, load .llm-lsp-cli.yaml from CWD
6. config/merge.py: deep_merge(current, project_config)
7. Return ClientConfig(**merged)
```

## Extension Points

1. **New LSP server:** Add JSON to `config/capabilities/`
2. **New LSP method:** Add to `LSPConstants`, `RequestHandler.RESPONSE_KEYS`
3. **New CLI command:** Add to appropriate `commands/*.py`, follow two-level hierarchy
4. **New output format:** Extend `OutputDispatcher`, update `FormattableRecord` protocol
5. **New record type:** Implement `FormattableRecord`, use `CompactFormatter.transform_*`
6. **Workspace-level command with grouping:** Use `format_grouped()` for JSON/YAML, hierarchical renderer for TEXT
7. **New config merge strategy:** Update `deep_merge()` in `config/merge.py`
8. **New language root_markers:** Add to `DEFAULT_CONFIG` in `config/defaults.py`

## Key Invariants

| Invariant | Location | ADR |
|-----------|----------|-----|
| No didClose - files stay open | DocumentSyncContext | ADR-0008 |
| mtime-based cache invalidation | DiagnosticCache | ADR-0008 |
| Default dry-run for renames | RenameService | ADR-0019 |
| Atomic backup before file modify | BackupManager | ADR-0019 |
| Hyphenated LSP command names | commands/lsp.py | This blueprint |
| Compact range format | All record types | ADR-0015 |
| No format logic in CLI | OutputDispatcher | ADR-0018 |
| CSV stays flat (no grouping) | OutputDispatcher | This blueprint |
| Server name resolution chain | output/server_name.py | This blueprint |
| Config priority: Project > Global > Defaults | ConfigManager.load() | ADR-0021 |
| Deep merge for nested config | deep_merge() | ADR-0021 |
| Auto-create global config on first run | ConfigManager.load() | ADR-0021 |
| Current-directory-only project config | ConfigManager.load() | ADR-0021 |
| Config-driven root detection (no hardcoded patterns) | root_detector.py | ADR-0021 |
| Pydantic models for LSP types | lsp/types.py | ADR-0023 |
| Typed transport adapter | lsp/typed_transport.py | ADR-0023 |
| ONLY TypedLSPTransport may access StdioTransport | lsp/ transport boundary | ADR-0024 |
