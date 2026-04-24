# 16. Load LSP client capabilities from server-specific JSON files

Date: 2026-04-25

## Status

Accepted

## Context

The current implementation hardcodes LSP client capabilities in `_get_standard_capabilities()`, making the CLI inflexible when connecting to different language servers with varying capability requirements. Server-specific JSON capability files already exist in the repository but are unused. The initialization flow needs:

- Server-specific capability negotiation (basedpyright, rust-analyzer, etc.)
- Clear fallback when no specific match exists
- Static configuration that does not change at runtime
- Clear separation between static configuration (JSON) and dynamic runtime values (processId, rootUri)

## Decision

We will load LSP client capabilities from server-specific JSON files at initialization time, falling back to `default.json` when no match exists. The JSON structure separates static `capabilities` from optional `initializationOptions`. Dynamic fields (`processId`, `rootUri`, `workspaceFolders`, `clientInfo`) are injected at runtime by the calling code.

Server matching extracts the basename from the server command path and uses the existing `_match_server_filter()` logic. Capabilities are cached in memory for the process lifetime. The system fails fast if `default.json` is missing or invalid.

When no server-specific JSON match is found, the system logs a warning indicating that `default.json` is being used. This provides observability for server support gaps without failing the initialization.

- Rejected: Merge capabilities with defaults
  - Pros: Richer capability sets automatically
  - Cons: Complex mental model, unpredictable capability intersection
  - Why not: Explicit file content is clearer than implicit merging rules

- Rejected: Load capabilities on every initialization without caching
  - Pros: Simpler implementation, no cache invalidation concerns
  - Cons: Unnecessary I/O for static configuration
  - Why not: Capabilities are immutable per process; caching is safe and cheap

- Rejected: Silent fallback to minimal hardcoded capabilities if default.json missing
  - Pros: CLI remains functional without configuration files
  - Cons: Hidden failures, inconsistent behavior across installations
  - Why not: Fail fast surfaces configuration issues immediately

- Rejected: Keep `_get_standard_capabilities()` as hardcoded baseline
  - Pros: No file dependencies, always works
  - Cons: Cannot adapt to different servers, violates open/closed principle
  - Why not: JSON-based configuration enables server-specific tuning without code changes

- Rejected: Silent fallback without logging
  - Pros: Cleaner logs, no noise for expected fallbacks
  - Cons: Undetected server support gaps, harder to diagnose capability mismatches
  - Why not: Warning logs provide actionable feedback for adding server-specific support

## Consequences

Easier:
- Adding support for new LSP servers without code changes (add JSON file)
- Tuning capabilities per server based on actual server behavior
- Testing with different capability configurations
- Identifying unsupported servers via warning logs

Harder:
- Deployment must include JSON files alongside the CLI
- Users cannot override capabilities at runtime
- Server name extraction from path must remain stable

Risks:
- Missing or corrupted `default.json` causes immediate failure (mitigated by packaging validation)
- Server command path variations may fail to match expected JSON filenames
- Caching prevents hot-reloading of capability files without process restart

Interfaces:
- `get_capabilities_for_server_path(server_path: str) -> dict[str, Any]` in `config/capabilities/`
- Returns: `{"capabilities": {...}, "initializationOptions": {...}}`
- Raises: `FileNotFoundError` if default.json missing; `json.JSONDecodeError` if invalid
- Logs: Warning when falling back to default.json for unrecognized server
