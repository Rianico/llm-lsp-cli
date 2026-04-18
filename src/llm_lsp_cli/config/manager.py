"""Configuration manager for llm-lsp-cli - facade for configuration operations."""

import shutil
from pathlib import Path
from typing import Any

import yaml

from llm_lsp_cli.infrastructure.config.loader import ConfigLoader
from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths

from .defaults import DEFAULT_CONFIG
from .initialize_params import build_initialize_params
from .path_builder import RuntimePathBuilder
from .schema import ClientConfig, LanguageServerConfig


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
    def get_runtime_base_dir(cls) -> Path:
        return RuntimePathBuilder.get_runtime_base_dir()

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
        """Build log file path."""
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
    def ensure_runtime_dir(cls) -> Path:
        return cls._get_xdg_paths().runtime_dir.parent

    @classmethod
    def ensure_project_dir(cls, workspace_path: str, base_dir: Path | None = None) -> Path:
        """Ensure project runtime directory exists."""
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir()
        subdir = RuntimePathBuilder()._build_workspace_subdir(workspace_path)
        project_dir = base_dir / subdir
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    @classmethod
    def ensure_config_dir(cls) -> Path:
        return cls.get_config_dir()

    @classmethod
    def ensure_state_dir(cls) -> Path:
        return cls.get_state_dir()

    @classmethod
    def load(cls) -> ClientConfig:
        """Load configuration from file."""
        paths = cls._get_xdg_paths()
        config_file = paths.config_dir / "config.yaml"
        if not config_file.exists():
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False))
            return ClientConfig(**DEFAULT_CONFIG)
        data = ConfigLoader.load(config_file, defaults={})
        return ClientConfig(**data)

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
        config_file.write_text(yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False))
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
        """Resolve server command for a language."""
        if cli_arg:
            return cli_arg, []
        lang_config = cls.get_language_config(language)
        if lang_config:
            resolved = shutil.which(lang_config.command)
            if resolved:
                return resolved, lang_config.args
        if language in DEFAULT_CONFIG["languages"]:
            defaults = DEFAULT_CONFIG["languages"][language]
            resolved = shutil.which(defaults["command"])
            if resolved:
                return resolved, defaults.get("args", [])
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
