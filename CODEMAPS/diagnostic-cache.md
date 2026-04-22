# Diagnostic Cache Architecture

<!-- Generated: 2026-04-23 | Files scanned: 5 -->

## Overview

The diagnostic cache implements ADR-001 mtime-based invalidation for LSP diagnostic responses.

## FileState Dataclass

Location: `src/llm_lsp_cli/lsp/cache.py`

```python
@dataclass
class FileState:
    mtime: float = 0.0              # File modification time (ground truth)
    document_version: int = 0       # LSP document version
    last_result_id: str | None      # Server's diagnostic version
    is_open: bool = False           # Whether didOpen was sent
    diagnostics: list[dict]         # Cached diagnostic items
    uri: str = ""                   # Original file URI
```

## DiagnosticCache Class

Key methods:
- `is_stale(uri, incoming_mtime) -> bool` - Returns `incoming_mtime > stored_mtime`
- `on_did_open(uri, mtime)` - Sets `is_open=True`, increments version
- `update_diagnostics(uri, diagnostics, result_id)` - Stores after LSP response
- `get_diagnostics(uri) -> list[dict]` - Returns cached or empty list

## Cache Invalidation Flow

```
CLI Request: get_diagnostics(file_path)
              |
              v
        stat(file_path).st_mtime
              |
              v
    daemon.py: mtime > state.mtime?
              |
         +----+----+
         |         |
        YES        NO
         |         |
         v         v
   Refresh Cache   Return cached
         |
         v
   1. state.mtime = mtime
   2. state.document_version += 1
   3. send didChange (if content changed)
   4. send textDocument/diagnostic(previousResultId)
   5. state.diagnostics = response.items
   6. state.last_result_id = response.resultId
```

## Integration Points

### LSPClient (`lsp/client.py`)

```python
async def request_diagnostics(self, file_path, uri, mtime):
    state = await self._diagnostic_cache.get_file_state(uri)

    # Cache hit: mtime unchanged and have resultId
    if state.last_result_id and mtime and not await cache.is_stale(uri, mtime):
        return state.diagnostics

    # Cache miss: request from server
    result = await transport.send_request("textDocument/diagnostic", {
        "textDocument": {"uri": uri},
        "previousResultId": state.last_result_id,
    })

    # Update cache
    await cache.update_diagnostics(uri, result["items"], result["resultId"])
    await cache.set_mtime(uri, mtime)
    return result["items"]
```

### Daemon (`daemon.py`)

```python
# In _send_lsp_request():
mtime = os.stat(file_path).st_mtime
result = await client.request_diagnostics(file_path, uri, mtime)
```

## Key Invariants

1. **mtime is ground truth** - Staleness determined solely by mtime comparison
2. **Monotonic document_version** - Never decrements, increments on didChange
3. **No didClose** - Files remain open for session (per ADR-001)
4. **previousResultId optimization** - Server can return "unchanged" if nothing changed

## Error Handling

- `stat()` failure: Proceed with `mtime=None`, forcing server query
- `textDocument/diagnostic` failure: Return cached diagnostics (may be stale)
- "unchanged" response: Return cached diagnostics from cache

## Testing

Key test files:
- `tests/unit/lsp/test_cache_hit_logging.py` - Cache hit logging
- `tests/unit/lsp/test_diagnostic_cache_skip.py` - Cache skip scenarios
- `tests/unit/lsp/test_resultid_lifecycle.py` - resultId handling
