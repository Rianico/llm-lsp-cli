"""Configuration schema definitions for llm-lsp-cli."""

from pydantic import BaseModel, ConfigDict, Field


class LanguageServerConfig(BaseModel):
    """Configuration for a specific language server."""

    model_config = ConfigDict(extra="allow")

    command: str = Field(..., description="Server executable command")
    args: list[str] = Field(default_factory=list, description="Command line arguments")
    initialize_params_file: str | None = Field(
        default=None, description="Path to initialize params JSON file"
    )
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")


class ClientConfig(BaseModel):
    """Main client configuration."""

    model_config = ConfigDict(extra="allow")

    # Daemon settings
    socket_path: str = Field(
        default="$XDG_RUNTIME_DIR/llm-lsp-cli/socket",
        description="UNIX socket path for CLI-daemon communication",
    )
    pid_file: str = Field(
        default="$XDG_RUNTIME_DIR/llm-lsp-cli/daemon.pid", description="PID file location"
    )
    log_file: str = Field(
        default="$XDG_STATE_HOME/llm-lsp-cli/daemon.log", description="Daemon log file"
    )

    # Language servers
    languages: dict[str, LanguageServerConfig] = Field(
        default_factory=dict, description="Language-specific server configurations"
    )

    # Global settings
    trace_lsp: bool = Field(default=False, description="Enable LSP communication tracing")
    timeout_seconds: int = Field(default=30, description="Default timeout for LSP requests")
