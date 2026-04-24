"""Unit tests for SymbolNode dataclass and SymbolTransformer.

This module tests the new SymbolNode frozen dataclass and SymbolTransformer
depth-controlled traversal as specified in ADR-0014.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

# =============================================================================
# Category A: SymbolNode Dataclass Tests
# =============================================================================


class TestSymbolNodeDataclass:
    """Tests for SymbolNode frozen dataclass - ADR-0014 spec."""

    def test_symbol_node_can_be_imported(self) -> None:
        """SymbolNode must be importable from symbol_transformer module."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        assert SymbolNode is not None

    def test_symbol_node_has_required_fields(self) -> None:
        """SymbolNode must have all specified fields with correct types."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        node = SymbolNode(
            name="MyClass",
            kind=5,
            kind_name="Class",
            range="1:1-50:1",
            selection_range="1:7-1:14",
            detail="class detail",
            tags=("@deprecated",),
            children=(),
            depth=0,
        )
        assert node.name == "MyClass"
        assert node.kind == 5
        assert node.kind_name == "Class"
        assert node.range == "1:1-50:1"
        assert node.selection_range == "1:7-1:14"
        assert node.detail == "class detail"
        assert node.tags == ("@deprecated",)
        assert node.children == ()
        assert node.depth == 0

    def test_symbol_node_is_frozen(self) -> None:
        """SymbolNode must be immutable (frozen dataclass)."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        node = SymbolNode(
            name="A",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        with pytest.raises(FrozenInstanceError):
            node.name = "Modified"  # type: ignore[misc]

    def test_symbol_node_equality(self) -> None:
        """Identical SymbolNodes must be equal."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        node1 = SymbolNode(
            name="A",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        node2 = SymbolNode(
            name="A",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        assert node1 == node2

    def test_symbol_node_is_hashable(self) -> None:
        """SymbolNode must be hashable for use in immutable tuples."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        node = SymbolNode(
            name="A",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        # Should not raise
        hash(node)

    def test_symbol_node_children_is_tuple(self) -> None:
        """Children must be tuple[SymbolNode, ...], not list."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        child = SymbolNode(
            name="child",
            kind=6,
            kind_name="Method",
            range="2:1-5:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=1,
        )
        parent = SymbolNode(
            name="parent",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(child,),
            depth=0,
        )
        assert isinstance(parent.children, tuple)
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"

    def test_symbol_node_tags_is_tuple(self) -> None:
        """Tags must be tuple[str, ...], not list."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode

        node = SymbolNode(
            name="A",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=("@deprecated", "@abstract"),
            children=(),
            depth=0,
        )
        assert isinstance(node.tags, tuple)
        assert node.tags == ("@deprecated", "@abstract")


# =============================================================================
# Category B: SymbolTransformer Depth Control Tests
# =============================================================================


@pytest.fixture
def nested_symbols() -> list[dict]:
    """Class with two methods (depth 2 structure)."""
    return [
        {
            "name": "MyClass",
            "kind": 5,
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 30, "character": 1},
            },
            "selectionRange": {
                "start": {"line": 0, "character": 6},
                "end": {"line": 0, "character": 13},
            },
            "children": [
                {
                    "name": "__init__",
                    "kind": 6,
                    "range": {
                        "start": {"line": 1, "character": 4},
                        "end": {"line": 5, "character": 20},
                    },
                    "selectionRange": {
                        "start": {"line": 1, "character": 8},
                        "end": {"line": 1, "character": 16},
                    },
                    "detail": "(self, x: int)",
                },
                {
                    "name": "process",
                    "kind": 6,
                    "range": {
                        "start": {"line": 7, "character": 4},
                        "end": {"line": 15, "character": 20},
                    },
                    "selectionRange": {
                        "start": {"line": 7, "character": 8},
                        "end": {"line": 7, "character": 15},
                    },
                    "tags": [1],
                },
            ],
        },
        {
            "name": "helper",
            "kind": 12,
            "range": {
                "start": {"line": 35, "character": 0},
                "end": {"line": 50, "character": 1},
            },
        },
    ]


