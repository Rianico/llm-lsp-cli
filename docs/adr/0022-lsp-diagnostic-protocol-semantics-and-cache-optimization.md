# 22. LSP diagnostic protocol semantics and cache optimization

Date: 2026-05-03

## Status

Accepted

## Context

During debugging sessions, we discovered several subtle but important aspects of LSP 3.17 diagnostic protocol semantics:

### Request vs Notification Semantics

| Type | Has ID | Response | Example |
|------|--------|----------|---------|
| Request | Yes | Yes | `textDocument/diagnostic` |
| Notification | No | No | `textDocument/didChange` |

This distinction affects how we handle communication at different layers of the system.

### previousResultId Optimization

LSP 3.17's pull diagnostics feature includes an optimization where clients can send `previousResultId` to avoid re-transmitting unchanged diagnostics:

- `textDocument/diagnostic`: Uses singular `previousResultId` (string)
- `workspace/diagnostic`: Uses array `previousResultIds`

When diagnostics haven't changed, servers can return:
```json
{"kind": "unchanged", "resultId": "X"}
```

### Version Tracking Distinction

Two independent versioning mechanisms exist:

| Field | Managed By | Purpose |
|-------|------------|---------|
| `document_version` | Client | Tracks content edits (increments on didChange) |
| `last_result_id` / `resultId` | Server | Tracks diagnostic computation state |

These are **orthogonal concerns** and should not be conflated.

## Decision

### Preserve resultId on "unchanged" Responses

When the LSP server returns `{"kind": "unchanged", "resultId": "X"}`, we must preserve the `resultId` for future incremental diagnostic requests.

**Implementation**: Return `(cached_diagnostics, result_id)` not `(cached_diagnostics, None)`.

### Don't Clear last_result_id on didChange

The LSP 3.17 optimization allows servers to return "unchanged" when diagnostics haven't changed (e.g., only comments modified). Clearing `last_result_id` on every `didChange` would:

1. Break the incremental optimization
2. Force full diagnostic recomputation every time
3. Waste bandwidth and server resources

**Correct behavior**: Keep `last_result_id` until server provides a new one.

### workspace/diagnostic previousResultIds Empty is Correct

At daemon startup, we send `workspace/diagnostic` once when cache is empty. `previousResultIds: []` is correct because:

1. There's nothing to compare against yet
2. Per-file optimization happens via `textDocument/diagnostic` which uses singular `previousResultId`
3. The empty array is the proper initial state

## Consequences

**Positive:**
- Correct implementation of LSP 3.17 pull diagnostics optimization
- Reduced bandwidth for comment-only changes
- Server resources saved on unchanged diagnostics
- Clear separation between document version and diagnostic version

**Negative:**
- Developers must understand two-layer version tracking
- Debugging requires awareness of request/notification distinction

**Related:**
- ADR 0005 (Unified workspace diagnostic cache) - Cache foundation
- ADR 0008 (mtime-based cache invalidation) - Ground truth staleness detection
- ADR 0010 (didChange subcommand) - External file change notification
