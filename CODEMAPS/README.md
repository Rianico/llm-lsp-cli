# CODEMAPS - Architecture Documentation

<!-- Generated: 2026-04-23 | Files scanned: 45+ -->

This directory contains token-lean architectural codemaps for the llm-lsp-cli project.

## Index

| File | Description |
|------|-------------|
| [architecture.md](architecture.md) | System architecture overview |
| [diagnostic-cache.md](diagnostic-cache.md) | Diagnostic cache with mtime-based invalidation |

## Quick Reference

### Architecture Decision Records (ADRs)

- **ADR-001**: mtime-based cache invalidation - see `.lsz/20260422/204301_filestate_version_refactor/architect/01-architecture-decision-record.md`

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

### Cache Invalidation (ADR-001)

```
CLI Request with mtime
       |
       v
  mtime > stored?
       |
   Yes | No
       |   --> Return cached diagnostics
       v
  Refresh cache:
  1. Update mtime
  2. Increment document_version
  3. Send didChange + diagnostic request
  4. Store result
```
