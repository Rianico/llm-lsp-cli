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

## Dependency Rule

Dependencies point inward:
```
CLI Layer → Application Layer → Domain Layer ← Infrastructure Layer
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

## Extension Points

1. **New LSP server:** Add JSON to `config/capabilities/`
2. **New LSP method:** Add to `LSPConstants`, `RequestHandler.RESPONSE_KEYS`
3. **New CLI command:** Add to appropriate `commands/*.py`, follow two-level hierarchy
4. **New output format:** Extend `CompactFormatter` or add to `OutputDispatcher`

## Key Invariants

| Invariant | Location | ADR |
|-----------|----------|-----|
| No didClose - files stay open | DocumentSyncContext | ADR-0008 |
| mtime-based cache invalidation | DiagnosticCache | ADR-0008 |
| Default dry-run for renames | RenameService | ADR-0019 |
| Atomic backup before file modify | BackupManager | ADR-0019 |
| Hyphenated LSP command names | commands/lsp.py | This blueprint |
