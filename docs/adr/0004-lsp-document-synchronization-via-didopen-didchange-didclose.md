# 4. LSP document synchronization via didOpen-didChange-didClose

Date: 2026-04-19

## Status

Accepted

amended by [10. expose-didChange-subcommand-for-external-file-change-notification](0010-expose-didchange-subcommand-for-external-file-change-notification.md)

## Context

The llm-lsp-cli uses a long-running daemon process to communicate with LSP servers. When users invoke `diagnostics` or `document_symbol` subcommands, the LSP server may return stale analysis results because:

1. The daemon maintains persistent LSP connections across multiple CLI invocations
2. Files may be modified externally (by editors, git operations, etc.) between daemon requests
3. The LSP server only reanalyzes files it knows about via textDocument lifecycle notifications
4. Without this sequence, LSP servers like pyright serve cached/stale diagnostics

The LSP protocol specifies document state tracking via:
- `textDocument/didOpen` - Document opened (initial content)
- `textDocument/didChange` - Document content changed
- `textDocument/didClose` - Document closed (server may discard state)

## Decision

Implement document synchronization within the daemon layer using a context manager pattern.

When the daemon receives a file-specific request, it internally executes the complete `didOpen` → request → `didClose` sequence as an atomic operation:

1. Read current file content from disk
2. Send `textDocument/didOpen` with content
3. Send the actual LSP request (`textDocument/diagnostic`, etc.)
4. Send `textDocument/didClose` to clean up
5. Return result to CLI

This keeps the CLI-to-daemon protocol simple while ensuring fresh LSP analysis.

Rejected alternatives:
- CLI manages document lifecycle: Violates separation of concerns; CLI shouldn't know LSP protocol details
- Keep documents permanently open: Memory leaks over time, conflicts with external editors
- Rely on workspace/diagnostic push mode only: Doesn't solve stale analysis for ad-hoc file queries

## Consequences

**Positive:**
- Fresh analysis for every request
- Simple CLI-to-daemon protocol
- Works with all LSP servers following the spec
- Per-request isolation prevents state leakage

**Negative:**
- Additional overhead per request (didOpen/didClose round-trips)
- File must be re-read from disk each time
- LSP server resets diagnostic version on each open

**Risks:**
- Performance impact for rapid successive queries (mitigated by caching at CLI level)
- Race conditions if file changes between read and didOpen
