# pyright: reportAny=false
"""Path building utilities for llm-lsp-cli runtime files.

This module handles LSP response data (dict[str, Any]).
LSP responses are inherently dynamic, so Any is used for dict value types.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from llm_lsp_cli.config.defaults import DEFAULT_CONFIG


class RuntimePathBuilder:
    """Builds runtime file paths for LSP servers.

    Handles construction of socket, PID, log, and daemon log file paths
    using a flat directory structure under .llm-lsp-cli/.
    """

    @staticmethod
    def get_runtime_base_dir(workspace_path: str | None = None) -> Path:
        """Get base runtime directory.

        Args:
            workspace_path: Optional workspace path. If None, uses current working directory.

        Returns:
            Path to the .llm-lsp-cli directory.
        """
        if workspace_path is None:
            return Path.cwd() / ".llm-lsp-cli"
        return Path(workspace_path).resolve() / ".llm-lsp-cli"

    @staticmethod
    def _get_lsp_server_name(language: str) -> str:
        """Get LSP server name for a language from defaults only.

        Args:
            language: Language identifier (e.g., 'python', 'typescript').

        Returns:
            Server command name extracted from defaults.

        Note:
            For config-based server name resolution, pass lsp_server_name
            parameter to build_* methods or use ConfigManager.get_lsp_server_name().
        """
        # Only use defaults to avoid import cycle with ConfigManager
        if language in DEFAULT_CONFIG["languages"]:
            return Path(DEFAULT_CONFIG["languages"][language]["command"]).name
        return language

    @classmethod
    def build_socket_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build socket file path.

        Args:
            workspace_path: Workspace directory path.
            language: Language identifier.
            base_dir: Optional base directory override.
            lsp_server_name: Optional server name override.

        Returns:
            Path to the socket file.
        """
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir(workspace_path)
        if lsp_server_name is None:
            lsp_server_name = cls._get_lsp_server_name(language)
        return base_dir / f"{lsp_server_name}.sock"

    @classmethod
    def build_pid_file_path(
        cls,
        workspace_path: str,
        language: str,
        base_dir: Path | None = None,
        lsp_server_name: str | None = None,
    ) -> Path:
        """Build PID file path.

        Args:
            workspace_path: Workspace directory path.
            language: Language identifier.
            base_dir: Optional base directory override.
            lsp_server_name: Optional server name override.

        Returns:
            Path to the PID file.
        """
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
        """Build log file path.

        Deprecated: LSP server log files are no longer created separately.
        All LSP stderr output is now captured in daemon.log only.

        Returns:
            Path to the log file (deprecated).
        """
        warnings.warn(
            "build_log_file_path is deprecated. "
            "LSP server log files are no longer created separately. "
            "Use build_daemon_log_path instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.build_socket_path(
            workspace_path, language, base_dir, lsp_server_name
        ).with_suffix(".log")

    @classmethod
    def build_daemon_log_path(
        cls,
        workspace_path: str,
        language: str,  # pyright: ignore[reportUnusedParameter]
        base_dir: Path | None = None,
    ) -> Path:
        """Build daemon log file path.

        Args:
            workspace_path: Workspace directory path.
            language: Language identifier.
            base_dir: Optional base directory override.

        Returns:
            Path to the daemon log file.
        """
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir(workspace_path)
        return base_dir / "daemon.log"

    @classmethod
    def build_diagnostic_log_path(
        cls,
        workspace_path: str,
        language: str,  # pyright: ignore[reportUnusedParameter]
        base_dir: Path | None = None,
    ) -> Path:
        """Build diagnostic log file path.

        Args:
            workspace_path: Workspace directory path.
            language: Language identifier.
            base_dir: Optional base directory override.

        Returns:
            Path to the diagnostic log file.
        """
        if base_dir is None:
            base_dir = cls.get_runtime_base_dir(workspace_path)
        return base_dir / "diagnostics.log"
