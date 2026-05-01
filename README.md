# llm-lsp-cli

An LSP CLI for LLMs - a daemon-backed command-line interface supporting multiple language servers, with compact output optimized for AI consumption and Claude Code hooks/skills integration.

## Why This Project

Official LSP plugins for editors often fail to recognize modern Python tooling like `uv` and `venv` properly. This leads to false diagnostics such as "cannot import pytest" errors even when pytest is installed in the active virtual environment and declared in `pyproject.toml` dependencies. This CLI provides direct LSP access with proper environment detection, giving LLMs reliable code intelligence without editor-specific configuration issues.

## Features

- **Definition Lookup**: Find where symbols are defined
- **References**: Find all references to a symbol
- **Completions**: Get code completion suggestions
- **Hover**: Show type information and documentation
- **Document Symbols**: List symbols in a file
- **Workspace Symbols**: Search symbols across the workspace
- **Diagnostics**: Get diagnostics for a file or entire workspace
- **Call Hierarchy**: Find incoming callers and outgoing callees
- **Rename**: Rename symbols across the workspace with preview and rollback

## LLM-Optimized Output

The CLI produces token-efficient output designed for LLM consumption:

- **Compact Ranges**: `"1:1-50:1"` instead of nested `{"start": {"line": 0, "character": 0}, "end": {"line": 49, "character": 0}}`
- **Relative Paths**: `src/main.py` instead of `file:///workspace/src/main.py`
- **Multiple Formats**: `--format text|json|yaml|csv` for flexibility
- **Test Filtering**: Automatic exclusion of test files (configurable with `--include-tests`)

**Example output:**
```json
{
  "_source": "basedpyright",
  "file_path": "src/llm_lsp_cli/commands/lsp.py",
  "command": "definition",
  "result": [
    {"file": "src/llm_lsp_cli/daemon_client.py", "range": "15:1-45:1"}
  ]
}
```

This format allows LLMs to immediately identify file ranges without parsing verbose LSP protocol responses.

## Architecture

See [docs/architecture/blueprint.md](docs/architecture/blueprint.md) for system architecture overview.

- **CLI <-> Daemon**: UNIX domain sockets with JSON-RPC 2.0 protocol
- **Daemon <-> LSP**: stdio transport with LSP 3.17 protocol
- **Configuration**: XDG Base Directory specification
- **Capabilities**: Server-specific JSON files loaded by server basename (see `config/capabilities/`)

## Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package
cd llm-lsp-cli
uv sync
```

## Quick Start

### 1. Initialize Configuration

```bash
llm-lsp-cli config init
```

### 2. Start the Daemon

```bash
# Start with default options
llm-lsp-cli daemon start

# Start with diagnostic log file (full LSP messages for debugging)
llm-lsp-cli daemon start --diagnostic-log

# Start with trace logging (most verbose, includes LSP transport)
llm-lsp-cli daemon start --trace
```

### 3. Use LSP Features

**Indexing:** Line and column numbers are 1-based for both input and output, matching editor conventions. Use positions as they appear in your editor (e.g., if `document-symbol` shows `range: "9:1-9:4"`, pass `9 1` to other commands).

```bash
# Get definition at position (line 10, column 5)
llm-lsp-cli lsp definition src/main.py 10 5

# Find references
llm-lsp-cli lsp references src/main.py 10 5

# Get completions
llm-lsp-cli lsp completion src/main.py 10 5

# Show hover information
llm-lsp-cli lsp hover src/main.py 10 5

# List document symbols
llm-lsp-cli lsp document-symbol src/main.py

# Search workspace symbols
llm-lsp-cli lsp workspace-symbol MyClass

# Get diagnostics for a file
llm-lsp-cli lsp diagnostics src/main.py

# Get diagnostics for entire workspace
llm-lsp-cli lsp workspace-diagnostics

# Find incoming calls (callers)
llm-lsp-cli lsp incoming-calls src/main.py 10 5

# Find outgoing calls (callees)
llm-lsp-cli lsp outgoing-calls src/main.py 10 5

# Rename symbol (preview changes)
llm-lsp-cli lsp rename src/main.py 10 5 new_name

# Rename symbol (apply changes, creates backup for rollback)
llm-lsp-cli lsp rename src/main.py 10 5 new_name --apply

# Rollback a rename session
llm-lsp-cli lsp rename --rollback <session-id>

# Notify daemon of external file change (for file watchers, CI tools)
llm-lsp-cli lsp did-change src/main.py
```

**Options:**
- `--format text|json|yaml|csv`: Output format (default: `json`)
- `--include-tests`: Include test files (excluded by default)
- `--language LANG`: Override language auto-detection
- `--raw`: Show original LSP server response (for debugging)
- `--depth N`: Hierarchy depth for symbol commands (default: 1)

### 4. Stop the Daemon

```bash
llm-lsp-cli daemon stop
```

### Daemon Management Commands

```bash
# Check daemon status
llm-lsp-cli daemon status

# Restart the daemon
llm-lsp-cli daemon restart

