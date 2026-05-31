"""Tests for IPC parameter and result models.

This test module covers T1 scenarios from the test specification.
Tests will fail until src/llm_lsp_cli/ipc/models.py is implemented.
"""

import pytest


class TestEmptyParams:
    """Tests for EmptyParams model (T1.1, T1.2)."""

    def test_empty_params_validates_empty_dict(self) -> None:
        """T1.1: EmptyParams validates empty dict."""
        from llm_lsp_cli.ipc.models import EmptyParams

        params = EmptyParams()
        assert params is not None

    def test_empty_params_model_dump_returns_empty_dict(self) -> None:
        """T1.2: EmptyParams model_dump returns empty dict."""
        from llm_lsp_cli.ipc.models import EmptyParams

        params = EmptyParams()
        assert params.model_dump() == {}


class TestPosition:
    """Tests for Position model (T1.3, T1.4)."""

    def test_position_validates_line_character(self) -> None:
        """T1.3: Position validates line/character."""
        from llm_lsp_cli.ipc.models import Position

        pos = Position(line=10, character=5)
        assert pos.line == 10
        assert pos.character == 5

    def test_position_accepts_zero_values(self) -> None:
        """T1.4: Position accepts zero values."""
        from llm_lsp_cli.ipc.models import Position

        pos = Position(line=0, character=0)
        assert pos.line == 0
        assert pos.character == 0


class TestTextDocumentIdentifier:
    """Tests for TextDocumentIdentifier model (T1.5)."""

    def test_text_document_identifier_validates_uri(self) -> None:
        """T1.5: TextDocumentIdentifier validates URI."""
        from llm_lsp_cli.ipc.models import TextDocumentIdentifier

        tdi = TextDocumentIdentifier(uri="file:///test.py")
        assert tdi.uri == "file:///test.py"


class TestTextDocumentPositionParams:
    """Tests for TextDocumentPositionParams model (T1.6)."""

    def test_text_document_position_params_nests_correctly(self) -> None:
        """T1.6: TextDocumentPositionParams nests correctly."""
        from llm_lsp_cli.ipc.models import (
            Position,
            TextDocumentIdentifier,
            TextDocumentPositionParams,
        )

        params = TextDocumentPositionParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
        )
        assert params.text_document.uri == "file:///test.py"
        assert params.position.line == 10

    def test_text_document_position_params_serializes_correctly(self) -> None:
        """T1.6b: TextDocumentPositionParams serializes nested models with aliases."""
        from llm_lsp_cli.ipc.models import (
            Position,
            TextDocumentIdentifier,
            TextDocumentPositionParams,
        )

        params = TextDocumentPositionParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
        )
        # model_dump() uses aliases by default
        data = params.model_dump(by_alias=True)
        assert data["textDocument"]["uri"] == "file:///test.py"
        assert data["position"]["line"] == 10
        assert data["position"]["character"] == 5


class TestWorkspaceSymbolParams:
    """Tests for WorkspaceSymbolParams model (T1.7)."""

    def test_workspace_symbol_params_validates_query(self) -> None:
        """T1.7: WorkspaceSymbolParams validates query."""
        from llm_lsp_cli.ipc.models import WorkspaceSymbolParams

        params = WorkspaceSymbolParams(query="foo")
        assert params.query == "foo"


class TestRenameParams:
    """Tests for RenameParams model (T1.8)."""

    def test_rename_params_includes_new_name_field(self) -> None:
        """T1.8: RenameParams includes newName field."""
        from llm_lsp_cli.ipc.models import (
            Position,
            RenameParams,
            TextDocumentIdentifier,
        )

        params = RenameParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
            newName="bar",
        )
        assert params.new_name == "bar"


