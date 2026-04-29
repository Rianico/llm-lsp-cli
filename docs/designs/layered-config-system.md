---
title: Layered Configuration System
status: approved
date: 2026-04-29
---

# Design: Layered Configuration System for uvx Users

## Problem Statement

When users run `llm-lsp-cli` via `uvx` without prior setup, they expect the tool to work immediately. The current design auto-creates global config, but lacks:

1. **Project-local configuration** for per-project settings
2. **Informative first-run experience** explaining config options

## Solution

Implement a layered configuration system with three tiers:

```
Defaults → Global (~/.config/llm-lsp-cli/config.yaml) → Project (.llm-lsp-cli.yaml)
```

## Config Discovery & Priority

| Layer | Location | Priority |
|-------|----------|----------|
| Defaults | `DEFAULT_CONFIG` (code) | Lowest |
| Global | `~/.config/llm-lsp-cli/config.yaml` | Medium |
| Project | `$PWD/.llm-lsp-cli.yaml` | Highest |

### Discovery Logic

1. Load `DEFAULT_CONFIG` as base
2. If global config exists: merge into base
   Else: create global config with defaults, show first-run notice
3. If `.llm-lsp-cli.yaml` exists in CWD: merge into result
4. Return merged `ClientConfig`

### Merge Strategy

- **Shallow merge** for top-level keys (e.g., `timeout_seconds`, `trace_lsp`)
- **Deep merge** for nested dicts (e.g., `languages.python.command`)
- Lists are replaced, not concatenated

## Implementation

### New File: `config/merge.py`

```python
def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries. Override takes precedence."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

### Modified: `config/manager.py`

```python
@classmethod
def load(cls) -> ClientConfig:
    """Load configuration with layer merge: Defaults → Global → Project."""
    # 1. Start with defaults
    merged = dict(DEFAULT_CONFIG)

    # 2. Global config
    global_path = cls.get_config_dir() / "config.yaml"
    global_created_now = False
    if not global_path.exists():
        cls._create_default_global_config(global_path)
        global_created_now = True

    global_data = ConfigLoader.load(global_path, defaults={})
    merged = deep_merge(merged, global_data)

    # Show first-run notice only when config was just created
    if global_created_now:
        cls._show_first_run_notice()

    # 3. Project config (if exists in CWD)
    project_path = Path.cwd() / ".llm-lsp-cli.yaml"
    if project_path.exists():
        project_data = ConfigLoader.load(project_path, defaults={})
        merged = deep_merge(merged, project_data)

    return ClientConfig(**merged)

@classmethod
def _show_first_run_notice(cls) -> None:
    """Show first-run notice about config options."""
    typer.secho(
        "Created default config at ~/.config/llm-lsp-cli/config.yaml\n"
        "Create .llm-lsp-cli.yaml in your project to override settings.",
        fg=typer.colors.YELLOW
    )
```

### Modified: `commands/config.py`

```python
@app.command("init")
def config_init(
    project: bool = typer.Option(
        False,
        "--project",
        "-p",
        help="Create .llm-lsp-cli.yaml in current directory instead of global config",
    ),
) -> None:
    """Initialize configuration file.

    Creates either:
    - Global config: ~/.config/llm-lsp-cli/config.yaml (default)
    - Project config: ./.llm-lsp-cli.yaml (with --project)
    """
    if project:
        config_path = Path.cwd() / ".llm-lsp-cli.yaml"
        if config_path.exists():
            typer.echo(f"Project config already exists at: {config_path}")
            return
        config_path.write_text(
            yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
        )
        typer.echo(f"Created project config at: {config_path}")
    else:
        config_path = ConfigManager.get_config_dir() / "config.yaml"
        if config_path.exists():
            typer.echo(f"Configuration already exists at: {config_path}")
            return
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
        )
        typer.echo(f"Created default configuration at: {config_path}")
```

## Edge Cases & Error Handling

| Scenario | Behavior |
|----------|----------|
| Global config corrupted (invalid YAML) | Raise `ConfigError` with path and line number |
| Project config invalid YAML | Raise `ConfigError`, suggest fixing or deleting |
| Project config missing required fields | Pydantic validation error on load |
| Both configs empty | Use `DEFAULT_CONFIG` |
| Permission denied creating global config | Raise `ConfigError` with helpful message |

## Testing Strategy

### Unit Tests

| Test | Description |
|------|-------------|
| `test_load_defaults_only` | Load with no configs, returns DEFAULT_CONFIG |
| `test_load_global_creates_file` | Missing global config creates file and shows notice |
| `test_load_global_exists` | Existing global config is loaded |
| `test_load_project_overrides_global` | Project config overrides global values |
| `test_deep_merge_shallow` | Top-level keys replaced |
| `test_deep_merge_nested` | Nested dicts merged recursively |
| `test_config_init_project_flag` | `--project` creates `.llm-lsp-cli.yaml` |
| `test_invalid_yaml_error` | Corrupted YAML raises helpful error |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_first_uvx_run` | Simulate `uvx llm-lsp-cli lsp symbols` with clean home |
| `test_project_config_in_action` | Verify LSP server command overridden by project config |

## Decision Log

| Decision | Alternatives Considered | Why Chosen |
|----------|------------------------|------------|
| Config priority: Project > Global > Defaults | Project-only, Global-only, Merge both | Familiar pattern (Ruff/ESLint), flexible |
| Project config file: `.llm-lsp-cli.yaml` | `pyproject.toml [tool.llm-lsp-cli]` | Simpler parsing, language-agnostic, visible |
| Discovery: Current directory only | Walk up to root, walk to git root | Simpler, explicit, user controls location |
| Auto-create global config | Silent defaults, explicit init required | Zero friction for uvx users |
| Notice on first run | Silent, every run | Informative without being annoying |
| Deep merge strategy | Shallow merge, full replacement | Allows partial overrides at any level |
| `--project` flag for `config init` | Separate `config init-project` command | Keeps related functionality together |

## Example Usage

```bash
# First-time uvx user - auto-creates global config with notice
uvx llm-lsp-cli lsp symbols src/main.py

# Create project-local config
cd my-project
uvx llm-lsp-cli config init --project
# Edit .llm-lsp-cli.yaml to customize

# Project config overrides global
uvx llm-lsp-cli lsp symbols src/main.py
```
