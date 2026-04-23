"""Server registry for managing multiple LSP workspaces."""

import asyncio
from pathlib import Path
from typing import Any

from llm_lsp_cli.config import ConfigManager
from llm_lsp_cli.config.defaults import DEFAULT_CONFIG
from llm_lsp_cli.infrastructure.config.exceptions import ServerNotFoundError
from llm_lsp_cli.infrastructure.config.path_resolver import ServerPathResolver

from .workspace import WorkspaceManager


class ServerRegistry:
    """Registry of LSP servers, one per workspace."""

    def __init__(self, lsp_conf: str | None = None):
        self._workspaces: dict[str, WorkspaceManager] = {}
        self._global_lock = asyncio.Lock()
        self._config: dict[str, Any] | None = None  # Cached config
        self._lsp_conf = lsp_conf

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file."""
        if self._config is None:
            try:
                loaded = ConfigManager.load().model_dump(mode="json")
                self._config = loaded if loaded is not None else DEFAULT_CONFIG
            except Exception:
                # Use defaults if config can't be loaded
                self._config = DEFAULT_CONFIG
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
        languages = config.get("languages", {})

        # Try config file first
        if language in languages:
            lang_config = languages[language]
            command = lang_config.get("command")
            args = lang_config.get("args", [])

            if command:
                # Use ServerPathResolver for path resolution
                try:
                    resolved = ServerPathResolver.resolve(command)
                    return resolved, args
                except ServerNotFoundError as e:
                    raise FileNotFoundError(str(e)) from e

        # Try default config
        if language in DEFAULT_CONFIG.get("languages", {}):
            defaults = DEFAULT_CONFIG["languages"][language]
            command = defaults["command"]
            args = defaults.get("args", [])

            try:
                resolved = ServerPathResolver.resolve(command)
                return resolved, args
            except ServerNotFoundError as e:
                raise FileNotFoundError(str(e)) from e

        # Not found
        available = list(languages.keys()) or list(DEFAULT_CONFIG.get("languages", {}).keys())
        raise FileNotFoundError(
            f"Language server for '{language}' not configured.\n"
            f"Available languages: {', '.join(available)}\n"
            f"Please configure the language server in the config file."
        )

    async def get_or_create_workspace(
        self,
        workspace_path: str,
        language: str | None = None,
    ) -> WorkspaceManager:
        """Get existing workspace or create new one."""
        import logging

        logger = logging.getLogger("llm_lsp_cli.server.registry")

        workspace_key = str(Path(workspace_path).resolve())
        logger.debug(
            f"get_or_create_workspace: key={workspace_key}, "
            f"existing={list(self._workspaces.keys())}"
        )

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

    async def request_definition(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> list[Any]:
        """Request definition at position."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_definition(file_path, line, column)

    async def request_references(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> list[Any]:
        """Request references at position."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_references(file_path, line, column)

    async def request_completions(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> list[Any]:
        """Request completions at position."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_completions(file_path, line, column)

    async def request_hover(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> Any:
        """Request hover at position."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_hover(file_path, line, column)

    async def request_document_symbols(
        self,
        workspace_path: str,
        file_path: str,
    ) -> list[Any]:
        """Request document symbols."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_document_symbols(file_path)

    async def request_workspace_symbols(
        self,
        workspace_path: str,
        query: str,
    ) -> list[Any]:
        """Request workspace symbols."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_workspace_symbols(query)

    async def request_diagnostics(
        self,
        workspace_path: str,
        file_path: str,
    ) -> list[Any]:
        """Request diagnostics for a single document."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_diagnostics(file_path)

    async def request_workspace_diagnostics(
        self,
        workspace_path: str,
    ) -> list[Any]:
        """Request diagnostics for entire workspace."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_workspace_diagnostics()

    async def request_call_hierarchy_incoming(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> list[Any]:
        """Request incoming calls at position."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_call_hierarchy_incoming(file_path, line, column)

    async def request_call_hierarchy_outgoing(
        self,
        workspace_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> list[Any]:
        """Request outgoing calls at position."""
        workspace = await self.get_or_create_workspace(workspace_path)
        client = await workspace.ensure_initialized()
        return await client.request_call_hierarchy_outgoing(file_path, line, column)

    async def shutdown_all(self) -> None:
        """Shutdown all workspaces."""
        async with self._global_lock:
            for workspace in self._workspaces.values():
                await workspace.shutdown()
            self._workspaces.clear()
