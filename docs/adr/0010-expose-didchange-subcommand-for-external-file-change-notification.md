# 10. Expose didChange subcommand for external file change notification

Date: 2026-04-23

## Status

Accepted

amends [4. LSP document synchronization via didOpen-didChange-didClose](0004-lsp-document-synchronization-via-didopen-didchange-didclose.md)

## Context

ADR-0004 established internal document synchronization where the daemon manages `didOpen`/`didChange`/`didClose` as an atomic sequence per request. ADR-0008 refined this with mtime-based cache invalidation, keeping files open for session lifetime.

**Gap**: External tools (editors, file watchers, CI pipelines) that modify files cannot notify the LSP server of changes. The current architecture only triggers reanalysis when CLI commands are invoked.

**Use cases**:
1. File watcher detects external edit and wants to trigger LSP reanalysis
2. CI tool modifies files and needs fresh diagnostics without restarting daemon
3. Integration with external editors that don't speak LSP directly

**Constraint**: The LSP client already has internal `didChange` handling for its own lifecycle, but no external API to trigger it.

## Decision

Add a `didChange` CLI subcommand that exposes `textDocument/didChange` notification for externally-triggered reanalysis.

**Interface**:
```
llm-lsp-cli did-change <file>
```

The command reads file content from disk by default. No content options are provided - simplicity over flexibility.

**Behavior**:
1. Daemon checks cache: if file is `None` or `FileState.opened` is `False`, send `didOpen` first
2. **Mtime check for open-before-change**:
   - CLI includes current file mtime in the didOpen request
   - If cached mtime matches the request mtime, skip `didOpen` (daemon already has current version)
   - Only send `didOpen` if mtime differs (file is actually new or stale)
   - This avoids redundant `didOpen` when daemon already synchronized the file
3. Read current file content from disk
4. Send `textDocument/didChange` with full text sync
5. Return acknowledgment (not diagnostics)
6. **No cache mutation** - subsequent requests will detect stale cache via mtime comparison per ADR-0008

The mtime-aware open-before-change is safe because:
- Matching mtime indicates daemon already has identical file content
- Skipped `didOpen` when mtime matches avoids redundant LSP server notification
- Simpler UX: callers don't need to manage document lifecycle or track daemon state

**Routing**: Extend `LspMethodRouter` with notification methods, or add parallel `LspNotificationRouter` for fire-and-forget operations.

**Rejected alternatives**:
- Require explicit open first: Unnecessarily complex; automatic open is harmless and simplifies UX
- Always send didOpen: Wasteful when daemon already has current file version; mtime check optimizes this
- Return diagnostics: Breaks notification pattern; use `diagnostics` command after `didChange`
- Update cache mtime: Unnecessary complexity; mtime-based invalidation (ADR-0008) handles staleness automatically
- Incremental sync: Requires content diff calculation; full sync is simpler and sufficient for CLI use

## Consequences

**Positive:**
- External tools can trigger LSP reanalysis without daemon restart
- Clean separation between notification (didChange) and query (diagnostics) patterns
- Simpler UX: no lifecycle management burden on caller
- Cache coherence via existing mtime-based invalidation (ADR-0008)
- Optimized didOpen: skips redundant notifications when daemon already has current file

**Negative:**
- Additional CLI surface to document and test
- Full sync bandwidth overhead for large files

**Risks:**
| Risk | Mitigation |
|------|------------|
| Version mismatch | LSP server tracks versions; client trusts server state |
| Concurrent changes | File locking not implemented; accept race condition for CLI use case |
| Double-open | Harmless; LSP servers handle redundant opens gracefully |
| Mtime collision | Rare edge case; full sync ensures server state matches disk |

**Related:**
- ADR 004 (LSP document synchronization) - This extends the internal pattern to external API
- ADR 008 (mtime-based cache invalidation) - Stale cache detected automatically on subsequent requests
