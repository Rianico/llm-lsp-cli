"""LspMethodRouter domain service for routing LSP methods to registry operations."""

from __future__ import annotations

from dataclasses import dataclass, field

from llm_lsp_cli.lsp.constants import LSPConstants


@dataclass(frozen=True)
class LspMethodConfig:
    """Configuration for an LSP method in the registry.

    Attributes:
        registry_method: The method name used for registry operations.
        required_params: List of required parameter names.
        param_mapping: Mapping from LSP params to registry params.
    """

    registry_method: str
    required_params: list[str] = field(default_factory=list)
    param_mapping: dict[str, str] = field(default_factory=dict)


def _create_method_config(
    registry_method: str,
    required_params: list[str] | None = None,
    uri_mapping: bool = True,
) -> LspMethodConfig:
    """Helper to create LspMethodConfig with common URI mapping pattern.

    Args:
        registry_method: The registry method name.
        required_params: Optional list of required params. Defaults to empty.
        uri_mapping: Whether to include textDocument.uri mapping. Defaults to True.

    Returns:
        Configured LspMethodConfig instance.
    """
    return LspMethodConfig(
        registry_method=registry_method,
        required_params=required_params or [],
        param_mapping={"uri": "textDocument.uri"} if uri_mapping else {},
    )


class LspMethodRouter:
    """Domain service for routing LSP methods to registry operations.

    Provides configuration for each LSP method, defining how requests
    should be routed to the server registry.
    """

    def __init__(self) -> None:
        """Initialize the router with default LSP method configurations."""
        self._configs: dict[str, LspMethodConfig] = {
            LSPConstants.DEFINITION: _create_method_config(
                "request_definition", ["textDocument", "position"]
            ),
            LSPConstants.REFERENCES: _create_method_config(
                "request_references", ["textDocument", "position"]
            ),
            LSPConstants.COMPLETION: _create_method_config(
                "request_completions", ["textDocument", "position"]
            ),
            LSPConstants.HOVER: _create_method_config(
                "request_hover", ["textDocument", "position"]
            ),
            LSPConstants.DOCUMENT_SYMBOL: _create_method_config(
                "request_document_symbols", ["textDocument"], uri_mapping=False
            ),
            LSPConstants.WORKSPACE_SYMBOL: _create_method_config(
                "request_workspace_symbols", ["query"], uri_mapping=False
            ),
            LSPConstants.DIAGNOSTIC: _create_method_config(
                "request_diagnostics", ["textDocument"], uri_mapping=False
            ),
            LSPConstants.WORKSPACE_DIAGNOSTIC: _create_method_config(
                "request_workspace_diagnostics", [], uri_mapping=False
            ),
            LSPConstants.CALL_HIERARCHY_INCOMING_CALLS: _create_method_config(
                "request_call_hierarchy_incoming", ["textDocument", "position"]
            ),
            LSPConstants.CALL_HIERARCHY_OUTGOING_CALLS: _create_method_config(
                "request_call_hierarchy_outgoing", ["textDocument", "position"]
            ),
        }

    def get_config(self, method: str) -> LspMethodConfig | None:
        """Get the configuration for an LSP method.

        Args:
            method: LSP method name (e.g., LSPConstants.DEFINITION).

        Returns:
            LspMethodConfig if configured, None otherwise.
        """
        return self._configs.get(method)
