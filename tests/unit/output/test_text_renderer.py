"""Unit tests for TextRenderer tree format output.

This module tests the TextRenderer class for tree-structured TEXT format
as specified in ADR-0014.
"""

import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_node():
    """A simple SymbolNode for testing."""
    from llm_lsp_cli.output.symbol_transformer import SymbolNode

    return SymbolNode(
        name="MyClass",
        kind=5,
        kind_name="Class",
        range="1:1-50:1",
        selection_range="1:7-1:14",
        detail="class MyClass",
        tags=("@deprecated",),
        children=(),
        depth=0,
    )


@pytest.fixture
def node_with_children():
    """SymbolNode with nested children."""
    from llm_lsp_cli.output.symbol_transformer import SymbolNode

    child1 = SymbolNode(
        name="method1",
        kind=6,
        kind_name="Method",
        range="2:1-5:1",
        selection_range="2:5-2:12",
        detail=None,
        tags=(),
        children=(),
        depth=1,
    )
    child2 = SymbolNode(
        name="method2",
        kind=6,
        kind_name="Method",
        range="6:1-10:1",
        selection_range=None,
        detail=None,
        tags=(),
        children=(),
        depth=1,
    )
    parent = SymbolNode(
        name="MyClass",
        kind=5,
        kind_name="Class",
        range="1:1-50:1",
        selection_range="1:7-1:14",
        detail=None,
        tags=(),
        children=(child1, child2),
        depth=0,
    )
    return parent


@pytest.fixture
def deeply_nested_nodes():
    """3-level nested SymbolNode structure."""
    from llm_lsp_cli.output.symbol_transformer import SymbolNode

    grandchild = SymbolNode(
        name="local_var",
        kind=13,
        kind_name="Variable",
        range="6:1-6:10",
        selection_range=None,
        detail=None,
        tags=(),
        children=(),
        depth=2,
    )
    child = SymbolNode(
        name="nested_func",
        kind=12,
        kind_name="Function",
        range="5:1-20:1",
        selection_range="5:5-5:16",
        detail=None,
        tags=(),
        children=(grandchild,),
        depth=1,
    )
    parent = SymbolNode(
        name="MyClass",
        kind=5,
        kind_name="Class",
        range="1:1-50:1",
        selection_range="1:7-1:14",
        detail=None,
        tags=(),
        children=(child,),
        depth=0,
    )
    return parent


# =============================================================================
# Category C: TextRenderer Tree Format Tests
# =============================================================================


class TestTextRendererImport:
    """Tests for TextRenderer importability."""

    def test_render_text_can_be_imported(self) -> None:
        """render_text function must be importable."""
        from llm_lsp_cli.output.text_renderer import render_text

        assert render_text is not None


class TestTreeConnectors:
    """Tests for tree connector rendering per ADR-0014."""

    def test_render_intermediate_sibling_uses_box_connector(self) -> None:
        """Intermediate sibling uses ├── connector per ADR-0014."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        child1 = SymbolNode(
            name="Child1",
            kind=6,
            kind_name="Method",
            range="2:1-5:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        child2 = SymbolNode(
            name="Child2",
            kind=6,
            kind_name="Method",
            range="6:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        nodes = (child1, child2)
        result = render_text(nodes)

        # Intermediate sibling MUST use ├── connector
        assert "├── Child1" in result
        # Last sibling MUST use └── connector
        assert "└── Child2" in result

    def test_render_last_sibling_uses_corner_connector(self) -> None:
        """Last sibling uses └── connector per ADR-0014."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        first = SymbolNode(
            name="First",
            kind=6,
            kind_name="Method",
            range="2:1-5:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        last = SymbolNode(
            name="Last",
            kind=6,
            kind_name="Method",
            range="6:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        nodes = (first, last)
        result = render_text(nodes)
        lines = result.split("\n")

        # Last sibling MUST use └── connector
        last_line = [line for line in lines if "Last" in line][0]
        assert "└── Last" in last_line

    def test_render_continuing_parent_prefix(self) -> None:
        """Symbols with more siblings at parent use │   prefix per ADR-0014."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        # Build a structure where MyClass has a sibling (helper)
        # So MyClass children should have │ continuation prefix
        method1 = SymbolNode(
            name="method1",
            kind=6,
            kind_name="Method",
            range="2:1-5:1",
            selection_range="2:5-2:12",
            detail=None,
            tags=(),
            children=(),
            depth=1,
        )
        method2 = SymbolNode(
            name="method2",
            kind=6,
            kind_name="Method",
            range="6:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=1,
        )
        myclass = SymbolNode(
            name="MyClass",
            kind=5,
            kind_name="Class",
            range="1:1-50:1",
            selection_range="1:7-1:14",
            detail=None,
            tags=(),
            children=(method1, method2),
            depth=0,
        )
        helper = SymbolNode(
            name="helper",
            kind=12,
            kind_name="Function",
            range="55:1-80:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )

        result = render_text((myclass, helper))
        lines = result.split("\n")

        # MyClass is NOT last (has helper sibling), so children get │ prefix
        method1_line = [line for line in lines if "method1" in line][0]
        method2_line = [line for line in lines if "method2" in line][0]

        assert "│   ├── method1" in method1_line
        assert "│   └── method2" in method2_line

    def test_render_single_root_node(self, simple_node) -> None:
        """Single root node uses └── connector."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Single root should use └── (it's both first and last)
        assert "└── MyClass" in result


