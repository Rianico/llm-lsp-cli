"""Configuration schema definitions for llm-lsp-cli."""

from pydantic import BaseModel, ConfigDict, Field


class LanguageServerConfig(BaseModel):
    """Configuration for a specific language server."""

    model_config = ConfigDict(extra="allow")

    command: str = Field(..., description="Server executable command")
    args: list[str] = Field(default_factory=list, description="Command line arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")


class LanguageTestFilterConfig(BaseModel):
    """Test filter configuration for a single language."""

    model_config = ConfigDict(extra="allow")

    directory_patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns for test directories",
    )
    suffix_patterns: list[str] = Field(
        default_factory=list,
        description="File suffix patterns",
    )
    prefix_patterns: list[str] = Field(
        default_factory=list,
        description="File prefix patterns",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="Negation patterns (explicitly include/exclude)",
    )
    enabled: bool = Field(default=True)


class TestFilterConfig(BaseModel):
    """Root test filter configuration with language-segmented groups."""

    model_config = ConfigDict(extra="allow")

    defaults: LanguageTestFilterConfig = Field(default_factory=LanguageTestFilterConfig)
    languages: dict[str, LanguageTestFilterConfig] = Field(default_factory=dict)
    fallback: LanguageTestFilterConfig | None = None


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

    # Test filter configuration
    test_filter: TestFilterConfig = Field(default_factory=TestFilterConfig)

    # Global settings
    trace_lsp: bool = Field(default=False, description="Enable LSP communication tracing")
    timeout_seconds: int = Field(default=30, description="Default timeout for LSP requests")
