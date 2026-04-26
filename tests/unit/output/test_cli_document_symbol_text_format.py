"""CLI integration tests for document-symbol TEXT format using tree renderer.

Tests verify that the CLI's document-symbol command uses the new
symbol_transformer + text_renderer pipeline for TEXT format output,
as specified in ADR-0014.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_lsp_cli.cli import app
from llm_lsp_cli.commands.shared import OutputFormat, RequestContext

runner = CliRunner()


def make_mock_context(
    workspace_path: str = "/workspace",
    language: str = "python",
    output_format: OutputFormat = OutputFormat.TEXT,
    file_path: str = "test.py",
) -> RequestContext:
    """Create a mock RequestContext for testing."""
    return RequestContext(
        workspace_path=workspace_path,
        language=language,
        output_format=output_format,
        file_path=Path(file_path),
        line=None,
        column=None,
        query=None,
        include_tests=False,
    )


# =============================================================================
# Category A: CLI Integration Tests for TEXT Format Tree Rendering
# =============================================================================


class TestDocumentSymbolTextFormat:
    """Tests for document-symbol command TEXT format using tree renderer."""

    @pytest.fixture
    def mock_document_symbol_response(self) -> dict:
        """Mock LSP documentSymbol response with nested symbols."""
        return {
            "symbols": [
                {
                    "name": "MyClass",
                    "kind": 5,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 1},
                    },
                    "selectionRange": {
                        "start": {"line": 0, "character": 6},
                        "end": {"line": 0, "character": 13},
                    },
                    "tags": [1],  # @deprecated
                    "children": [
                        {
                            "name": "__init__",
                            "kind": 6,
                            "range": {
                                "start": {"line": 1, "character": 4},
                                "end": {"line": 25, "character": 1},
                            },
                            "selectionRange": {
                                "start": {"line": 1, "character": 8},
                                "end": {"line": 1, "character": 16},
                            },
                        },
                        {
                            "name": "method",
                            "kind": 6,
                            "range": {
                                "start": {"line": 30, "character": 4},
                                "end": {"line": 45, "character": 1},
                            },
                            "selectionRange": {
                                "start": {"line": 30, "character": 8},
                                "end": {"line": 30, "character": 14},
                            },
                        },
                    ],
                },
                {
                    "name": "helper",
                    "kind": 12,
                    "range": {
                        "start": {"line": 55, "character": 0},
                        "end": {"line": 80, "character": 1},
                    },
                    "selectionRange": {
                        "start": {"line": 55, "character": 0},
                        "end": {"line": 55, "character": 7},
                    },
                },
            ]
        }

    def test_text_format_uses_tree_connectors(
        self, mock_document_symbol_response: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TEXT format must use tree connectors (|-- and `--) per ADR-0014."""
        from llm_lsp_cli.commands import lsp

        # Mock build_request_context to return a valid context
        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(),
        )

        # Mock send_request to return the test data
        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: mock_document_symbol_response,
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "text"],
            catch_exceptions=False,
        )

        # TEXT format MUST use tree connectors
        assert "├──" in result.output, "Missing intermediate connector for sibling"
        assert "└──" in result.output, "Missing last sibling connector"
        assert "MyClass" in result.output

    def test_text_format_uses_tree_renderer_with_children(
        self, mock_document_symbol_response: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TEXT format must show nested children with continuation prefix."""
        from llm_lsp_cli.commands import lsp

        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(),
        )

        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: mock_document_symbol_response,
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "text"],
            catch_exceptions=False,
        )

        # MyClass has a sibling (helper), so children should have | prefix
        assert "│" in result.output, "Missing continuation prefix for nested children"
        # Children should be indented under parent
        assert "│   ├── __init__" in result.output
        assert "│   └── method" in result.output

    def test_text_format_depth_parameter_respected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI --depth parameter must pass through to transform_symbols."""
        from llm_lsp_cli.commands import lsp

        # 3-level nested structure
        three_level_response = {
            "symbols": [
                {
                    "name": "OuterClass",
                    "kind": 5,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 100, "character": 1},
                    },
                    "children": [
                        {
                            "name": "inner_method",
                            "kind": 6,
                            "range": {
                                "start": {"line": 1, "character": 4},
                                "end": {"line": 50, "character": 1},
                            },
                            "children": [
                                {
                                    "name": "nested_func",
                                    "kind": 12,
                                    "range": {
                                        "start": {"line": 5, "character": 8},
                                        "end": {"line": 20, "character": 1},
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(),
        )

        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: three_level_response,
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        # With depth=1, grandchildren should NOT appear
        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "text", "--depth", "1"],
            catch_exceptions=False,
        )

        assert "inner_method" in result.output, "Children should appear"
        assert "nested_func" not in result.output, "Grandchildren should NOT appear with depth=1"

    def test_text_format_empty_symbols(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty symbol list should render 'No symbols found.' message."""
        from llm_lsp_cli.commands import lsp

        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(),
        )

        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: {"symbols": []},
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "text"],
            catch_exceptions=False,
        )

        assert result.output.strip() == "No symbols found."


class TestDocumentSymbolOtherFormats:
    """Tests for non-TEXT formats still using CompactFormatter."""

    @pytest.fixture
    def mock_symbols(self) -> dict:
        """Mock LSP response with symbols."""
        return {
            "symbols": [
                {
                    "name": "test_func",
                    "kind": 12,
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                }
            ]
        }

    def test_json_format_uses_compact_formatter(
        self, mock_symbols: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JSON format should use CompactFormatter with file field."""
        import json

        from llm_lsp_cli.commands import lsp

        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(output_format=OutputFormat.JSON),
        )

        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: mock_symbols,
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "json"],
            catch_exceptions=False,
        )

        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "test_func"
        assert "file" in data[0], "CompactFormatter JSON should have file field"
        assert "children" in data[0], "CompactFormatter JSON should have children field"

    def test_yaml_format_uses_compact_formatter(
        self, mock_symbols: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """YAML format should use CompactFormatter."""
        import yaml

        from llm_lsp_cli.commands import lsp

        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(output_format=OutputFormat.YAML),
        )

        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: mock_symbols,
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "yaml"],
            catch_exceptions=False,
        )

        data = yaml.safe_load(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "test_func"
        assert "file" in data[0], "CompactFormatter YAML should have file field"

    def test_csv_format_uses_compact_formatter(
        self, mock_symbols: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CSV format should use CompactFormatter with headers."""
        from llm_lsp_cli.commands import lsp

        monkeypatch.setattr(
            lsp,
            "build_request_context",
            lambda *args, **kwargs: make_mock_context(output_format=OutputFormat.CSV),
        )

        monkeypatch.setattr(
            lsp,
            "send_request",
            lambda *args, **kwargs: mock_symbols,
        )

        # Mock validate_file_in_workspace to skip file validation
        monkeypatch.setattr(
            lsp,
            "validate_file_in_workspace",
            lambda *args, **kwargs: Path("test.py"),
        )

        result = runner.invoke(
            app,
            ["lsp", "document-symbol", "test.py", "--format", "csv"],
            catch_exceptions=False,
        )

        lines = result.output.strip().split("\n")
        assert "file" in lines[0], "CSV should have file header"
        assert "name" in lines[0], "CSV should have name header"
        assert "test_func" in result.output
