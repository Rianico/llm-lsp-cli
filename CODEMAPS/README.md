# CODEMAPS - Architecture Documentation

<!-- Generated: 2026-04-25 | Files scanned: 48+ | Updated: Added ADR-0016 reference -->

This directory contains token-lean architectural codemaps for the llm-lsp-cli project.

## Index

| File | Description |
|------|-------------|
| [architecture.md](architecture.md) | System architecture overview |
| [diagnostic-cache.md](diagnostic-cache.md) | Diagnostic cache with mtime-based invalidation |

## Quick Reference

### Architecture Decision Records (ADRs)

See `docs/adr/` for full ADR documents:
- **ADR-0008**: mtime-based cache invalidation
- **ADR-0009**: Cache HIT to INFO level, `--diagnostic-log` option
- **ADR-0010**: `did-change` subcommand for external file change notification
- **ADR-0016**: Server-specific LSP client capabilities loading

### Key Components

```
src/llm_lsp_cli/
  cli.py              # Typer CLI entry point
  daemon.py           # Daemon process management, RequestHandler
  daemon_client.py    # Client for CLI-daemon communication
  lsp/
    client.py         # LSPClient - LSP protocol implementation
    cache.py          # DiagnosticCache, FileState - mtime-based caching
    transport.py      # StdioTransport - process communication
  ipc/
    unix_server.py    # UNIX socket server for daemon
    unix_client.py    # UNIX socket client for CLI
  config/
    manager.py        # ConfigManager - XDG paths, config loading
  output/
    formatter.py      # CompactFormatter - LLM-optimized output
```

### Communication Flow

```
CLI Client ──(UNIX Socket/JSON-RPC)──> Daemon ──(stdio/LSP 3.17)──> LSP Server
```

### Cache Invalidation (ADR-0008)

```
CLI Request with mtime
       |
       v
  mtime > stored?
       |
   Yes | No
       |   --> Return cached diagnostics (INFO: cache HIT)
       v
  Refresh cache:
  1. Update mtime
  2. Increment document_version
  3. Send didChange + diagnostic request
  4. Store result
```

### External Change Notification (ADR-0010)

```
llm-lsp-cli did-change <file>
       |
       v
  File open and mtime matches?
       |
   Yes | No
       |   --> Send didOpen first
       v
  Read file from disk
       |
       v
  Send didChange (full sync)
       |
       v
  Return acknowledgment
```
