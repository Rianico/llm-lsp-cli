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
from llm_lsp_cli.lsp.types import DocumentSymbol, Range, Position

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


def _make_range(start_line: int, start_char: int, end_line: int, end_char: int) -> Range:
    """Create a Range from line/char values."""
    return Range(
        start=Position(line=start_line, character=start_char),
        end=Position(line=end_line, character=end_char),
    )


# =============================================================================
# Category A: CLI Integration Tests for TEXT Format Tree Rendering
# =============================================================================


class TestDocumentSymbolTextFormat:
    """Tests for document-symbol command TEXT format using tree renderer."""

    @pytest.fixture
    def mock_document_symbol_response(self) -> list[DocumentSymbol]:
        """Mock LSP documentSymbol response with nested symbols."""
        return [
            DocumentSymbol(
                name="MyClass",
                kind=5,
                range=_make_range(0, 0, 50, 1),
                selection_range=_make_range(0, 6, 0, 13),
                tags=[1],  # @deprecated
                children=[
                    DocumentSymbol(
                        name="__init__",
                        kind=6,
                        range=_make_range(1, 4, 25, 1),
                        selection_range=_make_range(1, 8, 1, 16),
                    ),
                    DocumentSymbol(
                        name="method",
                        kind=6,
                        range=_make_range(30, 4, 45, 1),
                        selection_range=_make_range(30, 8, 30, 14),
                    ),
                ],
            ),
            DocumentSymbol(
                name="helper",
                kind=12,
                range=_make_range(55, 0, 80, 1),
                selection_range=_make_range(55, 0, 55, 7),
            ),
        ]

    def test_text_format_uses_tree_connectors(
        self, mock_document_symbol_response: list[DocumentSymbol], monkeypatch: pytest.MonkeyPatch
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
        self, mock_document_symbol_response: list[DocumentSymbol], monkeypatch: pytest.MonkeyPatch
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
        three_level_response = [
            DocumentSymbol(
                name="OuterClass",
                kind=5,
                range=_make_range(0, 0, 100, 1),
                selection_range=_make_range(0, 0, 0, 10),
                children=[
                    DocumentSymbol(
                        name="inner_method",
                        kind=6,
                        range=_make_range(10, 4, 50, 1),
                        selection_range=_make_range(10, 4, 10, 16),
                        children=[
                            DocumentSymbol(
                                name="local_var",
                                kind=13,
                                range=_make_range(15, 8, 16, 0),
                                selection_range=_make_range(15, 8, 15, 17),
                            ),
                        ],
                    ),
                ],
            ),
        ]

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
        assert "local_var" not in result.output, "Grandchildren should NOT appear with depth=1"

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
            lambda *args, **kwargs: [],  # Empty list of DocumentSymbol
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

        # Now shows header even for empty results
        assert "Basedpyright: document-symbol" in result.output


class TestDocumentSymbolOtherFormats:
    """Tests for non-TEXT formats still using CompactFormatter."""

    @pytest.fixture
    def mock_symbols(self) -> list[DocumentSymbol]:
        """Mock LSP response with symbols."""
        return [
            DocumentSymbol(
                name="test_func",
                kind=12,
                range=_make_range(0, 0, 10, 0),
                selection_range=_make_range(0, 0, 0, 9),
            )
        ]

    def test_json_format_uses_compact_formatter(
        self, mock_symbols: list[DocumentSymbol], monkeypatch: pytest.MonkeyPatch
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

        parsed = json.loads(result.output)
        assert "_source" in parsed
        assert "items" in parsed
        assert len(parsed["items"]) == 1
        assert parsed["items"][0]["name"] == "test_func"

    def test_yaml_format_uses_compact_formatter(
        self, mock_symbols: list[DocumentSymbol], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """YAML format should use CompactFormatter with file field."""
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

        parsed = yaml.safe_load(result.output)
        assert "_source" in parsed
        assert "items" in parsed
        assert len(parsed["items"]) == 1
        assert parsed["items"][0]["name"] == "test_func"

    def test_csv_format_uses_compact_formatter(
        self, mock_symbols: list[DocumentSymbol], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CSV format should use CompactFormatter with file column."""
        import csv
        import io

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

        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["name"] == "test_func"
