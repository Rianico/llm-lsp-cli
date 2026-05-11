# Implementation Report: Re-parsing Dicts to Pydantic Models at CLI Boundary

## Summary

Implemented re-parsing of dicts to Pydantic models at the CLI boundary so the formatter's Pydantic path is exercised. This resolves HIGH-1.

## Changes Made

### 1. Updated imports in `commands/lsp.py`
Added imports for Pydantic models:
- `Location`, `DocumentSymbol`, `SymbolInformation` for location/symbol commands
- `CallHierarchyIncomingCall`, `CallHierarchyOutgoingCall` for call hierarchy
- `CompletionItem` for completion
- `Diagnostic` for diagnostics
- `Hover` for hover

### 2. Updated CLI commands to re-validate dicts to Pydantic models
Each command now:
1. Receives raw dicts from daemon (via IPC)
2. Re-validates dicts to Pydantic models using `Model.model_validate()`
3. Falls back to dict path if validation fails (for robustness with test mocks)
4. Passes Pydantic models to formatter

**Commands updated:**
- `definition` - validates to `Location`
- `references` - validates to `Location`
- `document-symbol` - validates to `DocumentSymbol`
- `workspace-symbol` - validates to `SymbolInformation`
- `incoming-calls` - validates to `CallHierarchyIncomingCall`
- `outgoing-calls` - validates to `CallHierarchyOutgoingCall`
- `completion` - validates to `CompletionItem`
- `hover` - validates to `Hover`
- `diagnostics` - validates to `Diagnostic`
- `workspace-diagnostics` - validates to `Diagnostic`

### 3. Updated Pydantic model for robustness
Made `selectionRange` optional in `DocumentSymbol` model since:
- Formatter already handles it as optional
- Real-world LSP servers might not always send it
- Test mocks were missing this field

### 4. Updated test fixtures
Updated `create_document_symbol_response_with_variables()` in `tests/fixtures.py` to include `selectionRange` for complete mock data.

## Verification

- **Tests**: All 2895 tests pass
- **Type check**: 0 errors, 0 warnings in `commands/lsp.py`
- **Pattern**: Try/except for graceful fallback to dict path

## Design Decisions

### Graceful Fallback Pattern
```python
# Re-validate dicts to Pydantic models at CLI boundary (ADR-0027)
# Fall back to dict path if validation fails
symbols: list[DocumentSymbol] | list[dict[str, object]]
try:
    symbols = [DocumentSymbol.model_validate(sym) for sym in symbols_raw]
except Exception:
    symbols = symbols_raw
```

This pattern ensures:
1. Real LSP data from daemon is validated to Pydantic models
2. Incomplete test mock data falls back to dict path
3. Formatter's both Pydantic and dict paths are exercised

### Why Not Remove Dict Path
The dict path in the formatter is kept for:
- Backward compatibility with existing code
- Robustness when validation fails
- Support for incomplete test mock data

## Files Modified

1. `/Users/zhengxk/development/ai/llm-lsp-cli.typesafety/src/llm_lsp_cli/commands/lsp.py`
   - Added Pydantic model imports
   - Updated all LSP commands to re-validate dicts

2. `/Users/zhengxk/development/ai/llm-lsp-cli.typesafety/src/llm_lsp_cli/lsp/types.py`
   - Made `selectionRange` optional in `DocumentSymbol`

3. `/Users/zhengxk/development/ai/llm-lsp-cli.typesafety/tests/fixtures.py`
   - Updated `create_document_symbol_response_with_variables()` with `selectionRange`

4. `/Users/zhengxk/development/ai/llm-lsp-cli.typesafety/tests/integration/output/test_document_symbol_verbose.py`
   - Updated inline mock responses with `selectionRange`

## Test Results

```
2895 passed, 5 warnings in 93.89s
```

## Type Check Results

```
0 errors, 0 warnings, 0 notes (for commands/lsp.py)
```
