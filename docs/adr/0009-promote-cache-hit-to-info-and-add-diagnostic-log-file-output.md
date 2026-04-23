# 9. Promote cache HIT to INFO and add diagnostic log file output

Date: 2026-04-23

## Status

Accepted

Amends [7. Logging clarity and elegance refactor](0007-logging-clarity-and-elegance-refactor.md)

Extends [6. Diagnostic log masking to prevent log bloat](0006-diagnostic-log-masking-to-prevent-log-bloat.md)

## Context

Two observability gaps in the current logging architecture:

1. **Cache hit invisibility**: The `textDocument/diagnostic` cache HIT messages are logged at DEBUG level, making them invisible during normal operation. Users cannot verify that the mtime-based cache invalidation (ADR-0008) is working without enabling verbose debug logging.

2. **Masked diagnostic data**: Per ADR-0006, diagnostic arrays are masked in daemon.log to prevent bloat. When debugging LSP server issues, developers need full diagnostic content but enabling TRACE exposes too much noise.

Forces:
- Cache behavior should be observable at default log levels
- Full diagnostic content is useful for debugging but too verbose for daemon.log
- Opt-in mechanisms avoid noise for normal users
- File-based diagnostic log allows post-hoc analysis

## Decision

Implement a two-part logging enhancement:

1. **Promote cache HIT to INFO level**
   - Change `_log_cache_hit()` and `_log_cache_hit_server()` in `client.py` from `logger.debug()` to `logger.info()`
   - Cache HIT messages now visible at default INFO level
   - Format remains structured: `[cache HIT] {rel_path} | resultId=... | mtime=... | v=... | open=... | diags=N`

2. **Add `--diagnostic-log` CLI option for separate file output**
   - Add `--diagnostic-log` boolean flag to `start` and `restart` commands
   - When enabled, configure `llm_lsp_cli.lsp.diagnostic` logger with a FileHandler writing to `diagnostics.log`
   - The diagnostic logger receives full (unmasked) LSP messages for `LogCategory.SKIP` and `LogCategory.MASK` categories
   - Logger has `propagate=False` to prevent duplicate logging to daemon.log
   - Default: disabled (no diagnostics.log created)

Rejected alternatives:
- Log full diagnostics to daemon.log: Rejected by ADR-0006 (log bloat)
- Environment variable for diagnostic log: Poor discoverability compared to CLI flag
- Separate `--verbose` level for cache hits: Overcomplicates log level semantics

## Consequences

**Positive:**
- Cache behavior observable at default log level
- Developers can opt into full diagnostic logging without TRACE noise
- diagnostics.log is separate from daemon.log, easy to inspect or delete
- No performance impact when --diagnostic-log is disabled (logger has no handlers)

**Negative:**
- Additional CLI flag to document
- diagnostics.log grows unboundedly when enabled (mitigated by opt-in)
- Cache HIT messages add volume to daemon.log at INFO level

**Risks:**
- Users may leave --diagnostic-log enabled and forget about diagnostics.log growth (mitigated by opt-in, documented cleanup)
