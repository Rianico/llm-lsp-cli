"""Unit tests for formatter Pydantic model consumption.

These tests verify that the formatter layer accepts validated Pydantic models
from lsp/types.py instead of raw dict[str, object] inputs (ADR-0027).

Each test compares output from Pydantic model input against output from
equivalent dict input to ensure behavioral equivalence during migration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from llm_lsp_cli.lsp.types import (
    CallHierarchyIncomingCall,
    CallHierarchyItem,
    CallHierarchyOutgoingCall,
    CompletionItem,
    Diagnostic,
    DocumentSymbol,
    Hover,
    Location,
    MarkupContent,
    Position as LspPosition,
    Range as LspRange,
    SymbolInformation,
    TextEdit,
)
from llm_lsp_cli.output.formatter import CompactFormatter, Range, range_from_dict


# =============================================================================
# FIXTURES: Pydantic Model Instances
# =============================================================================


@pytest.fixture
def lsp_position() -> LspPosition:
    """Create a Position Pydantic model."""
    return LspPosition(line=0, character=0)


@pytest.fixture
def lsp_range() -> LspRange:
    """Create a Range Pydantic model."""
    return LspRange(
        start=LspPosition(line=0, character=0),
        end=LspPosition(line=50, character=0),
    )


@pytest.fixture
def lsp_location() -> Location:
    """Create a Location Pydantic model."""
    return Location(
        uri="file:///workspace/src/main.py",
        range=LspRange(
            start=LspPosition(line=10, character=5),
            end=LspPosition(line=20, character=15),
        ),
    )


@pytest.fixture
def document_symbol_simple() -> DocumentSymbol:
    """Create a simple DocumentSymbol without children."""
    return DocumentSymbol(
        name="MyClass",
        kind=5,  # Class
        range=LspRange(
            start=LspPosition(line=0, character=0),
            end=LspPosition(line=10, character=1),
        ),
        selection_range=LspRange(
            start=LspPosition(line=0, character=6),
            end=LspPosition(line=0, character=13),
        ),
    )


@pytest.fixture
def document_symbol_with_children() -> DocumentSymbol:
    """Create a DocumentSymbol with nested children."""
    return DocumentSymbol(
        name="MyClass",
        kind=5,  # Class
        range=LspRange(
            start=LspPosition(line=0, character=0),
            end=LspPosition(line=30, character=1),
        ),
        selection_range=LspRange(
            start=LspPosition(line=0, character=6),
            end=LspPosition(line=0, character=13),
        ),
        children=[
            DocumentSymbol(
                name="__init__",
                kind=6,  # Method
                range=LspRange(
                    start=LspPosition(line=1, character=4),
                    end=LspPosition(line=5, character=20),
                ),
                selection_range=LspRange(
                    start=LspPosition(line=1, character=8),
                    end=LspPosition(line=1, character=16),
                ),
                detail="(self, x: int)",
            ),
        ],
    )


@pytest.fixture
def symbol_information() -> SymbolInformation:
    """Create a SymbolInformation (workspace symbol format)."""
    return SymbolInformation(
        name="MyClass",
        kind=5,  # Class
        location=Location(
            uri="file:///workspace/src/main.py",
            range=LspRange(
                start=LspPosition(line=0, character=0),
                end=LspPosition(line=10, character=1),
            ),
        ),
        container_name="module",
    )


@pytest.fixture
def lsp_diagnostic() -> Diagnostic:
    """Create a Diagnostic Pydantic model."""
    return Diagnostic(
        range=LspRange(
            start=LspPosition(line=5, character=10),
            end=LspPosition(line=5, character=20),
        ),
        message="Undefined variable",
        severity=1,
        code="undef",
        source="pyright",
        tags=[1],  # Unnecessary
    )


@pytest.fixture
def lsp_hover_markup() -> Hover:
    """Create a Hover with MarkupContent."""
    return Hover(
        contents=MarkupContent(kind="markdown", value="```python\nmy_func() -> str\n```"),
        range=LspRange(
            start=LspPosition(line=10, character=5),
            end=LspPosition(line=10, character=12),
        ),
    )


@pytest.fixture
def lsp_completion() -> CompletionItem:
    """Create a CompletionItem Pydantic model."""
    return CompletionItem(
        label="my_func",
        kind=6,  # Method
        detail="() -> str",
        documentation=MarkupContent(kind="markdown", value="A function"),
        text_edit=TextEdit(
            range=LspRange(
                start=LspPosition(line=1, character=0),
                end=LspPosition(line=1, character=7),
            ),
            new_text="my_func()",
        ),
    )


@pytest.fixture
def call_hierarchy_incoming() -> CallHierarchyIncomingCall:
    """Create a CallHierarchyIncomingCall Pydantic model."""
    return CallHierarchyIncomingCall(
        from_=CallHierarchyItem(
            name="caller_func",
            kind=12,  # Function
            uri="file:///workspace/src/caller.py",
            range=LspRange(
                start=LspPosition(line=5, character=0),
                end=LspPosition(line=10, character=1),
            ),
            selection_range=LspRange(
                start=LspPosition(line=5, character=4),
                end=LspPosition(line=5, character=15),
            ),
        ),
        from_ranges=[
            LspRange(
                start=LspPosition(line=7, character=4),
                end=LspPosition(line=7, character=14),
            ),
        ],
    )


@pytest.fixture
def call_hierarchy_outgoing() -> CallHierarchyOutgoingCall:
    """Create a CallHierarchyOutgoingCall Pydantic model."""
    return CallHierarchyOutgoingCall(
        to=CallHierarchyItem(
            name="callee_func",
            kind=12,  # Function
            uri="file:///workspace/src/callee.py",
            range=LspRange(
                start=LspPosition(line=1, character=0),
                end=LspPosition(line=5, character=1),
            ),
            selection_range=LspRange(
                start=LspPosition(line=1, character=4),
                end=LspPosition(line=1, character=14),
            ),
        ),
        from_ranges=[
            LspRange(
                start=LspPosition(line=3, character=4),
                end=LspPosition(line=3, character=14),
            ),
        ],
    )


# =============================================================================
# FIXTURES: Equivalent dict representations
# =============================================================================


@pytest.fixture
def dict_range() -> dict[str, object]:
    """Dict equivalent of lsp_range fixture."""
    return {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 0}}


@pytest.fixture
def dict_location() -> dict[str, object]:
    """Dict equivalent of lsp_location fixture."""
    return {
        "uri": "file:///workspace/src/main.py",
        "range": {
            "start": {"line": 10, "character": 5},
            "end": {"line": 20, "character": 15},
        },
    }


@pytest.fixture
def dict_document_symbol_simple() -> dict[str, object]:
    """Dict equivalent of document_symbol_simple fixture."""
    return {
        "name": "MyClass",
        "kind": 5,
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 1}},
        "selectionRange": {
            "start": {"line": 0, "character": 6},
            "end": {"line": 0, "character": 13},
        },
    }


@pytest.fixture
def dict_diagnostic() -> dict[str, object]:
    """Dict equivalent of lsp_diagnostic fixture."""
    return {
        "range": {
            "start": {"line": 5, "character": 10},
            "end": {"line": 5, "character": 20},
        },
        "message": "Undefined variable",
        "severity": 1,
        "code": "undef",
        "source": "pyright",
        "tags": [1],
    }


# =============================================================================
# TEST SCENARIO B1: Range types are unified (lsp.types.Range = output.formatter.Range)
# =============================================================================


class TestRangeUnification:
    """Range from output.formatter is the same type as lsp.types.Range."""

    def test_range_is_lsp_range(self) -> None:
        """Range imported from output.formatter IS lsp.types.Range (unified)."""
        assert Range is LspRange

    def test_range_from_dict_produces_valid_range(
        self, dict_range: dict[str, object]
    ) -> None:
        """range_from_dict creates a valid Range from a dict."""
        result = range_from_dict(dict_range)

        assert result.start.line == 0
        assert result.start.character == 0
        assert result.end.line == 50
        assert result.end.character == 0

    def test_range_from_dict_matches_direct_construction(self) -> None:
        """range_from_dict produces equivalent Range to direct construction."""
        from llm_lsp_cli.output.formatter import Position

        dict_range: dict[str, object] = {
            "start": {"line": 5, "character": 10},
            "end": {"line": 5, "character": 20},
        }
        result = range_from_dict(dict_range)
        expected = Range(
            start=Position(line=5, character=10),
            end=Position(line=5, character=20),
        )
        assert result == expected


# =============================================================================
# TEST SCENARIO B2: transform_symbols() with DocumentSymbol produces same output
# =============================================================================


class TestTransformSymbolsPydantic:
    """RED: transform_symbols() must accept Pydantic DocumentSymbol models."""

    def test_transform_symbols_accepts_pydantic_document_symbol(
        self, document_symbol_simple: DocumentSymbol
    ) -> None:
        """RED: transform_symbols must accept list[DocumentSymbol] input."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        # This will fail because transform_symbols expects dict[str, object]
        result = formatter.transform_symbols([document_symbol_simple])

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].kind == 5
        assert result[0].kind_name == "Class"

    def test_transform_symbols_pydantic_matches_dict_output(
        self,
        document_symbol_simple: DocumentSymbol,
        dict_document_symbol_simple: dict[str, object],
    ) -> None:
        """RED: transform_symbols must produce same output for Pydantic and dict inputs."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        pydantic_result = formatter.transform_symbols([document_symbol_simple])
        dict_result = formatter.transform_symbols([dict_document_symbol_simple])

        assert len(pydantic_result) == len(dict_result)
        assert pydantic_result[0].name == dict_result[0].name
        assert pydantic_result[0].kind == dict_result[0].kind
        assert pydantic_result[0].kind_name == dict_result[0].kind_name

    def test_transform_symbols_pydantic_nested_children(
        self, document_symbol_with_children: DocumentSymbol
    ) -> None:
        """RED: transform_symbols must correctly handle nested children in Pydantic models."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        result = formatter.transform_symbols([document_symbol_with_children])

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert len(result[0].children) == 1
        assert result[0].children[0].name == "__init__"
        assert result[0].children[0].detail == "(self, x: int)"

    def test_transform_symbols_accepts_symbol_information(
        self, symbol_information: SymbolInformation
    ) -> None:
        """RED: transform_symbols must accept SymbolInformation (workspace symbol format)."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        result = formatter.transform_symbols([symbol_information])

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].container == "module"


# =============================================================================
# TEST SCENARIO B3: transform_locations() with Location produces same output
# =============================================================================


class TestTransformLocationsPydantic:
    """RED: transform_locations() must accept Pydantic Location models."""

    def test_transform_locations_accepts_pydantic_location(
        self, lsp_location: Location
    ) -> None:
        """RED: transform_locations must accept list[Location] input."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        result = formatter.transform_locations([lsp_location])

        assert len(result) == 1
        assert result[0].file == "/workspace/src/main.py"

    def test_transform_locations_pydantic_matches_dict_output(
        self, lsp_location: Location, dict_location: dict[str, object]
    ) -> None:
        """RED: transform_locations must produce same output for Pydantic and dict inputs."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        pydantic_result = formatter.transform_locations([lsp_location])
        dict_result = formatter.transform_locations([dict_location])

        assert len(pydantic_result) == len(dict_result)
        assert pydantic_result[0].file == dict_result[0].file
        assert pydantic_result[0].range == dict_result[0].range


# =============================================================================
# TEST SCENARIO B4: transform_diagnostics() with Diagnostic produces same output
# =============================================================================


class TestTransformDiagnosticsPydantic:
    """RED: transform_diagnostics() must accept Pydantic Diagnostic models."""

    def test_transform_diagnostics_accepts_pydantic_diagnostic(
        self, lsp_diagnostic: Diagnostic
    ) -> None:
        """RED: transform_diagnostics must accept list[Diagnostic] input."""
        workspace = Path("/workspace")
        file_path = "/workspace/src/main.py"
        formatter = CompactFormatter(workspace)

        result = formatter.transform_diagnostics([lsp_diagnostic], file_path=file_path)

        assert len(result) == 1
        assert result[0].message == "Undefined variable"
        assert result[0].severity == 1
        assert result[0].severity_name == "Error"
        assert result[0].code == "undef"

    def test_transform_diagnostics_pydantic_matches_dict_output(
        self, lsp_diagnostic: Diagnostic, dict_diagnostic: dict[str, object]
    ) -> None:
        """RED: transform_diagnostics must produce same output for Pydantic and dict inputs."""
        workspace = Path("/workspace")
        file_path = "/workspace/src/main.py"
        formatter = CompactFormatter(workspace)

        pydantic_result = formatter.transform_diagnostics([lsp_diagnostic], file_path=file_path)
        dict_result = formatter.transform_diagnostics([dict_diagnostic], file_path=file_path)

        assert len(pydantic_result) == len(dict_result)
        assert pydantic_result[0].message == dict_result[0].message
        assert pydantic_result[0].severity == dict_result[0].severity
        assert pydantic_result[0].code == dict_result[0].code


# =============================================================================
# TEST SCENARIO B5: transform_call_hierarchy_incoming() with CallHierarchyIncomingCall
# =============================================================================


class TestTransformCallHierarchyIncomingPydantic:
    """RED: transform_call_hierarchy_incoming() must accept Pydantic models."""

    def test_transform_call_hierarchy_incoming_accepts_pydantic(
        self, call_hierarchy_incoming: CallHierarchyIncomingCall
    ) -> None:
        """RED: transform_call_hierarchy_incoming must accept list[CallHierarchyIncomingCall]."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        result = formatter.transform_call_hierarchy_incoming([call_hierarchy_incoming])

        assert len(result) == 1
        assert result[0].name == "caller_func"
        assert result[0].kind == 12
        assert result[0].kind_name == "Function"

    def test_transform_call_hierarchy_incoming_accesses_from_field(
        self, call_hierarchy_incoming: CallHierarchyIncomingCall
    ) -> None:
        """RED: must correctly access from_ field (not from which is a keyword)."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        result = formatter.transform_call_hierarchy_incoming([call_hierarchy_incoming])

        # Verify the from_ field was correctly accessed
        assert result[0].file == "/workspace/src/caller.py"


# =============================================================================
# TEST SCENARIO B6: transform_call_hierarchy_outgoing() with CallHierarchyOutgoingCall
# =============================================================================


class TestTransformCallHierarchyOutgoingPydantic:
    """RED: transform_call_hierarchy_outgoing() must accept Pydantic models."""

    def test_transform_call_hierarchy_outgoing_accepts_pydantic(
        self, call_hierarchy_outgoing: CallHierarchyOutgoingCall
    ) -> None:
        """RED: transform_call_hierarchy_outgoing must accept list[CallHierarchyOutgoingCall]."""
        workspace = Path("/workspace")
        formatter = CompactFormatter(workspace)

        result = formatter.transform_call_hierarchy_outgoing([call_hierarchy_outgoing])

        assert len(result) == 1
        assert result[0].name == "callee_func"
        assert result[0].kind == 12
        assert result[0].kind_name == "Function"


# =============================================================================
# TEST SCENARIO B7: transform_completions() with CompletionItem
# =============================================================================


class TestTransformCompletionsPydantic:
    """RED: transform_completions() must accept Pydantic CompletionItem models."""

    def test_transform_completions_accepts_pydantic(
        self, lsp_completion: CompletionItem
    ) -> None:
        """RED: transform_completions must accept list[CompletionItem] input."""
        workspace = Path("/workspace")
        file_path = "/workspace/src/main.py"
        formatter = CompactFormatter(workspace)

        result = formatter.transform_completions([lsp_completion], file_path=file_path)

        assert len(result) == 1
        assert result[0].label == "my_func"
        assert result[0].kind == 6

    def test_transform_completions_handles_markup_documentation(
        self, lsp_completion: CompletionItem
    ) -> None:
        """RED: must correctly handle MarkupContent documentation."""
        workspace = Path("/workspace")
        file_path = "/workspace/src/main.py"
        formatter = CompactFormatter(workspace)

        result = formatter.transform_completions([lsp_completion], file_path=file_path)

        # Documentation should be extracted from MarkupContent
        assert result[0].documentation == "A function"


# =============================================================================
# TEST SCENARIO B8: transform_hover() with Hover
# =============================================================================


class TestTransformHoverPydantic:
    """RED: transform_hover() must accept Pydantic Hover models."""

    def test_transform_hover_accepts_pydantic(self, lsp_hover_markup: Hover) -> None:
        """RED: transform_hover must accept Hover input."""
        workspace = Path("/workspace")
        file_path = "/workspace/src/main.py"
        formatter = CompactFormatter(workspace)

        result = formatter.transform_hover(lsp_hover_markup, file_path=file_path)

        assert result is not None
        assert "my_func()" in result.content

    def test_transform_hover_handles_markup_contents(
        self, lsp_hover_markup: Hover
    ) -> None:
        """RED: must correctly handle MarkupContent in Hover.contents."""
        workspace = Path("/workspace")
        file_path = "/workspace/src/main.py"
        formatter = CompactFormatter(workspace)

        result = formatter.transform_hover(lsp_hover_markup, file_path=file_path)

        assert result is not None
        # MarkupContent should be extracted as value
        assert "```python" in result.content
