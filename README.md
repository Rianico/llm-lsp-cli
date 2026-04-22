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

```
┌─────────────────┐     UNIX Socket      ┌───────────────────────┐     stdio     ┌─────────────────┐
│   CLI Client    │ ◄─────────────────►  │    LSP Daemon         │ ◄───────────► │  LSP Server     │
│  (llm-lsp-cli)  │   (JSON-RPC 2.0)     │  (long-running)       │   (LSP 3.17)  │  (pylsp, etc.)  │
└─────────────────┘                      └───────────────────────┘               └─────────────────┘
```

- **CLI ↔ Daemon**: UNIX domain sockets with JSON-RPC 2.0 protocol
- **Daemon ↔ LSP**: stdio transport with LSP 3.17 protocol
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
# Create default configuration: $XDG_CONFIG_HOME/llm-lsp-cli
llm-lsp-cli config init
```

### 2. Start the Daemon

```bash
# Start the LSP daemon (defaults to Python)
llm-lsp-cli start

# Or specify a language explicitly
llm-lsp-cli start -l typescript
```

### 3. Check Status

```bash
# View daemon status
llm-lsp-cli status
```

### 4. Use LSP Features

The language is auto-detected from the file extension. You can also override with `--language` / `-l`.

All LSP feature commands support:
- `--format`, `-o`: Output format (`text`, `json`, `yaml`) - default is `json`
- `--include-tests`: Include results from test files (excluded by default for `definition`, `references`, `workspace-symbol`)

```bash
# Get definition at position (0-based line/column)
llm-lsp-cli definition src/main.py 10 5

# Find references (exclude test files by default)
llm-lsp-cli references src/main.py 10 5
llm-lsp-cli references src/main.py 10 5 --include-tests  # Include test files

# Get completions
llm-lsp-cli completion src/main.py 10 5

# Show hover information
llm-lsp-cli hover src/main.py 10 5

# List document symbols
llm-lsp-cli document-symbol src/main.py

# Search workspace symbols
llm-lsp-cli workspace-symbol MyClass

