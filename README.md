# llm-lsp-cli

A command-line tool for interacting with Language Server Protocol servers, providing code intelligence features from the terminal.

## Architecture

This tool consists of two main components:
1.  **A long-running daemon process**: Manages language server subprocesses, one for each project workspace.
2.  **A CLI client**: A user-facing tool (built with Typer) that communicates with the daemon via a UNIX socket.

This architecture ensures that the language server for a project remains running, providing fast responses without the delay of starting a new server for each command.

## Features

- **Code Navigation**: Get definitions (`definition`) and find references (`references`).
- **Code Analysis**: Get hover information (`hover`), list document symbols (`document-symbols`), and search for workspace symbols (`workspace-symbol`).
- **Completions**: Get code completions (`completions`).
- **Daemon Management**: Control the background daemon with `start`, `stop`, `restart`, and `status` commands.

## Configuration

Configuration files are located in `$XDG_CONFIG_HOME/llm-lsp-cli/` (usually `~/.config/llm-lsp-cli/`).

1.  **`config.json`**: Main configuration file.
    ```json
    {
      "servers": {
        "python": {
          "langServerPath": "/path/to/your/pylsp",
          "langServerArgs": ["--arg1"]
        }
      }
    }
    ```

2.  **`initialize_params_<language>.json`**: LSP `initialize` request parameters.
    Example for `pylsp`: `initialize_params_python.json`
    ```json
    {
        "processId": null,
        "capabilities": {},
        "trace": "off"
    }
    ```

### Language Server Discovery

The CLI finds the language server executable in the following order:
1.  The `--lang-server-path` CLI argument (to be added).
2.  The `langServerPath` field in `config.json`.
3.  An executable in the system's `PATH` (e.g., `pylsp`, `typescript-language-server`).

## Usage

First, start the daemon:
```bash
llm-lsp-cli daemon start
```

Then, you can use the commands in your project directory:
```bash
# Get definition of a symbol
llm-lsp-cli definition src/main.py:42:15 --workspace-root .

# Find references
llm-lsp-cli references src/utils.py:10:8

# Get completions
llm-lsp-cli completions src/main.py:50:5
```

Check the daemon status:
```bash
llm-lsp-cli daemon status
```

Stop the daemon when you're done:
```bash
llm-lsp-cli daemon stop
```
