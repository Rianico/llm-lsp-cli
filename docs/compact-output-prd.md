# PRD: LLM-Optimized Compact Output Format

**Date:** 2026-04-12  
**Status:** Proposed  
**Author:** Team

---

## 1. Overview

Transform `llm-lsp-cli` output from human-readable verbose format to **LLM-optimized compact format**. The CLI serves LLM consumers (via RTK token optimization), so output should prioritize:
- Token efficiency
- Structured consistency
- Information density

---

## 2. Goals

### 2.1 Primary Goals
1. **Reduce token count** in output by 40-60% without losing information
2. **File-centric grouping** — symbols grouped by source file
3. **Flat JSON structure** — array with `file` field, not nested objects
4. **Compact CSV headers** — `file,name,kind,range,detail,container,tags`

### 2.2 Non-Goals
- Backward compatibility with existing output format (breaking change accepted)
- Human-readable verbose output as default (use `--raw` for legacy format)
- Kind sub-grouping under files (adds complexity without token savings)

---

## 3. Commands Affected

| Command | Current Behavior | New Default Behavior |
|---------|------------------|----------------------|
| `workspace_symbol` | Flat list, one symbol per line | Grouped by file |
| `document_symbol` | Flat list, single file | Hierarchical (respects nesting) |
| `references` | Flat list of locations | Grouped by file |

---

## 4. Output Format Specifications

### 4.1 Text Format

**Before (current):**
```
MyClass (Class) in file:///project/utils.py [1:1-50:1]
my_function (Function) in file:///project/utils.py [55:1-80:1]
CONSTANT (Constant) in file:///project/utils.py [85:1-85:10]
AnotherClass (Class) in file:///project/models.py [1:1-100:1]
```

**After (compact default):**
```
utils.py:
  MyClass (5) [1:1-50:1]
  my_function (12) [55:1-80:1]
  CONSTANT (14) [85:1-85:10]

models.py:
  AnotherClass (5) [1:1-100:1]
```

**Changes:**
- Relative paths (strip `file://` prefix and workspace root)
- Numeric kind only (LLMs know the mapping: 5=Class, 12=Function, etc.)
- File headers with indented symbols
- No trailing whitespace

**With detail/container/tags:**
```
utils.py:
  MyClass (5) [1:1-50:1]
  my_function (12) [55:1-80:1] -> None
  deprecated_func (12) [100:1-120:1] -> str [deprecated]

models.py:
  AnotherClass (5) [1:1-100:1]
    InnerClass (5) [50:1-80:1] (container: AnotherClass)
```

### 4.2 JSON Format

**Before (current):**
```json
{
  "symbols": [
    {
      "name": "MyClass",
      "kind": 5,
      "kind_name": "Class",
      "location": {
        "uri": "file:///project/utils.py",
        "range": {
          "start": {"line": 0, "character": 0},
          "end": {"line": 49, "character": 0}
        }
      }
    }
  ]
}
```

**After (compact default - flat array):**
```json
[
  {
    "file": "utils.py",
    "name": "MyClass",
    "kind": 5,
    "range": "1:1-50:1"
  },
  {
    "file": "utils.py",
    "name": "my_function",
    "kind": 12,
    "range": "55:1-80:1",
    "detail": "-> None"
  }
]
```

**Design Rationale:**
- Flat array chosen over nested `{files: {...}}` structure
- LLMs handle flat arrays better (single iteration pattern)
- Consistent with CSV format (inherently flat)
- Standard REST API convention (LLMs trained on this pattern)
- ~12% token overhead for file field repetition is acceptable

**Changes:**
- Flat array (not nested under `symbols` key)
- `file` field instead of nested `location.uri`
- `range` as compact string `"start_line:start_char-end_line:end_char"`
- Omit `kind_name` (redundant — LLMs know the mapping)
- Omit `null` fields entirely (not `"detail": null`)
- Relative paths

### 4.3 YAML Format

Same structure as JSON, YAML-native:
```yaml
- file: utils.py
  name: MyClass
  kind: 5
  range: "1:1-50:1"

- file: utils.py
  name: my_function
  kind: 12
  range: "55:1-80:1"
  detail: "-> None"
```

### 4.4 CSV Format

**Before (current):**
```
name,kind,kind_name,uri,start_line,start_char,end_line,end_char
MyClass,5,Class,file:///project/utils.py,0,0,49,0
```

**After (compact default):**
```
file,name,kind,range,detail,container,tags
utils.py,MyClass,5,1:1-50:1,,,
utils.py,my_function,12,55:1-80:1,-> None,,
utils.py,old_func,12,100:1-120:1,-> str,deprecated,
```

**Changes:**
- Compact headers (8 columns → 7 columns)
- `range` as single column: `start_line:start_char-end_line:end_char`
- Relative paths in `file` column
- Empty fields for null values (not literal `null`)
- Tags comma-separated if multiple: `deprecated,experimental`

