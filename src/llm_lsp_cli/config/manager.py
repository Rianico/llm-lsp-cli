"""Configuration manager for llm-lsp-cli - facade for configuration operations."""

import warnings
from pathlib import Path
from typing import Any

import typer
import yaml

from llm_lsp_cli.infrastructure.config.exceptions import ConfigParseError
from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths
from llm_lsp_cli.utils.yaml_formatter import dump_config

from .defaults import DEFAULT_CONFIG
from .initialize_params import build_initialize_params
from .merge import deep_merge
from .path_builder import RuntimePathBuilder
from .schema import ClientConfig, LanguageServerConfig
from .server_validation import (
    ServerNotFoundError as ValidationServerError,
)
from .server_validation import validate_server_installed


class ConfigManager:
    """Manages configuration for llm-lsp-cli (facade pattern)."""

    LSP_SUBDIR = "llm-lsp-cli"
    CONFIG_FILE = "config.yaml"
    _path_builder = RuntimePathBuilder()

    @classmethod
    def _get_xdg_paths(cls) -> XdgPaths:
        return XdgPaths.get()

    @classmethod
    def get_config_dir(cls) -> Path:
        return cls._get_xdg_paths().config_dir

    @classmethod
    def get_state_dir(cls) -> Path:
        return cls._get_xdg_paths().state_dir

    @classmethod
    def get_runtime_dir(cls) -> Path:
        return cls._get_xdg_paths().runtime_dir

    @classmethod
    def get_runtime_base_dir(cls, workspace_path: str | None = None) -> Path:
        return RuntimePathBuilder.get_runtime_base_dir(workspace_path)

    @classmethod
    def build_socket_path(
        cls, workspace_path: str, language: str,
        base_dir: Path | None = None, lsp_server_name: str | None = None,
    ) -> Path:
        """Build socket file path."""
        return RuntimePathBuilder().build_socket_path(
            workspace_path, language, base_dir, lsp_server_name
        )

    @classmethod
    def build_pid_file_path(
        cls, workspace_path: str, language: str,
        base_dir: Path | None = None, lsp_server_name: str | None = None,
    ) -> Path:
        """Build PID file path."""
        return RuntimePathBuilder().build_pid_file_path(
            workspace_path, language, base_dir, lsp_server_name
        )

    @classmethod
    def build_log_file_path(
        cls, workspace_path: str, language: str,
        base_dir: Path | None = None, lsp_server_name: str | None = None,
    ) -> Path:
        """Build log file path.

        Deprecated: LSP server log files are no longer created separately.
        All LSP stderr output is now captured in daemon.log only.
        """
        warnings.warn(
            "build_log_file_path is deprecated. "
            "LSP server log files are no longer created separately. "
            "Use build_daemon_log_path instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return RuntimePathBuilder().build_log_file_path(
            workspace_path, language, base_dir, lsp_server_name
        )

    @classmethod
    def build_daemon_log_path(
        cls, workspace_path: str, language: str, base_dir: Path | None = None,
    ) -> Path:
        """Build daemon log file path."""
        return RuntimePathBuilder().build_daemon_log_path(
            workspace_path, language, base_dir
        )

    @classmethod
    def build_diagnostic_log_path(
        cls, workspace_path: str, language: str, base_dir: Path | None = None,
    ) -> Path:
        """Build diagnostic log file path."""
        return RuntimePathBuilder().build_diagnostic_log_path(
            workspace_path, language, base_dir
        )

    @classmethod
    def ensure_runtime_dir(cls) -> Path:
        """Ensure .llm-lsp-cli directory exists in current directory."""
        runtime_dir = Path.cwd() / ".llm-lsp-cli"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    @classmethod
    def ensure_config_dir(cls) -> Path:
        return cls.get_config_dir()

    @classmethod
    def ensure_state_dir(cls) -> Path:
        return cls.get_state_dir()

    @classmethod
    def load(cls) -> ClientConfig:
        """Load configuration with layer merge: Defaults -> Global -> Project."""
        # 1. Start with defaults
        merged = dict(DEFAULT_CONFIG)

        # 2. Global config (auto-create if missing)
        global_data, global_created_now = cls._load_global_config()
        merged = deep_merge(merged, global_data)

        # Show first-run notice only when config was just created
        if global_created_now:
            cls._show_first_run_notice()

        # 3. Project config (if exists in CWD)
        project_data = cls._load_project_config()
        if project_data:
            merged = deep_merge(merged, project_data)

        return ClientConfig(**merged)

    @classmethod
    def _load_global_config(cls) -> tuple[dict[str, Any], bool]:
        """Load global config, creating it if missing.

        Returns:
            Tuple of (config_data, was_just_created)
        """
        paths = cls._get_xdg_paths()
        global_path = paths.config_dir / "config.yaml"

        if not global_path.exists():
            global_path.parent.mkdir(parents=True, exist_ok=True)
            global_path.write_text(dump_config(DEFAULT_CONFIG))
            return ConfigLoader.load(global_path, defaults={}), True

        return ConfigLoader.load(global_path, defaults={}), False

    @classmethod
    def _load_project_config(cls) -> dict[str, Any] | None:
        """Load project config from CWD if it exists.

        Returns:
            Config dict if file exists and is valid, None otherwise.
            Raises ConfigParseError for invalid YAML.
        """
        project_path = Path.cwd() / ".llm-lsp-cli.yaml"
        if not project_path.exists():
            return None

        try:
            content = project_path.read_text()
            return yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            raise ConfigParseError(str(project_path), str(e)) from e

    @classmethod
    def _show_first_run_notice(cls) -> None:
        """Show first-run notice about config options.

        Only shows when stdout is a TTY (interactive terminal) to avoid
        polluting piped/programmatic output like JSON/YAML from config list.
        """
        import sys

        # Only show notice when stdout is a TTY (interactive terminal)
        if not sys.stdout.isatty():
            return

        typer.secho(
            "Created default config at ~/.config/llm-lsp-cli/config.yaml\n"
            "Create .llm-lsp-cli.yaml in your project to override settings.",
            fg=typer.colors.YELLOW,
        )

    @classmethod
    def save(cls, config: ClientConfig) -> None:
        """Save configuration to file."""
        paths = cls._get_xdg_paths()
        config_file = paths.config_dir / "config.yaml"
        ConfigLoader.save(config_file, config.model_dump(mode="json"))

    @classmethod
    def init_config(cls) -> bool:
        """Initialize configuration with defaults."""
        paths = cls._get_xdg_paths()
        config_file = paths.config_dir / "config.yaml"
        if config_file.exists():
            return False
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(dump_config(DEFAULT_CONFIG))
        return True

    @classmethod
    def get_language_config(cls, language: str) -> LanguageServerConfig | None:
        """Get language-specific server configuration."""
        config = cls.load()
        lang_config = config.languages.get(language)
        if lang_config is None:
            return None
        if language in DEFAULT_CONFIG["languages"]:
            defaults = DEFAULT_CONFIG["languages"][language]
            data = lang_config.model_dump()
            for key, value in defaults.items():
                if key not in data:
                    data[key] = value
            return LanguageServerConfig(**data)
        return lang_config

    @classmethod
    def resolve_server_command(
        cls, language: str, cli_arg: str | None = None
    ) -> tuple[str, list[str]]:
        """Resolve server command for a language.

        Args:
            language: Language identifier
            cli_arg: Optional CLI-override command

        Returns:
            Tuple of (resolved_executable_path, args_list)

        Raises:
            FileNotFoundError: If server executable cannot be resolved
        """
        if cli_arg:
            # CLI arg is treated as custom path
            try:
                resolved = validate_server_installed(cli_arg, is_custom_path=True)
                return resolved, []
            except ValidationServerError as e:
                raise FileNotFoundError(str(e)) from e

        lang_config = cls.get_language_config(language)
        if lang_config:
            try:
                resolved = validate_server_installed(
                    lang_config.command, language=language
                )
                return resolved, lang_config.args
            except ValidationServerError as e:
                raise FileNotFoundError(str(e)) from e

        # Fall back to defaults
        if language in DEFAULT_CONFIG["languages"]:
            defaults = DEFAULT_CONFIG["languages"][language]
            try:
                resolved = validate_server_installed(
                    defaults["command"], language=language
                )
                return resolved, defaults.get("args", [])
            except ValidationServerError as e:
                raise FileNotFoundError(str(e)) from e

        raise FileNotFoundError(
            f"Language server for '{language}' not found.\n"
            f"Please install the appropriate language server and ensure it's in PATH,\n"
            f"or specify --lang-server-path to provide a custom path."
        )

    @classmethod
    def load_initialize_params(
        cls,
        server_command: str,
        workspace_path: str,
        custom_conf_path: str | None = None,
    ) -> dict[str, Any]:
        """Load LSP initialize parameters.

        Delegates to build_initialize_params for dynamic parameter generation.

        Args:
            server_command: The server command to execute
            workspace_path: The workspace directory path
            custom_conf_path: Deprecated, kept for API compatibility

        Returns:
            Dictionary containing initialize parameters for the LSP server.
        """
        return build_initialize_params(
            server_command,
            workspace_path,
            custom_conf_path,
        )

    @classmethod
    def get_lsp_server_name(cls, language: str) -> str:
        """Get LSP server name for a language."""
        return RuntimePathBuilder()._get_lsp_server_name(language)
