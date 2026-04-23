# 6. Diagnostic log masking to prevent log bloat

Date: 2026-04-21

## Status

Accepted

Extended by [9. Promote cache HIT to INFO and add diagnostic log file output](0009-promote-cache-hit-to-info-and-add-diagnostic-log-file-output.md)

## Context

The `daemon.log` file grows unboundedly when LSP servers emit verbose diagnostic data. Workspace diagnostics from LSP servers (like basedpyright) can contain thousands of diagnostic entries across all project files. A single `$/progress` notification can exceed 100KB of JSON.

Current behavior:
- `transport.py` logs all incoming LSP messages when `trace=True`
- Diagnostic arrays in `$/progress`, `textDocument/publishDiagnostics`, and diagnostic responses are logged in full
- Log file location: `.llm-lsp-cli/daemon.log`

Forces:
- Developers need diagnostic visibility for debugging
- Full diagnostic content makes finding actual bugs harder
- Log files should remain readable and searchable
- Solution must not mutate data flowing through transport layer

## Decision

Implement centralized diagnostic masking at the transport layer in `StdioTransport._handle_message()`, applied only when `trace=True`.

Implementation:
1. Add `_mask_diagnostics(data)` helper to `transport.py`
2. Apply masking before `logger.debug()` calls in `_handle_message()`
3. Mask diagnostic arrays in:
   - `$/progress` notifications: `params.value.items[].diagnostics`
   - `textDocument/publishDiagnostics`: `params.diagnostics`
   - Diagnostic responses: `result.items[]`
4. Replace arrays with length metadata: `"... (array_len: N)"`
5. Use `copy.deepcopy()` to avoid mutating incoming data

Rejected alternatives:
- Mask at the logger configuration level: Too blunt, would mask non-diagnostic arrays
- Disable diagnostic logging entirely: Loses useful debugging information
- Mask at CLI level: Too late, daemon.log already bloated

## Consequences

**Positive:**
- Log files remain readable and searchable
- Diagnostic count still visible for debugging
- No mutation of actual data
- Applies consistently to all diagnostic sources

**Negative:**
- Full diagnostic details not available in logs (must use debugger or raw mode)
- Deep copy adds slight overhead

**Risks:**
- Masking may hide useful diagnostic details during debugging (mitigated by having raw mode option)
