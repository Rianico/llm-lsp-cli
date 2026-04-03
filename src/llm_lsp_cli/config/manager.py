"""Configuration manager for llm-lsp-cli.
Handles loading, saving, and validating configuration from XDG directories.
"""

import contextlib
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, cast

from .defaults import DEFAULT_CONFIG
from .schema import ClientConfig, LanguageServerConfig

# Private module-level XDG directories with fallback chains
# Initialized at module load time with existence and permission validation
# Type: ignore is used because pyright doesn't understand module-level init
_XDG_CONFIG_HOME: Path = None  # type: ignore
_XDG_STATE_HOME: Path = None  # type: ignore
_XDG_RUNTIME_DIR: Path = None  # type: ignore


def _resolve_config_home() -> Path:
    """Resolve XDG_CONFIG_HOME with fallback."""
    env_val = os.environ.get("XDG_CONFIG_HOME")
    if env_val:
        return Path(env_val)
    return Path.home() / ".config"


def _resolve_state_home() -> Path:
    """Resolve XDG_STATE_HOME with fallback."""
    env_val = os.environ.get("XDG_STATE_HOME")
    if env_val:
        return Path(env_val)
    return Path.home() / ".local" / "state"


def _resolve_runtime_dir() -> Path:
    """Resolve XDG_RUNTIME_DIR with fallback chain.

    Fallback chain:
    1. $XDG_RUNTIME_DIR
    2. $TMPDIR
    3. /tmp
    """
    env_val = os.environ.get("XDG_RUNTIME_DIR")
    if env_val:
        return Path(env_val)

    env_val = os.environ.get("TMPDIR")
    if env_val:
        return Path(env_val)

    return Path("/tmp")


