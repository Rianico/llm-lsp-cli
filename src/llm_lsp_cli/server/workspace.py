"""Workspace manager for LSP servers."""

import asyncio
from pathlib import Path

from llm_lsp_cli.lsp.client import LSPClient


class WorkspaceManager:
    """Manages a single workspace and its LSP client."""

    def __init__(
        self,
        workspace_path: str,
        server_command: str,
        server_args: list[str] | None = None,
        language_id: str = "python",
        trace: bool = False,
        timeout: float = 30.0,
        lsp_conf: str | None = None,
        log_file: Path | None = None,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.server_command = server_command
        self.server_args = server_args or []
        self.language_id = language_id
        self.trace = trace
        self.timeout = timeout
        self.lsp_conf = lsp_conf
        self.log_file = log_file

        self._client: LSPClient | None = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def ensure_initialized(self) -> LSPClient:
        """Ensure the LSP client is initialized."""
        async with self._lock:
            if not self._initialized:
                self._client = LSPClient(
                    workspace_path=str(self.workspace_path),
                    server_command=self.server_command,
                    server_args=self.server_args,
                    language_id=self.language_id,
                    trace=self.trace,
                    timeout=self.timeout,
                    lsp_conf=self.lsp_conf,
                    log_file=self.log_file,
                )
                await self._client.initialize()
                self._initialized = True

            assert self._client is not None
            return self._client

    async def shutdown(self) -> None:
        """Shutdown the workspace LSP client."""
        async with self._lock:
            if self._client and self._initialized:
                await self._client.shutdown()
                self._client = None
                self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if workspace is initialized."""
        return self._initialized