# Start with custom LSP config
llm-lsp-cli daemon start --lsp-conf /path/to/lsp-config.json
```

## Configuration

Configuration follows a three-tier priority system: **Project > Global > Defaults**.

| Layer | Location | Priority |
|-------|----------|----------|
| Project | `$PWD/.llm-lsp-cli.yaml` | Highest |
| Global | `$XDG_CONFIG_HOME/llm-lsp-cli/config.yaml` (usually `~/.config/llm-lsp-cli/config.yaml`) | Medium |
| Defaults | Built-in (`DEFAULT_CONFIG`) | Lowest |

### Default Configuration

```yaml
languages:
  python:
    command: basedpyright-langserver
    args: [--stdio]
  typescript:
    command: typescript-language-server
    args: [--stdio]
  javascript:
    command: typescript-language-server
    args: [--stdio]
  rust:
    command: rust-analyzer
  go:
    command: gopls
  java:
    command: jdtls
  cpp:
    command: clangd
  csharp:
    command: OmniSharp
trace_lsp: false
timeout_seconds: 30
```

### Creating Configuration

```bash
# Create global config
llm-lsp-cli config init

# Create project-local config (for team-specific settings)
llm-lsp-cli config init --project
```

### Listing Server Capabilities

```bash
# List capabilities for all LSP servers
llm-lsp-cli config list

# List capabilities for a specific server
llm-lsp-cli config list --lsp-server pyright-langserver

# Output in different formats
llm-lsp-cli config list --format yaml
```

### Configuration Files

| File | Path |
|------|------|
| Config | `$XDG_CONFIG_HOME/llm-lsp-cli/config.yaml` |
| PID | `$PWD/.llm-lsp-cli/{server}.pid` |
| Socket | `$PWD/.llm-lsp-cli/{server}.sock` |
| Daemon Log | `$PWD/.llm-lsp-cli/daemon.log` |
| Diagnostic Log | `$PWD/.llm-lsp-cli/diagnostics.log` (only with `--diagnostic-log`) |

## Test Filtering

The test filtering system automatically detects and filters test files from LSP results using glob-based pattern matching. By default, `definition`, `references`, `workspace-symbol`, and `workspace-diagnostics` commands exclude test files.

### Default Patterns by Language

| Language | Directory Patterns | File Patterns |
|----------|-------------------|---------------|
| Python | `**/tests/**`, `**/test/**` | `test_*.py`, `*_test.py`, `.test.py` |
| TypeScript | `**/__tests__/**`, `**/spec/**` | `*.test.ts`, `*.spec.ts` |
| JavaScript | `**/__tests__/**`, `**/spec/**` | `*.test.js`, `*.spec.js` |
| Go | - | `*_test.go` |
| Rust | `**/tests/**` | - |
| Java | `**/src/test/**`, `**/src/tests/**` | - |
| C# | `**/Tests/**`, `**/Test/**` | `*.test.cs`, `*.spec.cs` |
| C/C++ | `**/tests/**`, `**/test/**`, `**/unittests/**` | `*_test.c`, `*_test.cpp` |

### Usage

```bash
# Exclude test files (default)
llm-lsp-cli lsp definition src/main.py 10 5

# Include test files
llm-lsp-cli lsp definition src/main.py 10 5 --include-tests
```

## External File Change Notification

The `did-change` command notifies the LSP server when files are modified externally (e.g., by editors, file watchers, or CI tools). This triggers LSP reanalysis without restarting the daemon.

```bash
# Notify daemon of external file change
llm-lsp-cli lsp did-change src/main.py

# Then get updated diagnostics
llm-lsp-cli lsp diagnostics src/main.py
```

The command automatically handles:
- Sending `didOpen` if the file is not yet open or the mtime differs
- Sending `didChange` with full text sync
- Cache coherence via mtime-based invalidation

## Diagnostic Logging

For debugging LSP server issues, enable the diagnostic log file:

```bash
llm-lsp-cli daemon start --diagnostic-log
# Creates: $PWD/.llm-lsp-cli/diagnostics.log
```

This writes full (unmasked) LSP diagnostic messages to a separate file. Use `--trace` for maximum verbosity (includes LSP transport messages).

## Language Server Requirements

| Language | Server | Install |
|----------|--------|---------|
| Python | basedpyright-langserver | `pip install basedpyright` or `uv tool install basedpyright` |
| TypeScript/JavaScript | typescript-language-server | `npm install -g typescript-language-server typescript` |
| Rust | rust-analyzer | `rustup component add rust-analyzer` |
| Go | gopls | `go install golang.org/x/tools/gopls@latest` |
| Java | jdtls | Download from Eclipse JDT Language Server releases |
| C/C++ | clangd | `brew install llvm` (macOS) or system package manager |
| C# | OmniSharp | Download from OmniSharp releases |

## Troubleshooting

### Daemon won't start

1. Check if already running: `llm-lsp-cli daemon status`
2. Check log file: `cat $PWD/.llm-lsp-cli/daemon.log`
3. Clean up stale PID: `rm $PWD/.llm-lsp-cli/daemon.pid`

### "Language server not found"

Install the appropriate language server. See [Language Server Requirements](#language-server-requirements).

### No results from LSP queries

1. Ensure the file exists and is within the workspace
2. Check that the language server is properly configured
3. Enable LSP tracing: add `trace_lsp: true` to config
4. Check daemon logs: `cat $PWD/.llm-lsp-cli/daemon.log`

## Development

See [docs/architecture/](docs/architecture/) for architectural documentation.

```bash
# Install with development dependencies
uv sync --all-extras

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/ tests/

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=llm_lsp_cli --cov-report=term-missing
```

## License

MIT License
