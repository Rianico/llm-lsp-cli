# System Architecture Overview

<!-- Generated: 2026-04-23 | Files scanned: 48+ | Updated: Added ADR-0009, ADR-0010 documentation -->

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
- `did-change` - External file change notification (ADR-0010)

Daemon lifecycle options:
- `--debug` - Enable debug logging
- `--trace` - Enable transport-level trace logging
- `--diagnostic-log` - Write full diagnostics to diagnostics.log (ADR-0009)

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

See: `docs/adr/0008-mtime-based-cache-invalidation-for-lsp-diagnostics.md`

### ADR-0009: Cache HIT Logging and Diagnostic Log File

**Problem**: Cache HIT messages invisible at default log levels; diagnostic data masked in daemon.log per ADR-0006.

**Solution**:
- Promote cache HIT to INFO level (visible at default log level)
- Add `--diagnostic-log` CLI option for separate file output

**Consequences**:
- Cache behavior observable without debug logging
- Full diagnostic content available for debugging without TRACE noise

See: `docs/adr/0009-promote-cache-hit-to-info-and-add-diagnostic-log-file-output.md`

### ADR-0010: External File Change Notification

**Problem**: External tools (editors, file watchers, CI) that modify files cannot notify LSP server of changes.

**Solution**: Add `did-change` CLI subcommand that:
- Sends `didOpen` first if file not open or mtime differs
- Sends `textDocument/didChange` with full text sync
- Returns acknowledgment (not diagnostics)

**Consequences**:
- External tools can trigger LSP reanalysis without daemon restart
- Clean separation: notification (didChange) vs query (diagnostics)
- Cache coherence via mtime-based invalidation

See: `docs/adr/0010-expose-didchange-subcommand-for-external-file-change-notification.md`

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
