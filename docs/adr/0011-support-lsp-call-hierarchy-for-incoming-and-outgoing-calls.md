# 11. Support LSP call hierarchy for incoming and outgoing calls

Date: 2026-04-24

## Status

Accepted

## Context

The CLI currently supports position-based navigation commands (`definition`, `references`, `hover`, `completion`) but lacks support for call hierarchy queries. LSP 3.17 defines three call hierarchy methods:

1. `textDocument/prepareCallHierarchy` - Prepare call hierarchy items at a position
2. `callHierarchy/incomingCalls` - Find callers of a function/method
3. `callHierarchy/outgoingCalls` - Find functions/methods called by a function

This feature is essential for LLM-assisted code understanding, enabling queries like "who calls this function?" and "what does this function call?" without requiring the LLM to read and analyze the entire codebase.

The existing architecture follows a clean layering pattern:
- CLI layer (Typer commands) -> Application layer (DaemonClient) -> Infrastructure layer (LSPClient, Transport)
- LSP methods are defined in `constants.py`, types in `types.py`, client methods in `client.py`
- CLI commands follow a consistent pattern: position arguments (file, line, column), workspace/language options, output format options

## Decision

We will add two separate CLI commands: `incoming-calls` and `outgoing-calls`, following the established pattern for position-based commands.

**Implementation approach:**

1. **Constants**: Add `CALL_HIERARCHY_INCOMING_CALLS` and `CALL_HIERARCHY_OUTGOING_CALLS` to `LSPConstants` (note: `PREPARE_CALL_HIERARCHY` already exists)

2. **Types**: Add LSP type definitions:
   - `CallHierarchyItem` - Result of prepareCallHierarchy
   - `CallHierarchyIncomingCall` - Caller with from ranges
   - `CallHierarchyOutgoingCall` - Callee with from ranges

3. **LSPClient**: Add two new async methods:
   - `request_call_hierarchy_incoming(file_path, line, column)`
   - `request_call_hierarchy_outgoing(file_path, line, column)`
   - Both internally call `prepareCallHierarchy` first, then the respective follow-up method

4. **CLI**: Add two commands mirroring `definition` and `references` pattern:
   - `incoming-calls <file> <line> <column>` with standard workspace/language/format options
   - `outgoing-calls <file> <line> <column>` with standard workspace/language/format options

5. **Output**: Follow `references` command pattern - support `--raw` for legacy format, default to `CompactFormatter` for LLM-optimized output

**Rejected alternatives:**

- **Single `call-hierarchy` command with `--incoming/-i` and `--outgoing/-o` options**: Adds complexity for a use case where both are rarely needed together. Position-based queries typically want one direction at a time.
- **Mutually exclusive options validation**: More complex argument parsing without clear benefit.
- **Combined results from both directions**: Call hierarchy results are structurally different and semantically distinct; combining them would confuse LLM consumers.

## Consequences

**Positive:**
- LLMs can discover caller/callee relationships without reading entire codebase
- Consistent CLI UX with existing position-based commands
- Clean separation follows dependency rule (CLI depends on application, application on infrastructure)
- Testability through existing `DaemonClient` mock patterns

**Negative:**
- Two additional commands increase CLI surface area
- Requires LSP server support (pyright/pylance support this; some servers do not)
- Call hierarchy results can be large for functions with many callers/callees

**Risks:**
- **LSP server compatibility**: Not all LSP servers implement call hierarchy. The implementation should gracefully handle `MethodNotFound` errors.
- **Performance**: Deep call hierarchies may return large result sets. The `CompactFormatter` pattern already handles this through relative paths and compact ranges.
- **Position accuracy**: Call hierarchy requires the cursor to be on a callable symbol. User education may be needed if results are unexpectedly empty.
