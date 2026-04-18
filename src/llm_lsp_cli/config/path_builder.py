"""Path building utilities for llm-lsp-cli runtime files."""

import hashlib
import re
from pathlib import Path

from llm_lsp_cli.infrastructure.config.xdg_paths import XdgPaths


class RuntimePathBuilder:
    """Builds runtime file paths for LSP servers.

    Handles construction of socket, PID, log, and daemon log file paths
    using a consistent workspace-based directory structure.
    """

    @classmethod
    def build_socket_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build socket file path."""
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir()
        if lsp_server_name is None:
            lsp_server_name = cls._get_lsp_server_name(language)
        subdir = cls._build_workspace_subdir(workspace_path)
        return base_dir / subdir / f"{lsp_server_name}.sock"

    @classmethod
    def build_pid_file_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build PID file path."""
        return cls.build_socket_path(
            workspace_path, language, base_dir, lsp_server_name
        ).with_suffix(".pid")

    @classmethod
    def build_log_file_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build log file path."""
        return cls.build_socket_path(
            workspace_path, language, base_dir, lsp_server_name
        ).with_suffix(".log")

    @classmethod
    def build_daemon_log_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
    ) -> Path:
        """Build daemon log file path."""
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir()
        subdir = cls._build_workspace_subdir(workspace_path)
        return base_dir / subdir / "daemon.log"

    @classmethod
    def get_runtime_base_dir(cls) -> Path:
        """Get base runtime directory."""
        paths = XdgPaths.get()
        lsp_subdir = "llm-lsp-cli"
        return Path(str(paths.runtime_dir).removesuffix(f"/{lsp_subdir}"))

    @classmethod
    def _sanitize_workspace_name(cls, name: str) -> str:
        """Sanitize workspace name for file paths."""
        result = re.sub(r"[\\/]", "_", name)
        result = re.sub(r"\.\.", "_", result)
        result = re.sub(r"[^a-zA-Z0-9_-]", "_", result)
        result = re.sub(r"_+", "_", result)
        return result.lower().strip("_") if result else "unknown"

    @classmethod
    def _generate_workspace_hash(cls, project_path: str) -> str:
        """Generate short hash for workspace path."""
        return hashlib.md5(str(Path(project_path).resolve()).encode()).hexdigest()[:4]

    @classmethod
    def _build_workspace_subdir(cls, workspace_path: str) -> Path:
        """Build workspace subdirectory path."""
        workspace = Path(workspace_path).resolve()
        name = cls._sanitize_workspace_name(workspace.name)
        hash_val = cls._generate_workspace_hash(str(workspace))
        lsp_subdir = "llm-lsp-cli"
        return Path(lsp_subdir) / f"{name}-{hash_val}"

    @classmethod
    def _get_lsp_server_name(cls, language: str) -> str:
        """Get LSP server name for a language."""
        # Lazy import to avoid circular dependency
        from llm_lsp_cli.config.manager import ConfigManager

        try:
            lang_config = ConfigManager.get_language_config(language)
            if lang_config:
                return Path(lang_config.command).name
        except Exception:
            pass

        from llm_lsp_cli.config.defaults import DEFAULT_CONFIG

        if language in DEFAULT_CONFIG["languages"]:
            return Path(DEFAULT_CONFIG["languages"][language]["command"]).name
        return language
