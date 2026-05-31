"""Document synchronization context for daemon LSP operations."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_lsp_cli.lsp.client import LSPClient


class DocumentSyncContext:
    """Async context manager for document synchronization within daemon.

    This context manager handles the didOpen phase for a single file.
    Per ADR-0008, files remain open for the session lifetime:
    - didOpen is sent when entering the context
    - didClose is NOT sent when exiting (file stays open for session)
    - The file URI is returned for use in subsequent requests

    Usage:
        async with DocumentSyncContext(lsp_client, file_path) as uri:
            # Use uri for LSP requests
            result = await lsp_client.request_diagnostics(uri)
        # File remains open - no didClose sent
    """

    lsp_client: LSPClient
    file_path: Path

    def __init__(self, lsp_client: LSPClient, file_path: Path):
        """
        Initialize document sync context.

        Args:
            lsp_client: LSPClient instance
            file_path: Path to the file to synchronize
        """
        self.lsp_client = lsp_client
        self.file_path = file_path
        self.uri: str = ""

    async def __aenter__(self) -> str:
        """Open document and return URI if not already open.

        Per ADR-0008, files remain open for the session lifetime.
        This method checks the DiagnosticCache to avoid sending redundant
        didOpen notifications when a file is already open.

        Returns:
            File URI for subsequent LSP requests
        """
        uri = self.file_path.as_uri()
        state = await self.lsp_client.get_diagnostic_cache_state(uri)

        if not state.is_open:
            # File not yet open - send didOpen notification
            content = self.file_path.read_text(encoding="utf-8")
            self.uri = await self.lsp_client.open_document(self.file_path, content)
            # Mark file as open in cache
            await self.lsp_client.mark_diagnostic_cache_open(uri)
        else:
            # File already open - skip didOpen, just return URI
            self.uri = uri

        return self.uri

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Exit context without closing document.

        Per ADR-0008, files remain open for the session lifetime.
        No didClose is sent; the file stays open in the LSP server.
        """
        # No action - file stays open per ADR-0008
        pass
