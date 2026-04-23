# llm-lsp-cli

A CLI tool that interacts with Language Server Protocol (LSP) servers to provide code intelligence features (definitions, references, completions, symbols, hover) for LLM-assisted development.

## Features

- **Definition Lookup**: Find where symbols are defined
- **References**: Find all references to a symbol
- **Completions**: Get code completion suggestions
- **Hover**: Show type information and documentation
- **Document Symbols**: List symbols in a file
- **Workspace Symbols**: Search symbols across the workspace

## Architecture

See [CODEMAPS/architecture.md](CODEMAPS/architecture.md) for system architecture overview.

- **CLI <-> Daemon**: UNIX domain sockets with JSON-RPC 2.0 protocol
- **Daemon <-> LSP**: stdio transport with LSP 3.17 protocol
- **Configuration**: XDG Base Directory specification

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
llm-lsp-cli start
```

### 3. Use LSP Features

```bash
# Get definition at position (0-based line/column)
llm-lsp-cli definition src/main.py 10 5

# Find references
llm-lsp-cli references src/main.py 10 5

# Get completions
llm-lsp-cli completion src/main.py 10 5

# Show hover information
llm-lsp-cli hover src/main.py 10 5

# List document symbols
llm-lsp-cli document-symbol src/main.py

# Search workspace symbols
llm-lsp-cli workspace-symbol MyClass
```

**Options:**
- `--format text|json|yaml`: Output format (default: `json`)
- `--include-tests`: Include test files (excluded by default)
- `--language LANG`: Override language auto-detection

### 4. Stop the Daemon

```bash
llm-lsp-cli stop
```

## Configuration

Configuration is stored in `$XDG_CONFIG_HOME/llm-lsp-cli/config.yaml` (usually `~/.config/llm-lsp-cli/config.yaml`).

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
trace_lsp: false
timeout_seconds: 30
```

### Configuration Files

| File | Path |
|------|------|
| Config | `$XDG_CONFIG_HOME/llm-lsp-cli/config.yaml` |
| PID | `$PWD/.llm-lsp-cli/{server}.pid` |
| Socket | `$PWD/.llm-lsp-cli/{server}.sock` |
| Daemon Log | `$PWD/.llm-lsp-cli/daemon.log` |

## Test Filtering

The test filtering system automatically detects and filters test files from LSP results using glob-based pattern matching. By default, `definition`, `references`, and `workspace-symbol` commands exclude test files.

### Glob Pattern Syntax

| Pattern | Description | Example |
|---------|-------------|---------|
| `*` | Matches any characters except `/` | `test_*.py` matches `test_utils.py` |
| `**` | Matches any number of directory levels | `**/tests/**` matches `src/tests/test.py` |

### Default Patterns by Language

| Language | Patterns |
|----------|----------|
| Python | `**/tests/**`, `test_*.py`, `*_test.py` |
| TypeScript | `**/__tests__/**`, `*.test.ts`, `*.spec.ts` |
| Go | `*_test.go` |
| Rust | `**/tests/**` |

### Usage

```bash
# Exclude test files (default)
llm-lsp-cli definition src/main.py 10 5

# Include test files
llm-lsp-cli definition src/main.py 10 5 --include-tests
```

## Language Server Requirements

| Language | Server | Install |
|----------|--------|---------|
| Python | basedpyright-langserver | `pip install basedpyright` |
| TypeScript/JavaScript | typescript-language-server | `npm install -g typescript-language-server` |
| Rust | rust-analyzer | `rustup component add rust-analyzer` |
| Go | gopls | `go install golang.org/x/tools/gopls@latest` |

## Troubleshooting

### Daemon won't start

1. Check if already running: `llm-lsp-cli status`
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

See [CODEMAPS/](CODEMAPS/) for architectural documentation.

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
