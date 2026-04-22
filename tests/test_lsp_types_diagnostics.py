"""Tests for diagnostic types in LSP types module."""

from llm_lsp_cli.lsp import types as lsp


class TestDiagnosticTypes:
    """Tests for diagnostic-related types."""

    def test_document_diagnostic_params_type(self) -> None:
        """Test that DocumentDiagnosticParams type is defined."""
        # This should not raise an AttributeError
        params: lsp.DocumentDiagnosticParams = {
            "textDocument": {"uri": "file:///test.py"},
            "previousResultId": None,
        }

        assert params["textDocument"]["uri"] == "file:///test.py"

    def test_document_diagnostic_report_type(self) -> None:
        """Test that DocumentDiagnosticReport type is defined."""
        # This should not raise an AttributeError
        report: lsp.DocumentDiagnosticReport = {
            "kind": "full",
            "resultId": "abc123",
            "items": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                    "severity": 1,
                    "message": "Test error",
                }
            ],
        }

        assert report["kind"] == "full"
        assert len(report["items"]) == 1

    def test_workspace_diagnostic_item_type(self) -> None:
        """Test that WorkspaceDiagnosticItem type is defined."""
        # This should not raise an AttributeError
        item: lsp.WorkspaceDiagnosticItem = {
            "uri": "file:///test.py",
            "version": 1,
            "diagnostics": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 10},
                    },
                    "severity": 1,
                    "message": "Test error",
                }
            ],
        }

        assert item["uri"] == "file:///test.py"
        assert len(item["diagnostics"]) == 1

    def test_workspace_diagnostic_report_type(self) -> None:
        """Test that WorkspaceDiagnosticReport type is defined."""
        # This should not raise an AttributeError
        report: lsp.WorkspaceDiagnosticReport = {
            "items": [
                {
                    "uri": "file:///test1.py",
                    "version": 1,
                    "diagnostics": [{"severity": 1, "message": "Error 1"}],
                },
                {
                    "uri": "file:///test2.py",
                    "version": 1,
                    "diagnostics": [{"severity": 2, "message": "Warning 2"}],
                },
            ],
        }

        assert len(report["items"]) == 2