---

## 5. Field Specifications

### 5.1 Core Fields (Always Present)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `file` | string | Relative path from workspace root | `utils.py`, `src/models.py` |
| `name` | string | Symbol name | `MyClass`, `my_function` |
| `kind` | integer | LSP SymbolKind number (1-26) | `5` (Class), `12` (Function) |
| `range` | string | `start_line:start_char-end_line:end_char` (1-based) | `1:1-50:1` |

### 5.2 Optional Fields (Omit if Empty/Null)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `detail` | string | Type signature, return type | `-> None`, `(x: int) -> str` |
| `container` | string | Parent class/module name | `MyClass`, `utils` |
| `tags` | array | Symbol tags | `["deprecated"]`, `[1]` (tag ID) |

### 5.3 Field Omission Rules

```python
# Include field only if value is truthy
if detail:
    record["detail"] = detail
if container:
    record["container"] = container
if tags:
    record["tags"] = tags
```

**JSON output:**
```json
{"file": "utils.py", "name": "MyClass", "kind": 5, "range": "1:1-50:1"}
// No "detail": null, no "container": null, no "tags": []
```

---

## 6. Token Efficiency Analysis

### 6.1 Example: 10 Symbols in 2 Files

**Current format (JSON):**
```json
{
  "symbols": [
    {"name": "ClassA", "kind": 5, "kind_name": "Class", "location": {"uri": "file:///project/utils.py", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 49, "character": 0}}}},
    ... (10 symbols)
  ]
}
```
Estimated tokens: ~800

**New compact format:**
```json
[
  {"file": "utils.py", "name": "ClassA", "kind": 5, "range": "1:1-50:1"},
  ... (10 symbols)
]
```
Estimated tokens: ~350

**Savings: ~56%**

### 6.2 Text Format Comparison

**Current:**
```
ClassA (Class) in file:///project/utils.py [1:1-50:1]
funcA (Function) in file:///project/utils.py [55:1-80:1]
...
```
~50 chars per symbol × 10 = 500 chars

**New:**
```
utils.py:
  ClassA (5) [1:1-50:1]
  funcA (12) [55:1-80:1]
```
~25 chars per symbol + file header = ~280 chars

**Savings: ~44%**

---

## 7. Implementation Details

### 7.1 Path Normalization

```python
def normalize_path(uri: str, workspace: str) -> str:
    """Convert file:// URI to relative path."""
    # Strip file:// prefix
    path = uri.replace("file://", "")
    # Make relative to workspace
    workspace_path = Path(workspace).resolve()
    path_obj = Path(path).resolve()
    try:
        return str(path_obj.relative_to(workspace_path))
    except ValueError:
        # Path outside workspace, return absolute
        return str(path_obj)
```

### 7.2 Range Formatting

```python
def format_range(range_obj: dict) -> str:
    """Format LSP range to compact string (1-based)."""
    start = range_obj.get("start", {})
    end = range_obj.get("end", {})
    start_line = start.get("line", 0) + 1  # Convert 0-based to 1-based
    start_char = start.get("character", 0) + 1
    end_line = end.get("line", 0) + 1
    end_char = end.get("character", 0) + 1
    return f"{start_line}:{start_char}-{end_line}:{end_char}"
```

### 7.3 File Grouping Logic

```python
from collections import defaultdict
from typing import Any

def group_symbols_by_file(symbols: list[dict[str, Any]], workspace: str) -> dict[str, list[dict]]:
    """Group symbols by normalized file path."""
    grouped = defaultdict(list)
    for sym in symbols:
        location = sym.get("location", {})
        uri = location.get("uri", "")
        file_path = normalize_path(uri, workspace)
        
        # Build compact symbol record
        record: dict[str, Any] = {
            "file": file_path,
            "name": sym.get("name", ""),
            "kind": sym.get("kind", 0),
            "range": format_range(location.get("range", {})),
        }
        
        # Add optional fields only if present
        if sym.get("detail"):
            record["detail"] = sym["detail"]
        if sym.get("containerName"):
            record["container"] = sym["containerName"]
        if sym.get("tags"):
            record["tags"] = sym["tags"]
        
        grouped[file_path].append(record)
    
    return dict(grouped)
```

### 7.4 Text Formatter

```python
def format_workspace_symbols_compact(grouped_symbols: dict[str, list[dict]]) -> str:
    """Format grouped symbols as compact text."""
    lines = []
    
    for file_path, symbols in grouped_symbols.items():
        lines.append(f"{file_path}:")
        for sym in symbols:
            indent = "  "
            # Handle nested symbols (indent by container depth)
            if sym.get("container"):
                indent = "    "
            
            line = f"{indent}{sym['name']} ({sym['kind']}) [{sym['range']}]"
            
            # Add detail if present
            if sym.get("detail"):
                line += f" {sym['detail']}"
            
            # Add tags if present
            if sym.get("tags"):
                tag_str = ", ".join(sym["tags"])
                line += f" [{tag_str}]"
            
            lines.append(line)
        
        # Add blank line between files
        lines.append("")
    
    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()
    
    return "\n".join(lines)
```