def _ensure_directory_with_permissions(path: Path, mode: int = 0o700) -> bool:
    """Ensure directory exists with specified permissions.

    Args:
        path: Directory path to create/validate
        mode: Permission mode (default 0o700)

    Returns:
        bool: True if successful, False if permission denied
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(mode)
        return True
    except (OSError, PermissionError):
        return path.exists()


def _initialize_xdg_directories() -> None:
    """Initialize XDG directories at module load time.

    Validates existence and sets permissions for each directory.
    Stores results in private module-level variables.
    """
    global _XDG_CONFIG_HOME, _XDG_STATE_HOME, _XDG_RUNTIME_DIR

    # Resolve and initialize config home
    _XDG_CONFIG_HOME = _resolve_config_home()
    _ensure_directory_with_permissions(_XDG_CONFIG_HOME / "llm-lsp-cli")

    # Resolve and initialize state home
    _XDG_STATE_HOME = _resolve_state_home()
    _ensure_directory_with_permissions(_XDG_STATE_HOME / "llm-lsp-cli")

    # Resolve and initialize runtime dir
    _XDG_RUNTIME_DIR = _resolve_runtime_dir()
    _ensure_directory_with_permissions(_XDG_RUNTIME_DIR / "llm-lsp-cli")


# Module-level initialization - runs once at import time
_initialize_xdg_directories()


class ConfigManager:
    """Manages configuration for llm-lsp-cli."""

    # Configuration paths (built from private module variables)
    CONFIG_DIR = _XDG_CONFIG_HOME / "llm-lsp-cli"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the config directory."""
        return _XDG_CONFIG_HOME / "llm-lsp-cli"

    @classmethod
    def get_state_dir(cls) -> Path:
        """Get the state directory."""
        return _XDG_STATE_HOME / "llm-lsp-cli"

    @classmethod
    def get_runtime_dir(cls) -> Path:
        """Get the runtime directory."""
        return _XDG_RUNTIME_DIR

    @classmethod
    def get_runtime_base_dir(cls) -> Path:
        """Get the runtime base directory (not llm-lsp-cli subdirectory)."""
        return _XDG_RUNTIME_DIR

    @classmethod
    def _sanitize_workspace_name(cls, name: str) -> str:
        """Sanitize project name for use in file paths.

        Removes or replaces unsafe characters to prevent path traversal
        and ensure filesystem compatibility.

        Args:
            name: Raw project name (e.g., directory name)

        Returns:
            str: Sanitized name with only alphanumeric and underscore
        """
        result = name
        result = re.sub(r"[\\/]", "_", result)
        result = re.sub(r"\.\.", "_", result)
        result = re.sub(r"[^a-zA-Z0-9_-]", "_", result)
        result = re.sub(r"_+", "_", result)
        result = result.strip("_")
        return result.lower() if result else "unknown"

    @classmethod
    def _generate_workspace_hash(cls, project_path: str) -> str:
        """Generate a short hash for a project path.

        Uses MD5 for consistent hashing, returns first 4 alphanumeric chars.

        Args:
            project_path: Absolute path to the project

        Returns:
            str: 4-character alphanumeric hash
        """
        abs_path = str(Path(project_path).resolve())
        hash_obj = hashlib.md5(abs_path.encode("utf-8"))
        return hash_obj.hexdigest()[:4]

    @classmethod
    def _get_lsp_server_name(cls, language: str) -> str:
        """Get the LSP server name for a language.

        Resolves the server command name from configuration or defaults.
        Uses the base command name (without path) for file naming.

        Args:
            language: Language identifier (e.g., "python", "typescript")

        Returns:
            str: Server name (e.g., "pyright", "pylsp", "typescript-language-server")
        """
        lang_config = cls.get_language_config(language)
        if lang_config:
            command = lang_config.command
            # Extract base name from path (e.g., "/usr/bin/pyright" -> "pyright")
            return Path(command).name

        # Fallback to default config
        if language in DEFAULT_CONFIG["languages"]:
            command = DEFAULT_CONFIG["languages"][language]["command"]
            return Path(command).name

        # Final fallback to language name
        return language

    @classmethod
    def build_socket_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build isolated socket path for a workspace and language.

        Structure: ${BASE_DIR}/llm-lsp-cli/{workspace_name}-{workspace_hash}/{lsp_server_name}.sock

        Args:
            workspace_path: Path to the workspace root
            language: Language identifier (e.g., "python", "typescript")
            base_dir: Optional base directory (uses get_runtime_base_dir() if not provided)
            lsp_server_name: Optional LSP server name (auto-resolved from language if not provided)

        Returns:
            Path: Full socket file path
        """
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir()

        workspace = Path(workspace_path).resolve()
        workspace_name = cls._sanitize_workspace_name(workspace.name)
        workspace_hash = cls._generate_workspace_hash(str(workspace))

        # Resolve server name if not provided
        if lsp_server_name is None:
            lsp_server_name = cls._get_lsp_server_name(language)

        llm_lsp_dir = base_dir / "llm-lsp-cli"
        project_dir = llm_lsp_dir / f"{workspace_name}-{workspace_hash}"
        socket_file = project_dir / f"{lsp_server_name}.sock"

        return socket_file

    @classmethod
    def build_pid_file_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build isolated PID file path for a workspace and language.

        Structure: ${BASE_DIR}/llm-lsp-cli/{workspace_name}-{workspace_hash}/{lsp_server_name}.pid

        Args:
            workspace_path: Path to the workspace root
            language: Language identifier
            base_dir: Optional base directory
            lsp_server_name: Optional LSP server name (auto-resolved from language if not provided)

        Returns:
            Path: Full PID file path
        """
        socket_path = cls.build_socket_path(workspace_path, language, base_dir, lsp_server_name)
        return socket_path.with_suffix(".pid")

    @classmethod
    def build_log_file_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build isolated log file path for a workspace and language.

        Structure: ${BASE_DIR}/llm-lsp-cli/{workspace_name}-{workspace_hash}/{lsp_server_name}.log

        Args:
            workspace_path: Path to the workspace root
            language: Language identifier
            base_dir: Optional base directory
            lsp_server_name: Optional LSP server name (auto-resolved from language if not provided)

        Returns:
            Path: Full log file path
        """
        socket_path = cls.build_socket_path(workspace_path, language, base_dir, lsp_server_name)
        return socket_path.with_suffix(".log")

    @classmethod
    def build_daemon_log_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
    ) -> Path:
        """Build isolated daemon log file path for a workspace.

        Structure: ${BASE_DIR}/llm-lsp-cli/{workspace_name}-{workspace_hash}/daemon.log

        Args:
            workspace_path: Path to the workspace root
            language: Language identifier (used to determine project directory)
            base_dir: Optional base directory (uses get_runtime_base_dir() if not provided)

        Returns:
            Path: Full daemon log file path
        """
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir()

        workspace = Path(workspace_path).resolve()
        workspace_name = cls._sanitize_workspace_name(workspace.name)
        workspace_hash = cls._generate_workspace_hash(str(workspace))

        llm_lsp_dir = base_dir / "llm-lsp-cli"
        project_dir = llm_lsp_dir / f"{workspace_name}-{workspace_hash}"
        daemon_log = project_dir / "daemon.log"

        return daemon_log

    @classmethod
    def ensure_runtime_dir(cls) -> Path:
        """Ensure runtime directory exists with proper permissions.

        Creates the base runtime directory with 0o700 permissions (owner rwx only).

        Returns:
            Path: Runtime directory path
        """
        runtime_dir = cls.get_runtime_base_dir()
        runtime_dir.mkdir(parents=True, exist_ok=True)

        with contextlib.suppress(OSError):
            runtime_dir.chmod(0o700)

        llm_lsp_dir = runtime_dir / "llm-lsp-cli"
        llm_lsp_dir.mkdir(parents=True, exist_ok=True)

        with contextlib.suppress(OSError):
            llm_lsp_dir.chmod(0o700)

        return runtime_dir

    @classmethod
    def ensure_project_dir(
        cls,
        workspace_path: str,
        base_dir: Path | None = None,
    ) -> Path:
        """Ensure project-specific directory exists with proper permissions.

        Creates the project directory with 0o700 permissions.

        Args:
            workspace_path: Path to the workspace root
            base_dir: Optional base directory (uses get_runtime_base_dir() if not provided)

        Returns:
            Path: Project directory path
        """
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir()

        workspace = Path(workspace_path).resolve()
        workspace_name = cls._sanitize_workspace_name(workspace.name)
        workspace_hash = cls._generate_workspace_hash(str(workspace))

        llm_lsp_dir = base_dir / "llm-lsp-cli"
        project_dir = llm_lsp_dir / f"{workspace_name}-{workspace_hash}"
        project_dir.mkdir(parents=True, exist_ok=True)

        with contextlib.suppress(OSError):
            project_dir.chmod(0o700)

        return project_dir

    @classmethod
    def ensure_config_dir(cls) -> Path:
        """Ensure config directory exists."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return cls.CONFIG_DIR

    @classmethod
    def ensure_state_dir(cls) -> Path:
        """Ensure state directory exists."""
        state_dir = cls.get_state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    @classmethod
    def load(cls) -> ClientConfig:
        """Load configuration from file.

        Returns:
            ClientConfig: Loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist and can't be created
            json.JSONDecodeError: If config file is invalid JSON
            pydantic.ValidationError: If config doesn't match schema
        """
        if not cls.CONFIG_FILE.exists():
            cls.ensure_config_dir()
            cls.CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
            return ClientConfig(**DEFAULT_CONFIG)

        data = json.loads(cls.CONFIG_FILE.read_text())
        data = cls._expand_env(data)

        return ClientConfig(**data)

    @classmethod
    def save(cls, config: ClientConfig) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save
        """
        cls.ensure_config_dir()
        data = config.model_dump(mode="json")
        cls.CONFIG_FILE.write_text(json.dumps(data, indent=2))

    @classmethod
    def _init_capabilities(cls) -> None:
        """Initialize capabilities directory with default files."""
        import shutil
        from importlib import resources

        cap_dir = cls.CONFIG_DIR / "capabilities"
        cap_dir.mkdir(parents=True, exist_ok=True)

        # We need to copy from our package's capabilities dir to XDG_CONFIG_HOME
        try:
            # For Python 3.9+ resources API
            try:
                import llm_lsp_cli.config.capabilities as caps_pkg
                for r in resources.files(caps_pkg).iterdir():
                    if r.is_file() and r.name.endswith(".json"):
                        dest_file = cap_dir / r.name
                        if not dest_file.exists():
                            with resources.as_file(r) as src_file:
                                shutil.copy2(src_file, dest_file)
            except ImportError:
                # Fallback if package structure is different during tests
                src_dir = Path(__file__).parent / "capabilities"
                if src_dir.exists():
                    for src_file in src_dir.glob("*.json"):
                        dest_file = cap_dir / src_file.name
                        if not dest_file.exists():
                            shutil.copy2(src_file, dest_file)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to copy capabilities configs: {e}")

    @classmethod
    def init_config(cls) -> bool:
        """Initialize configuration with defaults.

        Returns:
            bool: True if config was created, False if it already existed
        """
        cls.ensure_config_dir()
        cls._init_capabilities()

        if cls.CONFIG_FILE.exists():
            return False

        cls.CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return True

    @classmethod
    def _expand_env(cls, data: dict[str, Any]) -> dict[str, Any]:
        from typing import cast
        """Expand environment variables in string values.

        Handles $VAR and ${VAR} patterns.

        Args:
            data: Dictionary to process

        Returns:
            dict: Dictionary with environment variables expanded
        """

        def expand_value(v: Any) -> Any:
            if isinstance(v, str):

                def replace_env(match: re.Match[str]) -> str:
                    var_name = match.group(1) or match.group(2)
                    return os.environ.get(var_name) or match.group(0)

                expanded = re.sub(r"\$\{([^}]+)\}|\$(\w+)", replace_env, v)
                return expanded
            elif isinstance(v, dict):
                return {k: expand_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [expand_value(item) for item in v]
            return v

        return cast(dict[str, Any], expand_value(data))

    @classmethod
    def load_initialize_params(
        cls,
        server_command: str,
        workspace_path: str,
        custom_conf_path: str | None = None
    ) -> dict[str, Any]:
        """Load and process LSP initialization capabilities configuration.

        Args:
            server_command: The executable path or name of the LSP server
            workspace_path: The absolute path to the workspace root
            custom_conf_path: Optional explicit capabilities config path

        Returns:
            dict: The processed initialization parameters
        """
        if custom_conf_path:
            conf_file = Path(custom_conf_path)
            if not conf_file.exists():
                raise FileNotFoundError(f"Custom LSP config not found: {custom_conf_path}")
        else:
            server_name = Path(server_command).name
            cap_dir = cls.CONFIG_DIR / "capabilities"
            conf_file = cap_dir / f"{server_name}.json"

            if not conf_file.exists():
                # Fallback to default.json
                conf_file = cap_dir / "default.json"
                if not conf_file.exists():
                    # If capabilities weren't scaffolded, scaffold them now
                    cls._init_capabilities()
                    if not conf_file.exists():
                        raise FileNotFoundError("Default LSP capabilities config not found.")

        # Read JSON
        try:
            content = conf_file.read_text()
        except Exception as e:
            raise OSError(f"Failed to read LSP config {conf_file}: {e}") from e

        # Process template substitutions
        workspace_p = Path(workspace_path).resolve()
        workspace_uri = workspace_p.as_uri()
        workspace_name = workspace_p.name

        # Standard replacements
        content = content.replace("$rootUri", workspace_uri)
        content = content.replace("$uri", workspace_uri)
        content = content.replace("$rootPath", str(workspace_p))
        content = content.replace("$name", workspace_name)

        # Process PID replacement (os.getpid() as unquoted integer if possible)
        # Handle cases where it's a string: "os.getpid()"
        pid = str(os.getpid())
        content = content.replace('"os.getpid()"', pid)
        # Also handle potential unquoted usages in case someone got creative
        content = content.replace('os.getpid()', pid)

        # Parse JSON
        try:
            params = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {conf_file}: {e}") from e

        return cast(dict[str, Any], params)

    @classmethod
    def get_language_config(cls, language: str) -> LanguageServerConfig | None:
        """Get configuration for a specific language.

        Args:
            language: Language identifier (e.g., 'python', 'typescript')

        Returns:
            LanguageServerConfig or None if not configured
        """
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
        """Resolve language server command with priority.

        Priority:
        1. CLI argument (--lang-server-path)
        2. Config file (languages.<lang>.command)
        3. Default from DEFAULT_CONFIG
        4. Raise FileNotFoundError

        Args:
            language: Language identifier
            cli_arg: Optional CLI override

        Returns:
            tuple: (command, args)

        Raises:
            FileNotFoundError: If server command not found
        """
        import shutil

        if cli_arg:
            return cli_arg, []

        lang_config = cls.get_language_config(language)
        if lang_config:
            command = lang_config.command
            args = lang_config.args

            resolved = shutil.which(command)
            if resolved:
                return resolved, args

        if language in DEFAULT_CONFIG["languages"]:
            defaults = DEFAULT_CONFIG["languages"][language]
            command = defaults["command"]
            args = defaults.get("args", [])

            resolved = shutil.which(command)
            if resolved:
                return resolved, args

        raise FileNotFoundError(
            f"Language server for '{language}' not found.\n"
            f"Please install the appropriate language server and ensure it's in PATH,\n"
            f"or specify --lang-server-path to provide a custom path."
        )