# Output in different formats
llm-lsp-cli definition src/main.py 10 5 --format text
llm-lsp-cli references src/main.py 10 5 --format yaml
```

### 5. Stop the Daemon

```bash
# Stop the LSP daemon
llm-lsp-cli stop
```

## Commands

### Daemon Lifecycle

| Command | Description |
|---------|-------------|
| `llm-lsp-cli start` | Start the LSP daemon |
| `llm-lsp-cli stop` | Stop the LSP daemon |
| `llm-lsp-cli restart` | Restart the LSP daemon |
| `llm-lsp-cli status` | Show daemon status |

**Options:**
- `--workspace PATH`, `-w PATH`: Specify workspace root (default: current directory)
- `--language FILE`, `-l FILE`: Language (auto-detected from file extension for feature commands)

### LSP Features

| Command | Description |
|---------|-------------|
| `definition <file> <line> <col>` | Get definition location |
| `references <file> <line> <col>` | Find all references |
| `completion <file> <line> <col>` | Get completions |
| `hover <file> <line> <col>` | Show hover info |
| `document-symbol <file>` | List file symbols |
| `workspace-symbol <query>` | Search workspace |

**Options:**
- `--workspace PATH`, `-w PATH`: Specify workspace root (default: current directory)
- `--language FILE`, `-l FILE`: Override language auto-detection
- `--format FORMAT`, `-o FORMAT`: Output format (`text`, `json`, `yaml`) - default is `json`
- `--include-tests`: Include results from test files (`definition`, `references`, `workspace-symbol` only)

### Configuration

| Command | Description |
|---------|-------------|
| `llm-lsp-cli config show` | Show current configuration |
| `llm-lsp-cli config init` | Initialize default configuration |
| `llm-lsp-cli config path` | Show config file path |

## Configuration

Configuration is stored in `$XDG_CONFIG_HOME/llm-lsp-cli/config.json` (usually `~/.config/llm-lsp-cli/config.json`).

### Configuration Files

| File | Purpose | Location |
|------|---------|----------|
| `config.json` | Main configuration | `$XDG_CONFIG_HOME/llm-lsp-cli/config.json` |
| `capabilities/*.json` | LSP server initialization params | `$XDG_CONFIG_HOME/llm-lsp-cli/capabilities/` |

### Capabilities Files

Per-server LSP capability configurations:

| File | Server |
|------|--------|
| `pyright-langserver.json` | Python (pyright) |
| `typescript-language-server.json` | TypeScript/JavaScript |
| `rust-analyzer.json` | Rust |
| `gopls.json` | Go |
| `jdtls.json` | Java |
| `default.json` | Fallback configuration |

### Default Configuration

```json
{
  "trace_lsp": false,
  "timeout_seconds": 30,
  "languages": {
    "python": {
      "command": "pyright-langserver",
      "args": ["--stdio"],
      "initialize_params_file": "pyright-langserver.json"
    },
    "typescript": {
      "command": "typescript-language-server",
      "args": ["--stdio"]
    },
    "javascript": {
      "command": "typescript-language-server",
      "args": ["--stdio"]
    },
    "rust": {
      "command": "rust-analyzer"
    },
    "go": {
      "command": "gopls"
    },
    "java": {
      "command": "jdtls"
    },
    "cpp": {
      "command": "clangd"
    },
    "csharp": {
      "command": "OmniSharp"
    }
  }
}
```

### Environment Variables

The following XDG environment variables are supported:

| Variable | Description | Default |
|----------|-------------|---------|
| `XDG_CONFIG_HOME` | Configuration directory | `~/.config` |
| `XDG_STATE_HOME` | State directory | `~/.local/state` |
| `XDG_RUNTIME_DIR` | Runtime directory (PID, socket) | Falls back to `$TMPDIR` or `/tmp` |

**Runtime Path Structure:**
```
${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/llm-lsp-cli/{workspace_name}-{workspace_hash}/{lsp_server_name}.{sock,pid,log}
```

### Configuration File Locations

| File | Path |
|------|------|
| Config | `$XDG_CONFIG_HOME/llm-lsp-cli/config.json` |
| Capabilities | `$XDG_CONFIG_HOME/llm-lsp-cli/capabilities/*.json` |
| PID | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace_name}-{workspace_hash}/{server}.pid` |
| Socket | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace_name}-{workspace_hash}/{server}.sock` |
| Logs | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace_name}-{workspace_hash}/{server}.log` |
| Daemon Log | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace_name}-{workspace_hash}/daemon.log` |

## Test Filtering

The test filtering system automatically detects and filters test files from LSP results using glob-based pattern matching. By default, the `definition`, `references`, and `workspace-symbol` commands exclude test files to focus on production code.

### Glob Pattern Syntax

| Pattern | Description | Example |
|---------|-------------|---------|
| `*` | Matches any characters except `/` | `test_*.py` matches `test_utils.py` |
| `**` | Matches any number of directory levels | `**/tests/**` matches `src/tests/test.py` |
| `?` | Matches single character | `test_?.py` matches `test_a.py` |

### Pattern Types

1. **Directory Patterns**: Match full paths containing test directories
   - Examples: `**/tests/**`, `**/__tests__/**`, `**/spec/**`

2. **Suffix Patterns**: Match file endings
   - Examples: `_test.go`, `.test.ts`, `.spec.js`, `test_*.py`

3. **Prefix Patterns**: Match file name beginnings
   - Examples: `test_`, `_test`

4. **Include Patterns**: Negation patterns to exclude files from test classification
   - Examples: `**/tests/fixtures/**`, `**/tests/conftest.py`

### Default Language Configurations

| Language | Directory Patterns | Suffix Patterns | Include Patterns |
|----------|-------------------|-----------------|------------------|
| Python | `**/tests/**`, `**/test/**` | `_test.py`, `.test.py`, `test_*.py` | `**/tests/fixtures/**`, `**/tests/conftest.py` |
| TypeScript | `**/__tests__/**`, `**/spec/**` | `.test.ts`, `.spec.ts` | - |
| JavaScript | `**/__tests__/**`, `**/spec/**` | `.test.js`, `.spec.js` | - |
| Go | - | `_test.go` | - |
| Rust | `**/tests/**` | - | `**/tests/common/**` |
| Java | `**/src/test/**` | - | - |
| C# | `**/Tests/**` | `.test.cs`, `.spec.cs` | - |

### Customizing Test Filter Patterns

Edit `$XDG_CONFIG_HOME/llm-lsp-cli/config.json`:

```json
{
    "test_filter": {
        "defaults": {
            "enabled": true,
            "directory_patterns": ["**/tests/**", "**/spec/**"],
            "suffix_patterns": ["_test.py", ".test.ts"],
            "prefix_patterns": ["test_"],
            "include_patterns": []
        },
        "languages": {
            "python": {
                "enabled": true,
                "directory_patterns": ["**/tests/**"],
                "suffix_patterns": ["_test.py", "test_*.py"],
                "prefix_patterns": [],
                "include_patterns": ["**/tests/fixtures/**"]
            }
        }
    }
}
```

### Using --include-tests Flag

```bash
# Filter test files (default behavior)
llm-lsp-cli definition src/main.py 10 5
llm-lsp-cli references src/main.py 10 5
llm-lsp-cli workspace-symbol MyClass

# Include test files in results
llm-lsp-cli definition src/main.py 10 5 --include-tests
llm-lsp-cli references src/main.py 10 5 --include-tests
llm-lsp-cli workspace-symbol MyClass --include-tests
```

## Language Server Requirements

You need to install the appropriate language server for your project language:

| Language | Server | Install |
|----------|--------|---------|
| Python | pyright-langserver | `pip install pyright` or `npm install -g pyright` |
| TypeScript/JavaScript | typescript-language-server | `npm install -g typescript-language-server typescript` |
| Rust | rust-analyzer | `rustup component add rust-analyzer` |
| Go | gopls | `go install golang.org/x/tools/gopls@latest` |
| Java | jdtls | See [Eclipse JDT LS](https://projects.eclipse.org/projects/eclipse.jdt.ls) |
| C/C++ | clangd | `apt install clangd` or `brew install llvm` |
| C# | OmniSharp | `dotnet tool install -g omnisharp` |

## Examples

### Python Example

```bash
# Start daemon
llm-lsp-cli start -l python

# Find where a function is defined
llm-lsp-cli definition myapp/views.py 42 10

# Find all usages of a variable
llm-lsp-cli references myapp/models.py 15 5

# Get type information
llm-lsp-cli hover myapp/utils.py 100 8

# List all classes and functions in a file
llm-lsp-cli document-symbol myapp/core.py

# Search for a class across the workspace
llm-lsp-cli workspace-symbol UserService

# Stop daemon when done
llm-lsp-cli stop
```

### TypeScript Example

```bash
# Start daemon for TypeScript project
llm-lsp-cli start -l typescript

# Find where a function is defined
llm-lsp-cli definition src/index.ts 42 10

# Find all usages of a variable
llm-lsp-cli references src/utils.ts 15 5

# Get completions
llm-lsp-cli completion src/app.tsx 100 8

# Stop daemon
llm-lsp-cli stop
```

### Rust Example

```bash
# Start daemon for Rust project
llm-lsp-cli start -l rust

# Find where a struct is defined
llm-lsp-cli definition src/main.rs 42 10

# Find all usages of a function
llm-lsp-cli references src/lib.rs 15 5

# Get type information
llm-lsp-cli hover src/types.rs 100 8

# List all functions and structs in a file
llm-lsp-cli document-symbol src/lib.rs

# Stop daemon
llm-lsp-cli stop
```

### Java Example

```bash
# Start daemon for Java project
llm-lsp-cli start -l java

# Find where a class is defined
llm-lsp-cli definition src/main/java/com/example/MyClass.java 42 10

# Find all usages of a method
llm-lsp-cli references src/main/java/com/example/Service.java 15 5

# Get type information
llm-lsp-cli hover src/main/java/com/example/Model.java 100 8

# Stop daemon
llm-lsp-cli stop
```

**Note:** Language is auto-detected from file extension for LSP commands. You can also explicitly specify with `--language` / `-l` option.

## Testing

```bash
# Run all tests
pytest tests/ 

# Run with coverage
pytest tests/ --cov=llm_lsp_cli --cov-report=html

# Run specific test file
pytest tests/test_server_registry.py 
```

## Troubleshooting

### Daemon won't start

1. Check if already running:
   ```bash
   llm-lsp-cli status
   ```
2. Check log file for errors:
   ```bash
   # Find the log file location from status output
   llm-lsp-cli status
   # Check runtime logs (typically in $XDG_RUNTIME_DIR or /tmp)
   ```
3. Clean up stale PID file if needed:
   ```bash
   rm ${XDG_RUNTIME_DIR:-/tmp}/llm-lsp-cli/*/daemon.pid
   ```

### "Language server not found"

Install the appropriate language server for your project language. See [Language Server Requirements](#language-server-requirements).

### Socket connection refused

1. Ensure daemon is running: `llm-lsp-cli status`
2. Check socket permissions:
   ```bash
   ls -la ${XDG_RUNTIME_DIR:-/tmp}/llm-lsp-cli/*/*.sock
   ```

### No results from LSP queries

1. Ensure the file exists and is within the workspace
2. Check that the language server is properly configured
3. Enable LSP tracing by adding `"trace_lsp": true` to your config
4. Check LSP server logs in `${XDG_RUNTIME_DIR:-/tmp}/llm-lsp-cli/{workspace-hash}/{server}.log`

### Pyright not finding symbols

1. Ensure workspace is fully indexed (wait a few seconds after starting daemon)
2. Check that `pyright-langserver` is installed: `which pyright-langserver`
3. Verify pyright config in `~/.config/llm-lsp-cli/capabilities/pyright-langserver.json`

## Available Scripts

The following commands are available via the `llm-lsp-cli` entry point:

```bash
# Daemon lifecycle
llm-lsp-cli start          # Start the LSP daemon
llm-lsp-cli stop           # Stop the LSP daemon
llm-lsp-cli restart        # Restart the LSP daemon
llm-lsp-cli status         # Show daemon status

# LSP features
llm-lsp-cli definition <file> <line> <col>    # Get definition location
llm-lsp-cli references <file> <line> <col>    # Find all references
llm-lsp-cli completion <file> <line> <col>    # Get completions
llm-lsp-cli hover <file> <line> <col>         # Show hover info
llm-lsp-cli document-symbol <file>            # List file symbols
llm-lsp-cli workspace-symbol <query>          # Search workspace

# Configuration
llm-lsp-cli config show    # Show current configuration
llm-lsp-cli config init    # Initialize default configuration
llm-lsp-cli config path    # Show config file path

# Other
llm-lsp-cli version        # Show version

# Global options (can be used with any command)
llm-lsp-cli --help                     # Show help
llm-lsp-cli <command> --help           # Show help for specific command
llm-lsp-cli <command> --workspace PATH # Override workspace path
llm-lsp-cli <command> --language LANG  # Override language detection
llm-lsp-cli <command> --format FORMAT  # Output format (text, json, yaml)
```

**Start Command Options:**
- `--debug`, `-d`: Enable debug logging
- `--lsp-conf`, `-c`: Custom LSP capabilities config file

## Project Structure

```
llm-lsp-cli/
├── pyproject.toml          # Project configuration
├── README.md               # This file
├── CLAUDE.md               # Developer quick reference
├── CODEMAPS/               # Architectural documentation
│   ├── README.md           # Codemaps index
│   ├── architecture.md     # System architecture overview
│   ├── lsp-client-architecture.md
│   ├── capability-system.md
│   └── multi-language-support.md
├── src/llm_lsp_cli/
│   ├── __init__.py         # Package init, version
│   ├── __main__.py         # python -m entry point
│   ├── cli.py              # Typer CLI commands
│   ├── daemon.py           # Daemon process management
│   ├── test_filter/        # Test file filtering (glob patterns)
│   │   ├── __init__.py     # Public API, config loading
│   │   ├── pattern_engine.py  # Glob pattern matching engine
│   │   └── language_registry.py  # Per-language pattern registry
│   ├── config/
│   │   ├── __init__.py
│   │   ├── manager.py      # Configuration manager, XDG paths
│   │   ├── schema.py       # Pydantic models
│   │   ├── defaults.py     # Default configs
│   │   └── capabilities/   # LSP capabilities JSON files
│   ├── ipc/
│   │   ├── __init__.py
│   │   ├── protocol.py     # JSON-RPC protocol
│   │   ├── unix_client.py  # UNIX socket client
│   │   └── unix_server.py  # UNIX socket server
│   ├── lsp/
│   │   ├── __init__.py
│   │   ├── client.py       # LSP client
│   │   ├── types.py        # LSP types
│   │   ├── constants.py    # LSP constants
│   │   └── transport.py    # stdio transport
│   ├── server/
│   │   ├── __init__.py
│   │   ├── workspace.py    # Workspace manager
│   │   └── registry.py     # Server registry
│   └── utils/
│       ├── __init__.py
│       ├── formatter.py    # Output formatting utilities
│       └── language_detector.py  # Language auto-detection
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    ├── test_cli.py                 # CLI command tests
    ├── test_config.py              # Configuration tests
    ├── test_daemon_handlers.py     # Daemon request handler tests
    ├── test_daemon_isolation.py    # Workspace isolation tests
    ├── test_e2e_daemon_lifecycle.py # End-to-end lifecycle tests
    ├── test_filter.py              # Test file filtering tests
    ├── test_ipc.py                 # IPC protocol tests
    ├── test_language_detector.py   # Language detection tests
    ├── test_lsp_integration.py     # LSP integration tests
    ├── test_lsp_types.py           # LSP types tests
    └── test_server_registry.py     # Server registry tests
```

## Development

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
