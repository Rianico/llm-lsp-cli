# ruff: noqa: E501 - LSP fixture data is necessarily verbose

"""Unit tests for SymbolTransformer hierarchical depth control.

This module tests the new depth-controlled symbol traversal functionality
as specified in ADR-0013.
"""

import pytest

from llm_lsp_cli.output import formatter
from llm_lsp_cli.output.formatter import CompactFormatter, SymbolRecord

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_class_symbol() -> dict:
    """Single class symbol with no children."""
    return {
        "name": "MyClass",
        "kind": 5,  # Class
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 1}},
        "selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 13}},
    }


@pytest.fixture
def class_with_methods() -> dict:
    """Class symbol with method children."""
    return {
        "name": "MyClass",
        "kind": 5,
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 30, "character": 1}},
        "selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 13}},
        "detail": None,
        "tags": [],
        "children": [
            {
                "name": "__init__",
                "kind": 6,  # Method
                "range": {"start": {"line": 1, "character": 4}, "end": {"line": 5, "character": 20}},
                "selectionRange": {"start": {"line": 1, "character": 8}, "end": {"line": 1, "character": 16}},
                "detail": "(self, x: int)",
                "tags": [],
            },
            {
                "name": "process",
                "kind": 6,
                "range": {"start": {"line": 7, "character": 4}, "end": {"line": 15, "character": 20}},
                "selectionRange": {"start": {"line": 7, "character": 8}, "end": {"line": 7, "character": 15}},
                "detail": None,
                "tags": [1],  # Deprecated
            },
        ],
    }


@pytest.fixture
def deeply_nested_symbol_tree() -> dict:
    """Class with method with nested function with variable (4 levels)."""
    return {
        "name": "OuterClass",
        "kind": 5,
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 50, "character": 1}},
        "selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 16}},
        "children": [
            {
                "name": "outer_method",
                "kind": 6,
                "range": {"start": {"line": 1, "character": 4}, "end": {"line": 40, "character": 20}},
                "selectionRange": {"start": {"line": 1, "character": 8}, "end": {"line": 1, "character": 20}},
                "children": [
                    {
                        "name": "nested_function",
                        "kind": 12,  # Function
                        "range": {"start": {"line": 5, "character": 8}, "end": {"line": 20, "character": 20}},
                        "selectionRange": {"start": {"line": 5, "character": 12}, "end": {"line": 5, "character": 27}},
                        "children": [
                            {
                                "name": "local_var",
                                "kind": 13,  # Variable
                                "range": {"start": {"line": 6, "character": 12}, "end": {"line": 6, "character": 25}},
                                "selectionRange": {"start": {"line": 6, "character": 12}, "end": {"line": 6, "character": 21}},
                            }
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def multi_symbol_tree() -> list[dict]:
    """Multiple top-level symbols with varying depths."""
    return [
        {
            "name": "CONSTANT",
            "kind": 14,  # Constant
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 20}},
        },
        {
            "name": "HelperClass",
            "kind": 5,
            "range": {"start": {"line": 2, "character": 0}, "end": {"line": 10, "character": 1}},
            "children": [
                {"name": "helper_method", "kind": 6, "range": {"start": {"line": 3, "character": 4}, "end": {"line": 5, "character": 20}}}
            ],
        },
        {
            "name": "top_level_function",
            "kind": 12,
            "range": {"start": {"line": 12, "character": 0}, "end": {"line": 20, "character": 1}},
        },
    ]


@pytest.fixture
def symbol_with_missing_children() -> dict:
    """Symbol dict without children key (edge case)."""
    return {
        "name": "SimpleFunc",
        "kind": 12,
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 1}},
    }


@pytest.fixture
def symbol_with_none_children() -> dict:
    """Symbol with explicit null children."""
    return {
        "name": "SimpleFunc",
        "kind": 12,
        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 1}},
        "children": None,
    }


# =============================================================================
# Depth Control Tests
# =============================================================================


