# 3. Support absolute LSP server paths in configuration

Date: 2026-04-18

## Status

Accepted

## Context

Users cannot specify absolute paths for LSP server executables (e.g., `~/.local/share/nvim/mason/bin/basedpyright-langserver`). The current implementation uses `shutil.which()` exclusively, which only resolves executables available in `PATH`.

Users installing LSP servers via Mason (Neovim), custom toolchains, or isolated environments need to specify absolute paths to their server executables.

Requirements:
- Support simple command names: `pyright-langserver` (PATH lookup)
- Support absolute paths: `~/.local/share/nvim/mason/bin/basedpyright-langserver`
- Support environment variables: `$HOME/.local/bin/pyright-langserver`
- Maintain backward compatibility with existing configs

## Decision

We will support absolute paths, tilde expansion, and environment variables in the `command` field of `config.yaml`.

Implementation approach:
1. Detect if command contains path indicators (`/`, `~`, `$`)
2. If yes: expand `~` and environment variables, validate path exists and is executable
3. If no: fall back to `shutil.which()` PATH lookup

Validation rules:
- Non-existent paths produce clear error messages
- Paths must be executable files
- Tilde (`~`) expands to user's home directory
- Environment variables (`$VAR`, `${VAR}`) are expanded

Rejected alternatives:
- Separate config field for absolute paths: Adds complexity, no clear benefit over unified command field
- Only support PATH lookup: Forces users to modify PATH, poor UX for Mason users

## Consequences

**Positive:**
- Users can specify exact paths to LSP servers
- Works with Mason, custom toolchains, isolated environments
- Backward compatible with existing configs
- Clear error messages when paths are invalid

**Negative:**
- More complex path resolution logic
- Potential security risk if users specify untrusted paths (mitigated by executability check)

**Risks:**
- Path validation must be robust across platforms (Windows vs Unix)
- Tilde expansion must handle edge cases correctly
