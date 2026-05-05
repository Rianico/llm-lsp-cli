"""Tests for Pydantic model validation of LSP types.

These tests verify that LSP response types are properly validated Pydantic models
with camelCase aliasing support and proper nested validation.
"""

import pytest
from pydantic import ValidationError


class TestPositionModel:
    """Tests for Position Pydantic model validation."""

    def test_position_valid(self) -> None:
        """Valid Position with int line/character."""
        from llm_lsp_cli.lsp.types import Position

        data = {"line": 10, "character": 5}
        pos = Position.model_validate(data)
        assert pos.line == 10
        assert pos.character == 5

    def test_position_invalid_type(self) -> None:
        """Position with string line raises ValidationError."""
        from llm_lsp_cli.lsp.types import Position

        data = {"line": "ten", "character": 5}  # type: ignore
        with pytest.raises(ValidationError):
            Position.model_validate(data)

    def test_position_serialization(self) -> None:
        """Position serializes to dict with correct field names."""
        from llm_lsp_cli.lsp.types import Position

        pos = Position(line=10, character=5)
        assert pos.model_dump() == {"line": 10, "character": 5}

    def test_position_missing_field(self) -> None:
        """Position with missing field raises ValidationError."""
        from llm_lsp_cli.lsp.types import Position

        data = {"line": 10}  # missing character
        with pytest.raises(ValidationError):
            Position.model_validate(data)


class TestRangeModel:
    """Tests for Range Pydantic model validation."""

    def test_range_valid(self) -> None:
        """Valid Range with start/end Positions."""
        from llm_lsp_cli.lsp.types import Range

        data = {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 10},
        }
        rng = Range.model_validate(data)
        assert rng.start.line == 1
        assert rng.end.character == 10

    def test_range_nested_validation_error(self) -> None:
        """Range with invalid Position raises ValidationError."""
        from llm_lsp_cli.lsp.types import Range

        data = {
            "start": {"line": "one", "character": 0},  # type: ignore
            "end": {"line": 1, "character": 10},
        }
        with pytest.raises(ValidationError):
            Range.model_validate(data)

    def test_range_serialization(self) -> None:
        """Range serializes to nested dict structure."""
        from llm_lsp_cli.lsp.types import Range

        rng = Range.model_validate(
            {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 10}}
        )
        result = rng.model_dump()
        assert result == {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 10},
        }


class TestLocationModel:
    """Tests for Location Pydantic model validation."""

    def test_location_valid(self) -> None:
        """Valid Location with uri and range."""
        from llm_lsp_cli.lsp.types import Location

        data = {
            "uri": "file:///test.py",
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
        }
        loc = Location.model_validate(data)
        assert loc.uri == "file:///test.py"
        assert loc.range.start.line == 0

    def test_location_nested_range_validation(self) -> None:
        """Location validates nested Range structure."""
        from llm_lsp_cli.lsp.types import Location

        data = {
            "uri": "file:///test.py",
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": "invalid", "character": 10},  # type: ignore
            },
        }
        with pytest.raises(ValidationError):
            Location.model_validate(data)


class TestHoverModel:
    """Tests for Hover Pydantic model validation."""

    def test_hover_with_markup_content(self) -> None:
        """Hover with MarkupContent validates correctly."""
        from llm_lsp_cli.lsp.types import Hover

        data = {
            "contents": {"kind": "markdown", "value": "test hover"},
            "range": None,
        }
        hover = Hover.model_validate(data)
        assert hover.contents is not None

    def test_hover_none_range(self) -> None:
        """Hover with None range is valid."""
        from llm_lsp_cli.lsp.types import Hover

        data = {
            "contents": {"kind": "plaintext", "value": "test"},
            "range": None,
        }
        hover = Hover.model_validate(data)
        assert hover.range is None


class TestInitializeResultModel:
    """Tests for InitializeResult Pydantic model with camelCase aliasing."""

    def test_initialize_result_with_server_info(self) -> None:
        """InitializeResult validates camelCase serverInfo via alias."""
        from llm_lsp_cli.lsp.types import InitializeResult

        data = {
            "capabilities": {"hoverProvider": True},
            "serverInfo": {"name": "test-server", "version": "1.0"},
        }
        result = InitializeResult.model_validate(data)
        assert result.server_info is not None
        assert result.server_info.get("name") == "test-server"

    def test_initialize_result_optional_server_info(self) -> None:
        """InitializeResult without serverInfo is valid."""
        from llm_lsp_cli.lsp.types import InitializeResult

        data = {"capabilities": {}}
        result = InitializeResult.model_validate(data)
        assert result.server_info is None

    def test_initialize_result_camel_case_field_accepted(self) -> None:
        """InitializeResult accepts camelCase serverInfo in input."""
        from llm_lsp_cli.lsp.types import InitializeResult

        # Input uses LSP spec camelCase
        data = {
            "capabilities": {},
            "serverInfo": {"name": "pyright", "version": "1.0"},
        }
        result = InitializeResult.model_validate(data)
        # Python attribute uses snake_case
        assert result.server_info is not None


