# 7. Logging clarity and elegance refactor

Date: 2026-04-22

## Status

Accepted

## Context

The LSP CLI tool has verbose logging that impacts developer experience when debugging LSP communication:

1. **Transport-level noise**: "Reading body of X bytes" messages appear at DEBUG level, but this is low-level transport plumbing
2. **Missing TRACE granularity**: `LogLevel.TRACE` (level 4) is defined but CLI only exposes `--debug` (level 3)
3. **Cache hit opacity**: When diagnostics return with `kind: "unchanged"`, the code returns cached results but logs nothing about the cache hit

Current architecture:
- `lsp/transport.py`: Transport-level logging at DEBUG
- `cli.py`: `--debug` flag for start/restart commands
- `domain/value_objects/log_level.py`: Defines TRACE level
- `lsp/client.py`: Cache returns handled silently

## Decision

Implement a three-tier logging refactor:

1. **Move transport-level messages to TRACE level**
   - "Reading body of X bytes" changes from `logger.debug()` to `logger.trace()`
   - DEBUG: Protocol-level concerns (LSP messages, method routing)
   - TRACE: Transport plumbing (byte-level I/O, header parsing)

2. **Add `--trace` CLI flag**
   - Add `--trace` flag to `start` and `restart` commands
   - `--debug`: Sets root logger to DEBUG level
   - `--trace`: Sets root logger to DEBUG AND enables TRACE for LSP transport

3. **Add explicit cache hit logging**
   - In `_normalize_document_diagnostics()`, when `result.get("kind") == "unchanged"`, log: `"Cache hit for diagnostics (unchanged), returning cached result for {uri}"`

Rejected alternatives:
- Keep all logging at DEBUG: Too noisy for typical debugging
- Remove transport logging entirely: Loses useful debugging capability
- Use environment variables for log level control: Poor discoverability

## Consequences

**Positive:**
- Clearer log level semantics
- Developers can enable fine-grained tracing when needed
- Cache behavior is observable in logs
- Better separation of concerns in logging

**Negative:**
- Additional CLI flag to maintain
- More complex logging configuration

**Risks:**
- Users may be confused by DEBUG vs TRACE distinction (mitigated by clear documentation)
