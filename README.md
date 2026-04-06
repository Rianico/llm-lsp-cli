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

### Configuration

| Command | Description |
|---------|-------------|
| `llm-lsp-cli config show` | Show current configuration |
| `llm-lsp-cli config init` | Initialize default configuration |
| `llm-lsp-cli config path` | Show config file path |

## Configuration

Configuration is stored in `$XDG_CONFIG_HOME/llm-lsp-cli/config.json` (usually `~/.config/llm-lsp-cli/config.json`).

### Default Configuration

```json
{
  "trace_lsp": false,
  "timeout_seconds": 30,
  "languages": {
    "python": {
      "command": "pyright-langserver",
      "args": ["--stdio"],
      "initialize_params_file": "initialize_params_pyright.json"
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
| PID | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace}/{server}.pid` |
| Socket | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace}/{server}.sock` |
| Logs | `$XDG_RUNTIME_DIR/llm-lsp-cli/{workspace}/{server}.log` |

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
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=llm_lsp_cli --cov-report=html

# Run specific test file
pytest tests/test_server_registry.py -v
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
4. Check LSP server logs in `/tmp/llm-lsp-cli/{workspace}/{server}.log`

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
```

## Project Structure

```
llm-lsp-cli/
├── pyproject.toml          # Project configuration
├── README.md               # This file
├── CODEMAPS/               # Architectural documentation
│   ├── README.md           # Codemaps index
│   ├── architecture.md     # System architecture overview
│   ├── lsp-client-architecture.md
│   ├── capability-system.md
│   └── multi-language-support.md
├── plans/
│   └── implementation-blueprint.md
├── src/llm_lsp_cli/
│   ├── __init__.py
│   ├── __main__.py         # Entry point
│   ├── cli.py              # Typer CLI commands
│   ├── daemon.py           # Daemon implementation
│   ├── config/
│   │   ├── __init__.py
│   │   ├── manager.py      # Configuration manager
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
│   └── server/
│       ├── __init__.py
│       ├── workspace.py    # Workspace manager
│       └── registry.py     # Server registry
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    ├── test_cli.py                 # CLI command tests
    ├── test_config.py              # Configuration tests
    ├── test_daemon_handlers.py     # Daemon request handler tests
    ├── test_daemon_isolation.py    # Workspace isolation tests
    ├── test_e2e_daemon_lifecycle.py # End-to-end lifecycle tests
    ├── test_ipc.py                 # IPC protocol tests
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
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=llm_lsp_cli --cov-report=term-missing
```

## License

MIT License