class TestDepthControl:
    """Tests for depth-controlled symbol traversal."""

    def test_depth_0_returns_top_level_only(self, class_with_methods: dict) -> None:
        """Depth 0 limits to root symbols, no children arrays."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([class_with_methods], depth=0)

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].children == []

    def test_depth_1_returns_immediate_children(self, class_with_methods: dict) -> None:
        """Depth 1 includes one level of children."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([class_with_methods], depth=1)

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert len(result[0].children) == 2
        # Children should have empty children arrays (depth exhausted)
        assert result[0].children[0].children == []
        assert result[0].children[1].children == []

    def test_depth_2_returns_two_levels(self, deeply_nested_symbol_tree: dict) -> None:
        """Depth 2 includes two levels of nested symbols."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([deeply_nested_symbol_tree], depth=2)

        assert len(result) == 1
        assert result[0].name == "OuterClass"
        assert len(result[0].children) == 1
        assert result[0].children[0].name == "outer_method"
        # nested_function should be present at depth 2
        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].name == "nested_function"
        # local_var should NOT be present (depth exhausted)
        assert result[0].children[0].children[0].children == []

    def test_depth_unlimited_returns_full_tree(self, deeply_nested_symbol_tree: dict) -> None:
        """Depth -1 traverses all levels."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([deeply_nested_symbol_tree], depth=-1)

        assert len(result) == 1
        assert result[0].name == "OuterClass"
        assert len(result[0].children) == 1
        assert result[0].children[0].name == "outer_method"
        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].name == "nested_function"
        # local_var should be present (unlimited depth)
        assert len(result[0].children[0].children[0].children) == 1
        assert result[0].children[0].children[0].children[0].name == "local_var"

    def test_depth_exceeds_actual_depth(self, simple_class_symbol: dict) -> None:
        """Request depth > actual depth returns actual depth, no error."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([simple_class_symbol], depth=5)

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].children == []


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in symbol transformation."""

    def test_empty_symbols_returns_empty(self) -> None:
        """Empty input returns empty output."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([], depth=-1)
        assert result == []

    def test_missing_children_field(self, symbol_with_missing_children: dict) -> None:
        """Symbol without children key gets empty children array."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([symbol_with_missing_children], depth=-1)

        assert len(result) == 1
        assert result[0].name == "SimpleFunc"
        assert result[0].children == []

    def test_none_children_field(self, symbol_with_none_children: dict) -> None:
        """Symbol with explicit null children gets empty children array."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([symbol_with_none_children], depth=-1)

        assert len(result) == 1
        assert result[0].name == "SimpleFunc"
        assert result[0].children == []

    def test_single_symbol_no_children(self, simple_class_symbol: dict) -> None:
        """Leaf symbol gets empty children array."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([simple_class_symbol], depth=-1)

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].children == []


# =============================================================================
# Field Transformation Tests
# =============================================================================


