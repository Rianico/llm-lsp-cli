"""Server registry for managing multiple LSP workspaces.

This module handles LSP response data.
Uses object for unknown data fields; specific types for known structures.
"""

import asyncio
from pathlib import Path

from llm_lsp_cli.config import ClientConfig, ConfigManager
from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
from llm_lsp_cli.infrastructure.config.exceptions import ServerNotFoundError
from llm_lsp_cli.infrastructure.config.path_resolver import ServerPathResolver

from .workspace import WorkspaceManager

# Pre-validated default config (cached for performance)
_DEFAULT_CLIENT_CONFIG: ClientConfig = ClientConfig.model_validate(DEFAULT_CONFIG)


class ServerRegistry:
    """Registry of LSP servers, one per workspace."""

    _workspaces: dict[str, WorkspaceManager]
    _global_lock: asyncio.Lock
    _config: ClientConfig | None  # Cached typed config
    _lsp_conf: str | None

    def __init__(self, lsp_conf: str | None = None):
        self._workspaces = {}
        self._global_lock = asyncio.Lock()
        self._config = None  # Cached config
        self._lsp_conf = lsp_conf

    @property
    def has_workspaces(self) -> bool:
        """Check if any workspaces are registered."""
        return bool(self._workspaces)

    def _load_config(self) -> ClientConfig:
        """Load configuration from file."""
        if self._config is None:
            try:
                self._config = ConfigManager.load()
            except Exception:
                # Use defaults if config can't be loaded
                self._config = _DEFAULT_CLIENT_CONFIG
        return self._config

    def _get_server_command(self, language: str) -> tuple[str, list[str]]:
        """Get server command for a language from config.

        Priority:
        1. Config file (languages.<lang>.command)
        2. Default from DEFAULT_CONFIG
        3. Raise FileNotFoundError

        Args:
            language: Language identifier (e.g., 'python', 'typescript')

        Returns:
            Tuple of (command, args)

        Raises:
            FileNotFoundError: If server command not found
        """
        config = self._load_config()

        # Try config file first
        lang_config = config.languages.get(language)
        if lang_config is not None:
            command = lang_config.command
            args = lang_config.args
            # Use ServerPathResolver for path resolution
            try:
                resolved = ServerPathResolver.resolve(command)
                return resolved, args
            except ServerNotFoundError as e:
                raise FileNotFoundError(str(e)) from e

        # Try default config
        default_lang_config = _DEFAULT_CLIENT_CONFIG.languages.get(language)
        if default_lang_config is not None:
            command = default_lang_config.command
            args = default_lang_config.args
            try:
                resolved = ServerPathResolver.resolve(command)
                return resolved, args
            except ServerNotFoundError as e:
                raise FileNotFoundError(str(e)) from e

        # Not found
        available = list(config.languages.keys())
        if not available:
            available = list(_DEFAULT_CLIENT_CONFIG.languages.keys())
        msg = (
            "Language server for '{}' not configured.\n"
            "Available languages: {}\n"
            "Please configure the language server in the config file."
        ).format(language, ", ".join(available))
        raise FileNotFoundError(msg)

    async def get_or_create_workspace(
        self,
        workspace_path: str,
        language: str | None = None,
    ) -> WorkspaceManager:
        """Get existing workspace or create new one."""
        import logging

        logger = logging.getLogger("llm_lsp_cli.server.registry")

        workspace_key = str(Path(workspace_path).resolve())
        existing = list(self._workspaces.keys())
        logger.debug(f"get_or_create_workspace: key={workspace_key}, existing={existing}")

        async with self._global_lock:
            if workspace_key not in self._workspaces:
                logger.debug(f"Creating new workspace: {workspace_key}")
                # Determine language (default to python)
                if language is None:
                    language = "python"

                # Get server command from config
                command, args = self._get_server_command(language)

                manager = WorkspaceManager(
                    workspace_path=workspace_path,
                    server_command=command,
                    server_args=args,
                    language_id=language,
                    lsp_conf=self._lsp_conf,
                    trace=True,  # Enable LSP tracing for debugging
                )
                self._workspaces[workspace_key] = manager
            else:
                logger.debug(f"Reusing existing workspace: {workspace_key}")

            return self._workspaces[workspace_key]

    async def request(
        self,
        workspace_path: str,
        method: str,
        params: dict[str, object],
    ) -> object:
        """Send a generic LSP request via the client.

        Args:
            workspace_path: Path to the workspace
            method: LSP method name (e.g., "textDocument/definition")
            params: LSP request parameters (already constructed by caller)

        Returns:
            Normalized response from the LSP server
        """
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request(method, params)

    async def shutdown_all(self) -> None:
        """Shutdown all workspaces."""
        async with self._global_lock:
            for workspace in self._workspaces.values():
                await workspace.shutdown()
            self._workspaces.clear()