class TestCompletionListModel:
    """Tests for CompletionList Pydantic model with isIncomplete alias."""

    def test_completion_list_valid(self) -> None:
        """CompletionList validates with isIncomplete alias."""
        from llm_lsp_cli.lsp.types import CompletionList

        data = {
            "isIncomplete": False,
            "items": [{"label": "test_func", "kind": 3}],
        }
        result = CompletionList.model_validate(data)
        assert result.is_incomplete is False
        assert len(result.items) == 1

    def test_completion_list_camel_case_input(self) -> None:
        """CompletionList accepts camelCase isIncomplete."""
        from llm_lsp_cli.lsp.types import CompletionList

        data = {"isIncomplete": True, "items": []}
        result = CompletionList.model_validate(data)
        assert result.is_incomplete is True


class TestDiagnosticModel:
    """Tests for Diagnostic Pydantic model validation."""

    def test_diagnostic_valid(self) -> None:
        """Diagnostic validates with required fields."""
        from llm_lsp_cli.lsp.types import Diagnostic

        data = {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
            "message": "Undefined variable",
            "severity": 1,
        }
        diag = Diagnostic.model_validate(data)
        assert diag.message == "Undefined variable"
        assert diag.severity == 1

    def test_diagnostic_optional_fields(self) -> None:
        """Diagnostic validates with optional fields."""
        from llm_lsp_cli.lsp.types import Diagnostic

        data = {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
            "message": "Error",
            "code": "E001",
            "source": "linter",
        }
        diag = Diagnostic.model_validate(data)
        assert diag.code == "E001"
        assert diag.source == "linter"


class TestCallHierarchyIncomingCallModel:
    """Tests for CallHierarchyIncomingCall with reserved word alias."""

    def test_call_hierarchy_incoming_call_from_alias(self) -> None:
        """CallHierarchyIncomingCall uses from_ field with 'from' alias."""
        from llm_lsp_cli.lsp.types import CallHierarchyIncomingCall

        data = {
            "from": {
                "name": "caller",
                "kind": 12,
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            },
            "fromRanges": [
                {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 5},
                }
            ],
        }
        call = CallHierarchyIncomingCall.model_validate(data)
        assert call.from_.name == "caller"

    def test_call_hierarchy_incoming_call_python_field_name(self) -> None:
        """CallHierarchyIncomingCall allows from_ as Python field name."""
        from llm_lsp_cli.lsp.types import CallHierarchyIncomingCall

        # When creating from Python, use from_
        data = {
            "from_": {
                "name": "caller",
                "kind": 12,
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            },
            "fromRanges": [],
        }
        call = CallHierarchyIncomingCall.model_validate(data)
        assert call.from_.name == "caller"


class TestCallHierarchyOutgoingCallModel:
    """Tests for CallHierarchyOutgoingCall model validation."""

    def test_call_hierarchy_outgoing_call_valid(self) -> None:
        """CallHierarchyOutgoingCall validates with 'to' field."""
        from llm_lsp_cli.lsp.types import CallHierarchyOutgoingCall

        data = {
            "to": {
                "name": "callee",
                "kind": 12,
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 10},
                },
            },
            "fromRanges": [],
        }
        call = CallHierarchyOutgoingCall.model_validate(data)
        assert call.to.name == "callee"


class TestModelIgnoresExtraFields:
    """Tests for forward compatibility with extra fields."""

    def test_position_ignores_extra_fields(self) -> None:
        """Pydantic models ignore extra fields from future LSP spec."""
        from llm_lsp_cli.lsp.types import Position

        data = {
            "line": 10,
            "character": 5,
            "futureField": "ignored",  # Not in current spec
        }
        pos = Position.model_validate(data)
        assert pos.line == 10
        # Extra field should not cause error or appear on model
        assert not hasattr(pos, "futureField")


class TestNoTypedDictRemains:
    """Tests to verify TypedDict types are converted to Pydantic."""

    def test_types_are_pydantic_models(self) -> None:
        """All LSP types should be Pydantic BaseModel subclasses."""
        from pydantic import BaseModel

        from llm_lsp_cli.lsp import types as lsp

        types_to_check = [
            lsp.Position,
            lsp.Range,
            lsp.Location,
            lsp.Hover,
            lsp.InitializeResult,
            lsp.CompletionList,
            lsp.Diagnostic,
            lsp.CallHierarchyIncomingCall,
            lsp.CallHierarchyOutgoingCall,
        ]

        for typ in types_to_check:
            assert issubclass(typ, BaseModel), f"{typ.__name__} should be a Pydantic model"

    def test_no_typeddict_in_types_module(self) -> None:
        """No TypedDict classes should remain in types module."""
        import ast
        from pathlib import Path

        types_file = Path("src/llm_lsp_cli/lsp/types.py")
        content = types_file.read_text()
        tree = ast.parse(content)

        typeddict_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "TypedDict":
                        typeddict_classes.append(node.name)
                    elif isinstance(base, ast.Attribute) and base.attr == "TypedDict":
                        typeddict_classes.append(node.name)

        assert len(typeddict_classes) == 0, f"Found TypedDict classes: {typeddict_classes}"
