# 5. Unified workspace diagnostic cache with streaming

Date: 2026-04-20

## Status

Accepted

## Context

The LSPClient implementation distinguishes between pull mode and push mode for workspace diagnostics:

**Current Architecture (Pre-ADR 005):**

| Mode | Mechanism | Handler |
|------|-----------|---------|
| **Pull mode** | `workspace/diagnostic` request with `partialResultToken`, results via `$/progress` | `WorkspaceDiagnosticManager` |
| **Push mode** | `textDocument/publishDiagnostics` notifications | `LSPClient._handle_diagnostics()` |

**Current Problems:**
- **Redundant abstraction**: `WorkspaceDiagnosticManager` only delegates to `DiagnosticCache`
- **Pull/push mode branching**: `request_workspace_diagnostics()` has conditional logic based on `_pull_mode_supported`
- **Duplicate progress handling**: Both `LSPClient._handle_progress()` and `WorkspaceDiagnosticManager._handle_progress()` exist
- **Circular dependency**: `WorkspaceDiagnosticManager` holds reference to `LSPClient`
- **No deduplication**: Same logical file with different URI representations creates separate entries

## Decision

Unify workspace diagnostic handling into a single `DiagnosticCache` class that manages both push and pull mode diagnostics with relative path keys.

Key design decisions:
1. **Single cache**: Unified cache for both push (`publishDiagnostics`) and pull (`workspace/diagnostic`) modes
2. **Relative path keys**: Cache keys are project-relative paths (`src/module/file.py`), not URIs
3. **Version tracking**: Cache values include `FileState` with `document_version`, `last_result_id`, `diagnostics`, `is_open`
4. **Streaming support**: Handle `$/progress` notifications for workspace diagnostic streaming
5. **Eliminate WorkspaceDiagnosticManager**: Fold functionality into `DiagnosticCache`

Rejected alternatives:
- Keep separate caches: Duplicates state, requires synchronization
- URI-based keys: Inefficient when same file referenced differently
- No version tracking: Cannot detect stale diagnostics

## Consequences

**Positive:**
- Simpler architecture with single cache responsibility
- No circular dependencies
- Consistent deduplication via relative path keys
- Proper version tracking for stale detection
- Reduced memory usage (no duplicate entries)

**Negative:**
- Breaking change to cache API
- Requires migration of existing cache state
- More complex path resolution logic

**Risks:**
- Path resolution must handle edge cases (symlinks, case sensitivity)
- Thread safety requirements for async operations
- Backward compatibility for existing clients