@pytest.fixture
def deeply_nested() -> list[dict]:
    """4-level nested structure: Class -> Method -> Function -> Variable."""
    return [
        {
            "name": "OuterClass",
            "kind": 5,
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 50, "character": 1},
            },
            "children": [
                {
                    "name": "outer_method",
                    "kind": 6,
                    "range": {
                        "start": {"line": 1, "character": 4},
                        "end": {"line": 40, "character": 20},
                    },
                    "children": [
                        {
                            "name": "nested_function",
                            "kind": 12,
                            "range": {
                                "start": {"line": 5, "character": 8},
                                "end": {"line": 20, "character": 20},
                            },
                            "children": [
                                {
                                    "name": "local_var",
                                    "kind": 13,
                                    "range": {
                                        "start": {"line": 6, "character": 12},
                                        "end": {"line": 6, "character": 25},
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ]


class TestSymbolTransformer:
    """Tests for SymbolTransformer depth-controlled traversal."""

    def test_transform_symbols_can_be_imported(self) -> None:
        """transform_symbols function must be importable."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        assert transform_symbols is not None

    def test_transform_depth_0_top_level_only(self, nested_symbols: list[dict]) -> None:
        """Depth 0 returns only root symbols, no children."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode, transform_symbols

        result = transform_symbols(nested_symbols, depth_limit=0, workspace=Path("/ws"))

        assert isinstance(result, tuple)
        assert len(result) == 2  # Two top-level symbols
        for node in result:
            assert isinstance(node, SymbolNode)
            assert node.children == ()
            assert node.depth == 0

    def test_transform_depth_1_includes_children(self, nested_symbols: list[dict]) -> None:
        """Depth 1 includes root + immediate children."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        result = transform_symbols(nested_symbols, depth_limit=1, workspace=Path("/ws"))

        assert len(result) == 2
        class_node = result[0]
        assert class_node.name == "MyClass"
        assert len(class_node.children) == 2  # __init__ and process
        for child in class_node.children:
            assert child.children == ()  # No grandchildren
            assert child.depth == 1

    def test_transform_depth_2_two_levels(self, deeply_nested: list[dict]) -> None:
        """Depth 2 includes symbols up to depth 2."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        result = transform_symbols(deeply_nested, depth_limit=2, workspace=Path("/ws"))

        method = result[0].children[0]  # depth 1
        assert method.name == "outer_method"
        assert len(method.children) == 1  # nested_function at depth 2
        assert method.children[0].children == ()  # No depth 3

    def test_transform_depth_unlimited(self, deeply_nested: list[dict]) -> None:
        """Depth -1 traverses all levels."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        result = transform_symbols(deeply_nested, depth_limit=-1, workspace=Path("/ws"))

        func = result[0].children[0].children[0]  # depth 2
        assert func.name == "nested_function"
        assert len(func.children) == 1  # local_var at depth 3
        assert func.children[0].name == "local_var"

    def test_transform_depth_exceeds_actual(self, nested_symbols: list[dict]) -> None:
        """Requesting depth > actual depth returns available depth."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        # Should not error, should return full available tree
        result = transform_symbols(nested_symbols, depth_limit=10, workspace=Path("/ws"))
        assert len(result) == 2

    def test_transform_converts_fields_correctly(self) -> None:
        """LSP fields converted to SymbolNode format."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        symbols = [
            {
                "name": "Test",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 10, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 6},
                    "end": {"line": 0, "character": 10},
                },
                "tags": [1],
                "detail": "detail",
            }
        ]
        result = transform_symbols(symbols, depth_limit=-1, workspace=Path("/ws"))
        node = result[0]
        assert node.range == "1:1-11:1"  # 1-based compact format
        assert node.selection_range == "1:7-1:11"
        assert node.tags == ("@deprecated",)  # Tag 1 -> @deprecated
        assert node.detail == "detail"

    def test_transform_maps_symbol_tags(self) -> None:
        """Numeric tags converted to string representations."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        symbols = [
            {
                "name": "T",
                "kind": 12,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 1, "character": 0},
                },
                "tags": [1, 2],
            }
        ]
        result = transform_symbols(symbols, depth_limit=-1, workspace=Path("/ws"))
        assert result[0].tags == ("@deprecated", "@abstract")

    def test_transform_unknown_tag_fallback(self) -> None:
        """Unknown tags fallback to numeric string."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        symbols = [
            {
                "name": "T",
                "kind": 12,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 1, "character": 0},
                },
                "tags": [999],
            }
        ]
        result = transform_symbols(symbols, depth_limit=-1, workspace=Path("/ws"))
        assert result[0].tags == ("@999",)

    def test_transform_returns_tuple(self) -> None:
        """transform_symbols returns tuple[SymbolNode, ...], not list."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        symbols = [
            {
                "name": "A",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 1, "character": 0},
                },
            }
        ]
        result = transform_symbols(symbols, depth_limit=-1, workspace=Path("/ws"))
        assert isinstance(result, tuple)

    def test_transform_empty_symbols(self) -> None:
        """Empty input returns empty tuple."""
        from llm_lsp_cli.output.symbol_transformer import transform_symbols

        result = transform_symbols([], depth_limit=-1, workspace=Path("/ws"))
        assert result == ()
