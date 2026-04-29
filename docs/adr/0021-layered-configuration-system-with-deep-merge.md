# 21. Layered configuration system with deep merge

Date: 2026-04-29

## Status

Accepted

## Context

Users running `llm-lsp-cli` via `uvx` expect zero-setup operation, while also needing per-project customization. The existing configuration only supports global config auto-creation, lacking:

1. Project-local configuration for team-specific settings
2. Clear merge semantics when multiple config sources coexist
3. Informative first-run experience explaining configuration options

The solution must maintain Clean Architecture boundaries (ConfigManager in infrastructure layer, pure merge logic testable without I/O) and align with XDG directory conventions already in use.

## Decision

We will implement a three-tier configuration system with Project > Global > Defaults priority, using deep merge for nested dictionaries and list replacement.

**Configuration Priority:**
| Layer | Location | Priority |
|-------|----------|----------|
| Defaults | `DEFAULT_CONFIG` (code) | Lowest |
| Global | `~/.config/llm-lsp-cli/config.yaml` | Medium |
| Project | `$PWD/.llm-lsp-cli.yaml` | Highest |

**Merge Strategy:**
- Deep merge for nested dicts (e.g., `languages.python.command` can override without redeclaring all languages)
- List replacement, not concatenation
- Shallow merge for top-level scalars

**Auto-initialization:**
- Missing global config is auto-created with defaults
- First-run notice displayed only when auto-creating (not on every run)

**Discovery Scope:**
- Project config discovered in current directory only (no parent traversal)
- Explicit location over implicit discovery for reproducibility

Rejected alternatives:
- **Parent directory traversal**: Rejected to avoid surprise configs from parent projects
- **pyproject.toml [tool.llm-lsp-cli]**: Rejected to remain language-agnostic and avoid parsing complexity
- **Shallow merge only**: Rejected because it would require redeclaring entire `languages` block to override one server
- **Explicit init required**: Rejected to maintain zero-friction uvx experience

## Consequences

**Positive:**
- Zero-setup experience for uvx users (global config auto-created)
- Project-level customization without affecting global settings
- Minimal config files (only override what's needed)
- Deep merge allows surgical overrides of nested server configurations
- Clear precedence rules avoid ambiguity

**Negative:**
- Deep merge logic must be tested for edge cases (circular references, type mismatches)
- Current-directory-only discovery requires users to run from project root
- List replacement may surprise users expecting concatenation

**Risks:**
- Config precedence bugs if merge order is wrong (mitigated by unit tests)
- Global config corruption if auto-creation fails mid-write (mitigated by atomic write)