class TestRootLevelConnectors:
    """Tests for root-level tree connectors with multiple siblings."""

    def test_multiple_root_siblings_with_file_header(self) -> None:
        """Root level siblings with file header per ADR-0014 example."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        root1 = SymbolNode(
            name="MyClass",
            kind=5,
            kind_name="Class",
            range="1:1-50:1",
            selection_range="1:5-1:12",
            detail=None,
            tags=("@deprecated",),
            children=(),
            depth=0,
        )
        root2 = SymbolNode(
            name="helper",
            kind=12,
            kind_name="Function",
            range="55:1-80:1",
            selection_range="55:1-55:8",
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )

        result = render_text((root1, root2), file_header="file.py:")
        lines = result.split("\n")

        assert lines[0] == "file.py:"
        # Root level uses 2-space indent + connector
        assert "  ├── MyClass" in lines[1]
        assert "  └── helper" in lines[2]

    def test_multiple_root_siblings_without_file_header(self) -> None:
        """Root level siblings without file header."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        root1 = SymbolNode(
            name="First",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        root2 = SymbolNode(
            name="Second",
            kind=12,
            kind_name="Function",
            range="20:1-30:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )

        result = render_text((root1, root2))

        # Should still have connectors even without file header
        assert "├── First" in result
        assert "└── Second" in result


class TestFieldFormat:
    """Tests for field formatting in TEXT output."""

    def test_render_all_fields_present(self, simple_node) -> None:
        """Complete field format: name (kind_name) [range] sel[selection_range] [tags] detail."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Should include all fields
        assert "MyClass" in result
        assert "(Class)" in result  # kind_name, not numeric kind
        assert "[1:1-50:1]" in result  # range
        assert "sel[1:7-1:14]" in result  # selection_range
        assert "[@deprecated]" in result  # tags
        assert "class MyClass" in result  # detail

    def test_render_omits_null_fields(self) -> None:
        """Null/empty fields must be omitted from output."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        node = SymbolNode(
            name="Func",
            kind=12,
            kind_name="Function",
            range="5:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        result = render_text((node,))
        assert "Func (Function) [5:1-10:1]" in result
        assert "sel[" not in result
        assert "[]" not in result  # No empty tags

    def test_render_no_file_field(self, simple_node) -> None:
        """File field must NOT appear per symbol (redundant with CLI header)."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Should not contain "file=" or similar per-symbol file reference
        assert "file=" not in result.lower()
        assert ".py:" not in result  # No per-symbol file path


class TestMultiFileGrouping:
    """Tests for multi-file grouping in TEXT output."""

    def test_render_groups_by_file(self) -> None:
        """Symbols grouped by file with file header."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        node = SymbolNode(
            name="Test",
            kind=5,
            kind_name="Class",
            range="1:1-10:1",
            selection_range=None,
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )
        result = render_text((node,), file_header="src/models.py:")
        assert "src/models.py:" in result

    def test_render_without_file_header(self, simple_node) -> None:
        """Render works without file header."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Should still render the symbol
        assert "MyClass" in result


class TestEmptyInput:
    """Tests for empty input handling."""

    def test_render_empty_nodes(self) -> None:
        """Empty tuple returns appropriate message."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text(())
        assert result == "No symbols found."


