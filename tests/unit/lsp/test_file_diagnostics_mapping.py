"""Tests for file-to-diagnostics mapping."""

import pytest

from llm_lsp_cli.lsp.client import WorkspaceDiagnosticManager


class TestFileDiagnosticsMapping:
    """Test file-to-diagnostics mapping in the workspace diagnostic result."""

    async def test_workspace_diagnostic_items_have_uri(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test workspace diagnostic items contain URIs."""
        await workspace_diagnostic_manager._update_cache(
            "file:///workspace/src/module.py",
            [{"range": {"start": {"line": 0}}, "message": "Error"}],
        )

        items = await workspace_diagnostic_manager._get_cache_items()

        assert len(items) == 1
        assert items[0]["uri"] == "file:///workspace/src/module.py"
        assert "diagnostics" in items[0]

    async def test_workspace_diagnostic_items_have_version(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test workspace diagnostic items have version field."""
        await workspace_diagnostic_manager._update_cache(
            "file:///test.py",
            [{"message": "Error"}],
        )

        items = await workspace_diagnostic_manager._get_cache_items()

        assert "version" in items[0]
        # Version may be None if not tracked

    async def test_diagnostics_preserve_structure(
        self,
        workspace_diagnostic_manager: WorkspaceDiagnosticManager,
    ) -> None:
        """Test diagnostic structure is preserved through cache."""
        original_diagnostic = {
            "range": {
                "start": {"line": 10, "character": 5},
                "end": {"line": 10, "character": 15},
            },
            "severity": 1,
            "code": "E001",
            "source": "pyright",
            "message": "Type mismatch",
            "tags": [1],
        }

        await workspace_diagnostic_manager._update_cache(
            "file:///test.py",
            [original_diagnostic],
        )

        items = await workspace_diagnostic_manager._get_cache_items()

        cached = items[0]["diagnostics"][0]
        assert cached["range"]["start"]["line"] == 10  # type: ignore[typeddict-item]
        assert cached["severity"] == 1  # type: ignore[typeddict-item]
        assert cached["code"] == "E001"  # type: ignore[typeddict-item]
        assert cached["source"] == "pyright"  # type: ignore[typeddict-item]
        assert cached["message"] == "Type mismatch"  # type: ignore[typeddict-item]