class TestFieldTransformation:
    """Tests for field transformation in hierarchical output."""

    def test_kind_translated_to_kind_name(self, simple_class_symbol: dict) -> None:
        """Numeric kind is translated to kind_name string."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([simple_class_symbol], depth=-1)

        assert len(result) == 1
        assert result[0].kind == 5
        assert result[0].kind_name == "Class"

    def test_unknown_kind_shows_numeric(self) -> None:
        """Unmapped kind value shows Unknown(N) format."""
        formatter = CompactFormatter("/workspace")
        symbol = {
            "name": "UnknownSymbol",
            "kind": 999,
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 1}},
        }
        result = formatter.transform_symbols([symbol], depth=-1)

        assert len(result) == 1
        assert result[0].kind_name == "Unknown(999)"

    def test_range_formatted_compact(self) -> None:
        """Range object is converted to compact string format (1-based)."""
        formatter = CompactFormatter("/workspace")
        symbol = {
            "name": "TestFunc",
            "kind": 12,
            "range": {
                "start": {"line": 21, "character": 5},
                "end": {"line": 21, "character": 15},
            },
        }
        result = formatter.transform_symbols([symbol], depth=-1)

        assert len(result) == 1
        # 0-based line 21 -> 1-based line 22
        assert result[0].range.to_compact() == "22:6-22:16"

    def test_selection_range_included_when_present(self, simple_class_symbol: dict) -> None:
        """SelectionRange is preserved and formatted."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([simple_class_symbol], depth=-1)

        assert len(result) == 1
        assert result[0].selection_range is not None
        # 0-based line 0 -> 1-based line 1
        assert result[0].selection_range.to_compact() == "1:7-1:14"

    def test_detail_field_preserved(self, class_with_methods: dict) -> None:
        """Detail field is passed through unchanged."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([class_with_methods], depth=-1)

        assert len(result) == 1
        assert len(result[0].children) == 2
        # __init__ has detail
        assert result[0].children[0].detail == "(self, x: int)"

    def test_tags_field_preserved(self, class_with_methods: dict) -> None:
        """Tags field is passed through unchanged."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([class_with_methods], depth=-1)

        assert len(result) == 1
        assert len(result[0].children) == 2
        # process has tags [1]
        assert result[0].children[1].tags == [1]

    def test_null_detail_becomes_none(self, class_with_methods: dict) -> None:
        """Null or missing detail becomes None in output."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([class_with_methods], depth=-1)

        assert len(result) == 1
        # process method has detail: None
        assert result[0].children[1].detail is None


# =============================================================================
# Parent Tracking Tests (for CSV format)
# =============================================================================


class TestParentTracking:
    """Tests for parent field tracking in hierarchical symbols."""

    def test_parent_field_tracks_hierarchy(self, class_with_methods: dict) -> None:
        """Child symbols have parent field set to parent name."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([class_with_methods], depth=-1)

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].parent is None  # Top-level has no parent

        # Children should have parent set
        for child in result[0].children:
            assert child.parent == "MyClass"

    def test_nested_parent_chain(self, deeply_nested_symbol_tree: dict) -> None:
        """Multi-level parent chain is tracked correctly."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols([deeply_nested_symbol_tree], depth=-1)

        # OuterClass (parent=None)
        assert result[0].name == "OuterClass"
        assert result[0].parent is None

        # outer_method (parent=OuterClass)
        method = result[0].children[0]
        assert method.name == "outer_method"
        assert method.parent == "OuterClass"

        # nested_function (parent=outer_method)
        func = method.children[0]
        assert func.name == "nested_function"
        assert func.parent == "outer_method"

        # local_var (parent=nested_function)
        var = func.children[0]
        assert var.name == "local_var"
        assert var.parent == "nested_function"

    def test_top_level_has_no_parent(self, multi_symbol_tree: list[dict]) -> None:
        """Root symbols have parent=None."""
        formatter = CompactFormatter("/workspace")
        result = formatter.transform_symbols(multi_symbol_tree, depth=-1)

        for rec in result:
            assert rec.parent is None


# =============================================================================
# SymbolRecord Extended Fields Tests
# =============================================================================


class TestSymbolRecordFields:
    """Tests for SymbolRecord dataclass extended fields."""

    def test_symbol_record_has_parent_field(self) -> None:
        """SymbolRecord has parent field with default None."""
        rec = SymbolRecord(
            file="test.py",
            name="func",
            kind=12,
            kind_name="Function",
            range=formatter.Range(
                formatter.Position(0, 0),
                formatter.Position(10, 0),
            ),
        )
        assert hasattr(rec, "parent")
        assert rec.parent is None

    def test_symbol_record_has_children_field(self) -> None:
        """SymbolRecord has children field with default empty list."""
        rec = SymbolRecord(
            file="test.py",
            name="func",
            kind=12,
            kind_name="Function",
            range=formatter.Range(
                formatter.Position(0, 0),
                formatter.Position(10, 0),
            ),
        )
        assert hasattr(rec, "children")
        assert rec.children == []

    def test_symbol_record_immutable_fields(self) -> None:
        """Position and Range remain immutable/frozen."""
        from llm_lsp_cli.output.formatter import Position, Range

        pos = Position(1, 2)
        with pytest.raises(AttributeError):
            pos.line = 5  # type: ignore[misc]

        range_obj = Range(Position(0, 0), Position(10, 0))
        with pytest.raises(AttributeError):
            range_obj.start = Position(5, 5)  # type: ignore[misc]
