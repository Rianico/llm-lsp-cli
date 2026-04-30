# Project Instructions: llm-lsp-cli

## Tech Stack

Python 3.10+ CLI with Typer, Pydantic 2.5+, python-daemon. Uses uv for package management, ruff for linting, mypy (strict) for type checking, pytest for testing.

## Code Style

- **Type hints**: Required on all functions (mypy strict mode)
- **Naming**: `snake_case` for files/functions/variables, `PascalCase` for classes
- **Models**: Use Pydantic for data validation and configuration
- **Async**: Use async/await for I/O operations (daemon, LSP communication)
- **Immutability**: Prefer returning new objects over mutation

## Testing

```bash
uv run pytest tests/ -q              # Run all tests (quiet)
uv run pytest tests/ --cov=llm_lsp_cli --cov-report=term-missing  # With coverage
```

**Test naming:** `test_<feature>.py` (e.g., `test_daemon_client.py`)

**Fixtures:** Common fixtures in `tests/conftest.py` (temp_dir, temp_file, sample_python_file)

## Build & Run

```bash
uv sync --all-extras    # Install with dev dependencies
uv run ruff check src/  # Lint
uv run mypy src/        # Type check
uv run llm-lsp-cli --help  # Run CLI
```

## Project Structure

```
src/llm_lsp_cli/
├── cli.py              # CLI entry point, command registration
├── daemon.py           # Daemon process manager
├── daemon_client.py    # Daemon IPC client
├── commands/           # CLI command implementations (daemon, lsp, config)
├── lsp/                # LSP protocol (client, cache, transport, types)
├── ipc/                # JSON-RPC over UNIX sockets
├── config/             # Configuration management, server capabilities
├── output/             # LLM-optimized output formatting
├── test_filter/        # Test file exclusion patterns
├── domain/             # Domain layer (entities, services, repositories, value_objects)
├── server/             # Server registry and workspace management
├── application/        # Application interfaces (dependency injection boundaries)
├── infrastructure/     # Infrastructure implementations (config, ipc, logging)
├── shared/             # Shared utilities (logging)
└── utils/              # General utilities (formatter, language_detector, uri)
```

## Key Conventions

### Commit Style
Conventional commits with scope: `feat(lsp):`, `fix(daemon):`, `refactor(output):`, `docs(adr):`

### Error Handling
Rich exceptions in `exceptions.py` with context:
- `DaemonError` includes workspace/language context and log file path
- `DaemonStartupTimeoutError`, `DaemonCrashedError` for specific daemon failures

### LSP Integration
- **Caching**: mtime-based invalidation (file modification time is ground truth)
- **Document sync**: Files stay open for session (no didClose)
- **Capabilities**: Server-specific JSON files in `config/capabilities/`

### Output Format
LLM-optimized compact output:
- Relative paths (strip `file://` and workspace root)
- Compact ranges: `"1:1-50:1"` instead of nested objects
- `--format text|json|yaml|csv` for output control

## Architecture Decisions

Key ADRs in `docs/adr/`:
- **ADR-0008**: mtime-based cache invalidation
- **ADR-0010**: External file change notification (`did-change` command)
- **ADR-0011**: LSP call hierarchy (incoming/outgoing calls)
- **ADR-0016**: Server-specific LSP client capabilities
- **ADR-0019**: LSP rename feature with layered service architecture
- **ADR-0021**: Layered configuration system (Project > Global > Defaults)

## Adding New LSP Server Support

1. Create `src/llm_lsp_cli/config/capabilities/<server-name>.json`
2. Add server to `_SERVERS` dict in `config/capabilities/__init__.py`
3. Register language server command in default config (`config/defaults.py`)
