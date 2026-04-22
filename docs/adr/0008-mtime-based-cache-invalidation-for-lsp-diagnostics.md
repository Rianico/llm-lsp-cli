# 8. mtime-based cache invalidation for LSP diagnostics

Date: 2026-04-22

## Status

Accepted

## Context

The `FileState` dataclass had version management issues:

1. `document_version` (client-managed) and `last_result_id` (server-managed) were independent with no clear relationship
2. `diagnostics_version` duplicated `document_version` logic, creating semantic confusion
3. No reliable mechanism for daemon/cache to determine if cache is stale
4. Current design unnecessarily closed files, adding complexity

Per LSP 3.17 specification:
- **Document Version (Client-Managed)**: Tracks content edits, starts at 1, increments on change, never resets
- **resultId (Server-Managed)**: Server's internal diagnostic version, exposed as string, resets to 0 on file open

The fundamental problem: `document_version` (content tracking) and `last_result_id` (diagnostic version) are orthogonal concerns. The cache cannot determine staleness from these alone because:
- `last_result_id` is server-managed and opaque to client
- `document_version` doesn't indicate whether the file content actually changed

## Decision

We will implement mtime-based cache invalidation using file modification time as the ground truth for staleness detection.

Key changes:
- Add `mtime: float` to `FileState` for ground-truth staleness detection
- Remove `diagnostics_version` field (replaced by mtime comparison)
- Cache is stale iff `incoming_mtime > stored_mtime`
- Files stay open for session lifetime (no didClose per request)

Rejected alternatives:
- Keep `diagnostics_version` with rename: Doesn't address the core issue - document_version and resultId are still independent
- Hash-based content detection: Adds I/O overhead; mtime is sufficient for most cases
- Remove client-side cache entirely: Loses optimization benefits for unchanged files

## Consequences

**Positive:**
- Clear staleness detection: mtime is unambiguous ground truth
- Simpler state management: No confusing diagnostics_version field
- Better LSP optimization: Keep files open, use previousResultId for incremental updates
- No unnecessary didClose: Simpler lifecycle, better performance

**Negative:**
- CLI must stat files: Every request requires filesystem stat() call
- mtime limitations: Can have false positives (touch without content change)
- Race conditions: File changes during request return diagnostics for mtime at request time

**Risks:**
| Risk | Mitigation |
|------|-----------|
| mtime false positives | Acceptable trade-off; content still valid, diagnostics correct |
| Rapid successive writes | Use high-resolution mtime (nanoseconds) |
| CLI stat() overhead | Minimal; stat() is fast syscall |

**Related:**
- ADR 004 (LSP document synchronization) - Originally used didClose per request
- ADR 005 (Unified workspace diagnostic cache) - Provides the cache foundation
