---
complexity: lightweight
date: 2026-05-13
status: approved
---

# Python 3.14 Upgrade Design

## Summary

Pin project to Python 3.14 and enable full PEP compliance linting across ruff, mypy, and basedpyright.

## Understanding

| Item | Details |
|------|---------|
| **What** | Pin Python to 3.14, configure tools for 3.14, enable PEP compliance |
| **Why** | Modernize project, enforce stricter code quality |
| **Who** | Developers, CI/CD pipelines |
| **Constraints** | Breaking change (drops 3.10-3.13), consistent tool config |
| **Non-goals** | Updating source code for 3.14 syntax, adding unrelated deps |

## Assumptions

1. Python 3.14 available in target environments
2. uv supports Python 3.14
3. Current code is 3.14-compatible
4. No `.python-version` file needed — uv handles version via `pyproject.toml`

## Design

### Files to Modify

#### 1. `pyproject.toml`

```toml
[project]
requires-python = "==3.14.*"
classifiers = [
  # Remove 3.10-3.12, add 3.14
  "Programming Language :: Python :: 3.14",
]

[tool.ruff]
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "D"]

[tool.ruff.lint.pydocstyle]
convention = "pep257"

[tool.mypy]
python_version = "3.14"
```

#### 2. `pyrightconfig.json`

```json
{
  "typeCheckingMode": "recommended",
  "pythonVersion": "3.14",
  "extraPaths": ["./typings"]
}
```

### Ruff Rules Added

| Rule | PEP | What It Checks |
|------|-----|----------------|
| `D` | PEP 257 | Docstring conventions |
| `N` | PEP 8 | Naming conventions |

**Skipped:** `ANN` (redundant with mypy strict)

### Suppresssions Removed

All project-level suppresssions removed from `pyrightconfig.json`:
- `reportMissingTypeStubs`
- `reportCallInDefaultInitializer`
- `reportImplicitStringConcatenation`

## Decision Log

| Decision | Alternatives | Why Chosen |
|----------|-------------|------------|
| `==3.14.*` version | `>=3.14`, `==3.14` | Allows patches, blocks major |
| No `.python-version` | Add file | uv handles via pyproject.toml |
| Skip `ANN` rules | Enable | Redundant with mypy strict |
| Remove suppressions | Keep | Scoped Over Global principle |

## Validation

### Example 1: CI Lint Check

```bash
uv run ruff check src/    # Uses py314, D + N rules active
uv run mypy src/           # Uses python_version = "3.14"
uv run basedpyright src/   # Uses pythonVersion: "3.14"
```

All tools agree on Python 3.14.

### Example 2: Wrong Python Version

```bash
uv sync  # With Python 3.12 installed
# error: Python 3.12 does not match required version ==3.14.*
```

### Example 3: Surfaced Issues

Previously hidden issues from suppressions now visible:
```
src/llm_lsp_cli/daemon.py:45:10 - warning: Implicit string concatenation
```

Fix at source or add line-level suppression if intentional.
