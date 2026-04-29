# Tests for command header integration
"""Tests for header generation in LSP commands."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from llm_lsp_cli.commands.lsp import (
    completion,
    document_symbol,
    hover,
    incoming_calls,
    outgoing_calls,
    references,
    rename,
)
from llm_lsp_cli.commands.shared import GlobalOptions
from llm_lsp_cli.utils import OutputFormat


@pytest.fixture
def mock_ctx() -> MagicMock:
    """Create a mock Typer context with GlobalOptions."""
    ctx = MagicMock()
    ctx.obj = GlobalOptions(
        workspace="/workspace",
        language="python",
        output_format=OutputFormat.JSON,
    )
    return ctx


class TestDocumentSymbolHeaders:
    """Tests for document-symbol command headers."""

    def test_document_symbol_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for document-symbol."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "symbols": [
                {"name": "foo", "kind": 12, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 15}}}
            ]
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                document_symbol(
                    mock_ctx,
                    str(test_file),
                    workspace=None,
                    language=None,
                    output_format=None,
                    depth=1,
                    raw=False,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: document-symbol" in combined

    def test_document_symbol_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for document-symbol."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)
        mock_ctx.obj.output_format = OutputFormat.JSON

        mock_response = {
            "symbols": [
                {"name": "foo", "kind": 12, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 15}}}
            ]
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                document_symbol(
                    mock_ctx,
                    str(test_file),
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                    depth=1,
                    raw=False,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "document-symbol" in data["_source"]


class TestReferencesHeaders:
    """Tests for references command headers."""

    def test_references_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for references."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\nx = foo()\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "locations": [
                {"uri": test_file.as_uri(), "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 15}}}
            ]
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                references(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=None,
                    include_tests=False,
                    raw=False,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: references" in combined

    def test_references_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for references."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\nx = foo()\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "locations": [
                {"uri": test_file.as_uri(), "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 15}}}
            ]
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                references(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                    include_tests=False,
                    raw=False,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "references" in data["_source"]


class TestIncomingCallsHeaders:
    """Tests for incoming-calls command headers."""

    def test_incoming_calls_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for incoming-calls."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {"calls": []}

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                incoming_calls(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=None,
                    include_tests=False,
                    raw=False,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: incoming-calls" in combined

    def test_incoming_calls_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for incoming-calls."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "calls": [
                {"from": {"uri": test_file.as_uri(), "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 15}}}}
            ]
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                incoming_calls(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                    include_tests=False,
                    raw=False,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "incoming-calls" in data["_source"]


class TestOutgoingCallsHeaders:
    """Tests for outgoing-calls command headers."""

    def test_outgoing_calls_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for outgoing-calls."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {"calls": []}

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                outgoing_calls(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=None,
                    include_tests=False,
                    raw=False,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: outgoing-calls" in combined

    def test_outgoing_calls_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for outgoing-calls."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "calls": [
                {"to": {"uri": test_file.as_uri(), "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 15}}}}
            ]
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                outgoing_calls(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                    include_tests=False,
                    raw=False,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "outgoing-calls" in data["_source"]


class TestCompletionHeaders:
    """Tests for completion command headers."""

    def test_completion_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for completion."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {"items": []}

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                completion(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=None,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: completion" in combined

    def test_completion_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for completion."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {"items": [{"label": "foo", "kind": 3}]}

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                completion(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "completion" in data["_source"]


class TestHoverHeaders:
    """Tests for hover command headers."""

    def test_hover_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for hover."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "hover": {"contents": {"kind": "plaintext", "value": "def foo() -> None"}}
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                hover(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=None,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: hover" in combined

    def test_hover_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for hover."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "hover": {"contents": {"kind": "plaintext", "value": "def foo() -> None"}}
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                hover(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "hover" in data["_source"]


class TestRenameHeaders:
    """Tests for rename command headers."""

    def test_rename_text_header(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """TEXT format shows header for rename."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        # Empty workspace_edit means no changes - but we need something
        mock_response = {
            "workspace_edit": {"changes": {}}
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                rename(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    "bar",
                    workspace=None,
                    language=None,
                    output_format=None,
                    apply=False,
                    dry_run=False,
                    rollback=None,
                )

        combined = "\n".join(output_lines)
        assert "Basedpyright: rename" in combined

    def test_rename_json_source(self, mock_ctx: MagicMock, tmp_path: Path) -> None:
        """JSON format shows _source field for rename."""
        import llm_lsp_cli.commands.lsp as lsp_module

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        mock_ctx.obj.workspace = str(tmp_path)

        mock_response = {
            "workspace_edit": {
                "changes": {
                    test_file.as_uri(): [
                        {"range": {"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 7}}, "newText": "bar"}
                    ]
                }
            }
        }

        output_lines: list[str] = []

        def capture(x: str, **kwargs: Any) -> None:
            output_lines.append(x)

        with patch.object(lsp_module, "send_request", return_value=mock_response):
            with patch.object(lsp_module, "typer") as mock_typer:
                mock_typer.echo.side_effect = capture
                rename(
                    mock_ctx,
                    str(test_file),
                    1,
                    1,
                    "bar",
                    workspace=None,
                    language=None,
                    output_format=OutputFormat.JSON,
                    apply=False,
                    dry_run=False,
                    rollback=None,
                )

        output = output_lines[0]
        data = json.loads(output)
        assert "_source" in data
        assert "rename" in data["_source"]
