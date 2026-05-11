# 29. Split diagnostic cache into document and workspace channels

Date: 2026-05-12

## Status

Accepted

Supercedes [5. Unified workspace diagnostic cache with streaming](0005-unified-workspace-diagnostic-cache-with-streaming.md)

## Context

ADR-0005 established a "Single cache: Unified cache for both push and pull modes" where `FileState.diagnostics` was a single field written by two independent LSP notification sources:

1. `textDocument/publishDiagnostics` -- per-file, pushed when file content changes
2. `workspace/diagnostic` via `$/progress` -- workspace-wide, incremental batches

This caused a stale data bug: after fixing a diagnostic and sending `didChange`, the server pushes updated `publishDiagnostics` (clearing the diagnostic for that file), but the previous workspace diagnostic batch still occupies the same field. The `workspace-diagnostics` command returns stale data because the fresh document-level write has overwritten the workspace-level data, or vice versa.

The LSP protocol treats these as independent channels with different lifecycles and freshness guarantees. Document diagnostics update in real time per file; workspace diagnostics update in batches on the server's schedule. Writing both to a single field means later writes from one source silently overwrite earlier writes from the other.

## Decision

Split `FileState.diagnostics` into two independent fields aligned with the LSP protocol's two diagnostic channels:

- `document_diagnostics`: Updated by `textDocument/publishDiagnostics` and `textDocument/diagnostic`. Read by the `diagnostics` command.
- `workspace_diagnostics`: Updated by `workspace/diagnostic` via `$/progress`. Read by the `workspace-diagnostics` command.
- `has_workspace_diagnostics` flag: Distinguishes "workspace diagnostics never written" from "workspace diagnostics explicitly written as empty list."

Backward compatibility: `get_diagnostics()` and `get_cached()` return `document_diagnostics`, preserving existing caller behavior.

Rejected alternatives:
- Single field with source tagging: Requires consumers to filter by source on every read, adds branching complexity, and still risks one source overwriting the other during concurrent notification processing.
- Separate cache objects per channel: Duplicates FileState metadata (mtime, version, is_open) across two caches, requiring synchronization and risking divergence.
- Clear workspace diagnostics on publishDiagnostics: Violates LSP protocol semantics; workspace diagnostics represent the server's workspace-wide analysis, which is independent of per-file publish events.

## Consequences

**Positive:**
- Stale data bug eliminated; each channel reads from its own field
- Cache structure aligns with LSP protocol semantics
- Each channel maintains independent freshness guarantees
- Minimal API surface change; backward-compatible defaults preserved

**Negative:**
- Slightly increased memory per FileState (two lists instead of one)
- More fields to reason about in FileState dataclass
- Consumers must understand which channel to read from

**Risks:**
- Future LSP methods that merge the two channels would require another re-evaluation
- The `has_workspace_diagnostics` flag must be set correctly; missing it would cause `get_all_workspace_diagnostics()` to skip files

**Related:**
- ADR 0008 (mtime-based cache invalidation) -- Staleness detection applies to both channels
- ADR 0022 (LSP diagnostic protocol semantics) -- Documents the request/notification distinction and previousResultId optimization