class TestTreeIndentation:
    """Tests for tree indentation and prefix rendering per ADR-0014."""

    def test_root_level_has_two_space_indent(self, simple_node) -> None:
        """Root level nodes start with 2-space indent per ADR-0014."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        lines = result.split("\n")

        # Root level should have 2-space indent + connector
        symbol_line = [line for line in lines if "MyClass" in line][0]
        assert symbol_line.startswith("  └──")

    def test_depth_1_has_correct_indent(self, node_with_children) -> None:
        """Depth 1 children have correct indent based on parent position."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((node_with_children,))
        lines = result.split("\n")

        # MyClass at root (single node, uses └──)
        myclass_line = [line for line in lines if "MyClass" in line][0]
        assert myclass_line.startswith("  └──")

        # Children of a last sibling get spaces prefix (terminated branch)
        method1_line = [line for line in lines if "method1" in line][0]
        method2_line = [line for line in lines if "method2" in line][0]

        # Single root = children get spaces, not │
        assert method1_line.startswith("      ├──")
        assert method2_line.startswith("      └──")

    def test_deeply_nested_structure(self, deeply_nested_nodes) -> None:
        """3-level structure has correct connectors at each level."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((deeply_nested_nodes,))
        lines = result.split("\n")

        # Level 0: MyClass (single root, last sibling)
        myclass_line = [line for line in lines if "MyClass" in line][0]
        assert myclass_line.startswith("  └──")

        # Level 1: nested_func (single child, last sibling)
        # Parent is last sibling, so children get spaces prefix
        func_line = [line for line in lines if "nested_func" in line][0]
        assert func_line.startswith("      └──")

        # Level 2: local_var (single grandchild, last sibling)
        # Parent is last sibling, so children get spaces prefix
        var_line = [line for line in lines if "local_var" in line][0]
        assert var_line.startswith("          └──")


class TestBackwardCompatibility:
    """Tests ensuring existing behavior is preserved."""

    def test_range_format_compact(self, simple_node) -> None:
        """Range format must be compact line:char-line:char."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Must use compact format, not nested object
        assert "[1:1-50:1]" in result
        assert "start" not in result.lower()  # No nested position objects

    def test_selection_range_format_compact(self, simple_node) -> None:
        """Selection range format must be compact with sel[] prefix."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        assert "sel[1:7-1:14]" in result


class TestADR0014Example:
    """Tests matching the exact ADR-0014 example output."""

    def test_exact_adr_example(self) -> None:
        """Output matches ADR-0014 example exactly."""
        from llm_lsp_cli.output.symbol_transformer import SymbolNode
        from llm_lsp_cli.output.text_renderer import render_text

        # Build the exact structure from ADR-0014
        init_method = SymbolNode(
            name="__init__",
            kind=9,
            kind_name="Constructor",
            range="10:1-25:1",
            selection_range="10:5-10:13",
            detail=None,
            tags=(),
            children=(),
            depth=1,
        )
        other_method = SymbolNode(
            name="method",
            kind=6,
            kind_name="Method",
            range="30:1-45:1",
            selection_range="30:5-30:11",
            detail=None,
            tags=(),
            children=(),
            depth=1,
        )
        myclass = SymbolNode(
            name="MyClass",
            kind=5,
            kind_name="Class",
            range="1:1-50:1",
            selection_range="1:5-1:12",
            detail=None,
            tags=("@deprecated",),
            children=(init_method, other_method),
            depth=0,
        )
        helper = SymbolNode(
            name="helper",
            kind=12,
            kind_name="Function",
            range="55:1-80:1",
            selection_range="55:1-55:8",
            detail=None,
            tags=(),
            children=(),
            depth=0,
        )

        result = render_text((myclass, helper), file_header="file.py:")
        lines = result.split("\n")

        # Verify exact structure per ADR-0014 (using kind_name, not numeric kind)
        assert lines[0] == "file.py:"
        assert "├── MyClass (Class) [1:1-50:1] sel[1:5-1:12] [@deprecated]" in lines[1]
        assert "│   ├── __init__ (Constructor) [10:1-25:1] sel[10:5-10:13]" in lines[2]
        assert "│   └── method (Method) [30:1-45:1] sel[30:5-30:11]" in lines[3]
        assert "└── helper (Function) [55:1-80:1] sel[55:1-55:8]" in lines[4]