---

## 8. `--raw` Flag (Legacy Mode)

For backward compatibility with existing tooling:

```python
@app.command()
def workspace_symbol(
    # ... existing params ...
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Output in legacy verbose format (one symbol per line, full columns)",
    ),
) -> None:
    if raw:
        # Use legacy formatter
        _execute_lsp_command(..., text_formatter=_format_workspace_symbols_text, ...)
    else:
        # Use new compact formatter
        _execute_lsp_command(..., text_formatter=_format_workspace_symbols_compact, ...)
```

---

## 9. Migration Guide

### For Scripts Parsing Current Output

**If parsing text output:**
```bash
# Old: grep for symbol names in flat output
llm-lsp-cli workspace_symbol MyClass

# New: parse file-grouped output, or use --raw
llm-lsp-cli workspace_symbol MyClass --raw
```

**If parsing JSON:**
```python
# Old: access response["symbols"]
for sym in response["symbols"]:
    uri = sym["location"]["uri"]

# New: flat array, use file field
for sym in response:
    file_path = sym["file"]
```

**If parsing CSV:**
```python
# Old: expect start_line, start_char columns
# New: parse range column
import re

def parse_range(range_str: str) -> dict:
    match = re.match(r"(\d+):(\d+)-(\d+):(\d+)", range_str)
    if match:
        return {
            "start_line": int(match.group(1)),
            "start_char": int(match.group(2)),
            "end_line": int(match.group(3)),
            "end_char": int(match.group(4)),
        }
```

---

## 10. Testing Requirements

### 10.1 Unit Tests

- [ ] `normalize_path()` — URI to relative path conversion
- [ ] `format_range()` — LSP range to compact string
- [ ] `group_symbols_by_file()` — grouping logic
- [ ] `format_workspace_symbols_compact()` — text output
- [ ] CSV formatter with new headers
- [ ] JSON formatter omits null fields

### 10.2 Integration Tests

- [ ] `workspace_symbol` — text output grouped by file
- [ ] `workspace_symbol --format json` — flat array structure
- [ ] `workspace_symbol --format csv` — compact headers
- [ ] `workspace_symbol --raw` — legacy format preserved
- [ ] `document_symbol` — hierarchical output
- [ ] `references` — locations grouped by file

### 10.3 Edge Cases

- [ ] Empty result set (no symbols found)
- [ ] Single symbol (no grouping benefit)
- [ ] Symbols outside workspace boundary
- [ ] Nested symbols (container handling)
- [ ] Special characters in file paths
- [ ] Windows path separators

---

## 11. Documentation Updates

### 11.1 README.md

Update example output snippets to show compact format.

### 11.2 CLI Help Text

```
--raw    Output in legacy verbose format (one symbol per line, full columns)
```

### 11.3 New Documentation File

Create `docs/output-formats.md` with:
- Compact format specification
- Migration guide
- Token efficiency examples
- LLM prompt examples using compact output

---

## 12. Rollout Plan

### Phase 1: Implementation
- [ ] Add compact formatters
- [ ] Add `--raw` flag
- [ ] Update tests

### Phase 2: Documentation
- [ ] Update README examples
- [ ] Write migration guide
- [ ] Document token savings

### Phase 3: Release
- [ ] Bump minor version (breaking change)
- [ ] Release notes highlight format change
- [ ] Monitor for user feedback

---

## 13. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Token reduction (JSON) | 40-60% | Compare old vs new output token count |
| Token reduction (text) | 30-50% | Line count comparison |
| User satisfaction | >80% positive | GitHub issues/feedback |
| Backward compat issues | <5 reports | `--raw` flag usage |

---

## 14. Appendix: LSP SymbolKind Reference

| ID | Name | ID | Name |
|----|------|----|------|
| 1 | File | 14 | Constant |
| 2 | Module | 15 | String |
| 3 | Namespace | 16 | Number |
| 4 | Package | 17 | Boolean |
| 5 | Class | 18 | Array |
| 6 | Method | 19 | Object |
| 7 | Property | 20 | Key |
| 8 | Field | 21 | Null |
| 9 | Constructor | 22 | EnumMember |
| 10 | Enum | 23 | Struct |
| 11 | Interface | 24 | Event |
| 12 | Function | 25 | Operator |
| 13 | Variable | 26 | TypeParameter |

LLMs have this mapping in training data — no need to emit `kind_name`.
