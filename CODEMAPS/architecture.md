# System Architecture Overview

<!-- Generated: 2026-04-23 | Files scanned: 45+ -->

## High-Level Architecture

```
+------------------+     UNIX Socket      +-------------------+     stdio     +----------------+
|   CLI Client     | <-----------------> |    LSP Daemon     | <-----------> |   LSP Server   |
| (llm-lsp-cli)    |   (JSON-RPC 2.0)    |   (long-running)  |   (LSP 3.17)  | (pyright, etc) |
+------------------+                     +-------------------+               +----------------+
```

## Component Layers

### 1. CLI Layer (`cli.py`)

Entry point using Typer. Commands:
- `start/stop/restart/status` - Daemon lifecycle
- `definition/references/hover/completion` - Position-based LSP features
- `document-symbol/workspace-symbol` - Symbol queries
- `diagnostics/workspace-diagnostics` - Diagnostic queries

Key functions:
- `_send_request()` - Routes to DaemonClient
- `_build_request_context()` - Resolves workspace/language
- `CompactFormatter` - LLM-optimized output

### 2. IPC Layer (`ipc/`)

```
unix_client.py  - DaemonClient: Auto-starts daemon if not running
unix_server.py  - UNIXServer: Accepts connections, dispatches to handler
protocol.py     - JSON-RPC 2.0 framing (Content-Length header)
```

### 3. Daemon Layer (`daemon.py`)

```
DaemonManager          - Process lifecycle (PID file, socket, signals)
RequestHandler         - Routes LSP methods to registry
DocumentSyncContext    - Per ADR-001: opens files, no didClose
```

**ADR-001 Invariant**: Files stay open for session lifetime. `DocumentSyncContext.__aexit__` does NOT send didClose.

### 4. LSP Client Layer (`lsp/`)

```
client.py      - LSPClient: Protocol implementation
                 - request_diagnostics(uri, mtime) - uses cache
                 - _ensure_open() - sends didOpen
cache.py       - DiagnosticCache + FileState
                 - is_stale(uri, mtime) - mtime comparison
                 - mtime: float - ground truth for staleness
transport.py   - StdioTransport: Process spawn, notification routing
```

### 5. Configuration Layer (`config/`)

```
manager.py     - ConfigManager: XDG paths, server resolution
schema.py      - Pydantic models for config validation
capabilities/  - Per-server LSP initialize params (JSON)
```

## Data Flow: Diagnostic Request

```
1. CLI: llm-lsp-cli diagnostics src/main.py
2. cli.py: _send_request("textDocument/diagnostic", {...})
3. daemon_client.py: DaemonClient.request() -> auto-start if needed
4. unix_client.py: Send JSON-RPC over socket
5. daemon.py: RequestHandler._handle_lsp_method()
6. daemon.py: DocumentSyncContext.__aenter__() -> didOpen if needed
7. lsp/client.py: LSPClient.request_diagnostics(uri, mtime)
8. lsp/cache.py: DiagnosticCache.is_stale(uri, mtime)
   - If stale: Send didChange + textDocument/diagnostic
   - If fresh: Return cached diagnostics
9. Response flows back through layers
```

## Key Design Decisions

### ADR-001: mtime-Based Cache Invalidation

**Problem**: Previous `diagnostics_version` duplicated `document_version` logic with no clear staleness signal.

**Solution**: Use `mtime` (file modification time) as ground truth:
- `FileState.mtime: float` - stored modification time
- `is_stale(uri, incoming_mtime)` returns `incoming_mtime > stored_mtime`
- CLI sends mtime with every diagnostic request

**Consequences**:
- No didClose - files stay open for session
- Clear cache invalidation semantics
- `previousResultId` optimization preserved

See: `.lsz/20260422/204301_filestate_version_refactor/architect/01-architecture-decision-record.md`

### Output Format (compact-output-prd.md)

LLM-optimized output:
- Flat arrays in JSON (not nested under "symbols")
- Relative paths (strip `file://` and workspace root)
- Compact ranges: `"1:1-50:1"` instead of nested objects
- `--raw` flag for legacy verbose format

## File Structure

```
src/llm_lsp_cli/
  cli.py              # 1400+ lines - Typer commands
  daemon.py           # 730+ lines - Process management
  daemon_client.py    # Auto-start client
  exceptions.py       # CLIError, DaemonStartupError, etc.

  lsp/
    client.py         # 720+ lines - LSPClient
    cache.py          # 290+ lines - DiagnosticCache, FileState
    transport.py      # stdio process management
    types.py          # LSP type definitions
    constants.py      # Method names, constants

  ipc/
    unix_client.py    # Socket client
    unix_server.py    # Socket server
    protocol.py       # JSON-RPC framing

  config/
    manager.py        # ConfigManager
    schema.py         # Pydantic models
    capabilities/     # LSP init params JSON files

  output/
    formatter.py      # CompactFormatter
    symbol_filter.py  # Verbosity-based filtering

  test_filter/
    pattern_engine.py     # Glob pattern matching
    language_registry.py  # Per-language test patterns

  domain/
    services/lsp_method_router.py  # Method -> registry mapping
    value_objects/log_level.py     # TRACE_LEVEL support
```

## Extension Points

1. **New LSP server**: Add JSON to `config/capabilities/`, update `config/defaults.py`
2. **New LSP method**: Add to `LSPConstants`, `RequestHandler.RESPONSE_KEYS`, `LspMethodRouter`
3. **New output format**: Extend `CompactFormatter` or add to `_output_result()`
4. **Test filter patterns**: Update `test_filter/language_registry.py`