class TestDefinitionParams:
    """Tests for DefinitionParams model (T1.9)."""

    def test_definition_params_extends_text_document_position_params(self) -> None:
        """T1.9: DefinitionParams extends TextDocumentPositionParams."""
        from llm_lsp_cli.ipc.models import (
            DefinitionParams,
            Position,
            TextDocumentIdentifier,
        )

        params = DefinitionParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
        )
        assert params.text_document.uri == "file:///test.py"
        assert params.position.line == 10


class TestHoverParams:
    """Tests for HoverParams model (T1.10)."""

    def test_hover_params_extends_text_document_position_params(self) -> None:
        """T1.10: HoverParams extends TextDocumentPositionParams."""
        from llm_lsp_cli.ipc.models import (
            HoverParams,
            Position,
            TextDocumentIdentifier,
        )

        params = HoverParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
        )
        assert params.text_document.uri == "file:///test.py"
        assert params.position.line == 10


class TestDocumentSymbolParams:
    """Tests for DocumentSymbolParams model (T1.11)."""

    def test_document_symbol_params_validates(self) -> None:
        """T1.11: DocumentSymbolParams validates."""
        from llm_lsp_cli.ipc.models import (
            DocumentSymbolParams,
            TextDocumentIdentifier,
        )

        params = DocumentSymbolParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
        )
        assert params.text_document.uri == "file:///test.py"


class TestCompletionParams:
    """Tests for CompletionParams model (T1.12)."""

    def test_completion_params_includes_context(self) -> None:
        """T1.12: CompletionParams includes context."""
        from llm_lsp_cli.ipc.models import (
            CompletionContext,
            CompletionParams,
            Position,
            TextDocumentIdentifier,
        )

        params = CompletionParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
            context=CompletionContext(triggerKind=1),
        )
        assert params.context is not None
        assert params.context.trigger_kind == 1


class TestReferenceParams:
    """Tests for ReferenceParams model (T1.13)."""

    def test_reference_params_includes_context(self) -> None:
        """T1.13: ReferenceParams includes context."""
        from llm_lsp_cli.ipc.models import (
            Position,
            ReferenceContext,
            ReferenceParams,
            TextDocumentIdentifier,
        )

        params = ReferenceParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
            context=ReferenceContext(includeDeclaration=True),
        )
        assert params.context.include_declaration is True


class TestPrepareRenameParams:
    """Tests for PrepareRenameParams model (T1.14)."""

    def test_prepare_rename_params_extends_base(self) -> None:
        """T1.14: PrepareRenameParams extends base."""
        from llm_lsp_cli.ipc.models import (
            Position,
            PrepareRenameParams,
            TextDocumentIdentifier,
        )

        params = PrepareRenameParams(
            textDocument=TextDocumentIdentifier(uri="file:///test.py"),
            position=Position(line=10, character=5),
        )
        assert params.text_document.uri == "file:///test.py"


class TestPingResult:
    """Tests for PingResult model (T1.15)."""

    def test_ping_result_validates_status(self) -> None:
        """T1.15: PingResult validates status."""
        from llm_lsp_cli.ipc.models import PingResult

        result = PingResult(status="ok")
        assert result.status == "ok"


class TestShutdownResult:
    """Tests for ShutdownResult model (T1.16)."""

    def test_shutdown_result_validates_status(self) -> None:
        """T1.16: ShutdownResult validates status."""
        from llm_lsp_cli.ipc.models import ShutdownResult

        result = ShutdownResult(status="ok")
        assert result.status == "ok"


class TestDaemonStatusResult:
    """Tests for DaemonStatusResult model (T1.17)."""

    def test_daemon_status_result_includes_all_fields(self) -> None:
        """T1.17: DaemonStatusResult includes all fields."""
        from llm_lsp_cli.ipc.models import DaemonStatusResult

        result = DaemonStatusResult(
            running=True,
            workspace="/ws",
            language="py",
            pid=123,
            uptime_seconds=1.5,
        )
        assert result.running is True
        assert result.workspace == "/ws"
        assert result.language == "py"
        assert result.pid == 123
        assert result.uptime_seconds == 1.5
