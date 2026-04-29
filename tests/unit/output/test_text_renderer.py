"""Unit tests for TextRenderer tree format output.

This module tests the TextRenderer class for tree-structured TEXT format
as specified in ADR-0014.
"""

from typing import Any

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
        """Complete field format: name (kind_name), range: <range>, selection_range: <sel>, tags: [<tags>]"""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Should include all fields
        assert "MyClass" in result
        assert "(Class)" in result  # kind_name, not numeric kind
        assert "range: 1:1-50:1" in result  # range with prefix
        assert "selection_range: 1:7-1:14" in result  # selection_range with prefix
        assert "tags: [@deprecated]" in result  # tags with prefix
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
        assert "Func (Function), range: 5:1-10:1" in result  # Comma-separated format
        assert "selection_range" not in result
        assert "tags:" not in result  # No empty tags

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
        """Range format must be compact line:char-line:char (bare format)."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        # Must use compact format (bare, no brackets)
        assert "1:1-50:1" in result
        assert "start" not in result.lower()  # No nested position objects

    def test_selection_range_format_compact(self, simple_node) -> None:
        """Selection range format must be compact with selection_range: prefix."""
        from llm_lsp_cli.output.text_renderer import render_text

        result = render_text((simple_node,))
        assert "selection_range: 1:7-1:14" in result


class TestADR0014Example:
    """Tests matching the exact ADR-0014 example output."""

    def test_exact_adr_example(self) -> None:
        """Output matches ADR-0014 example with bare range format."""
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

        # Verify exact structure per new format (comma-separated with prefixes)
        assert lines[0] == "file.py:"
        assert "├── MyClass (Class), range: 1:1-50:1, selection_range: 1:5-1:12, tags: [@deprecated]" in lines[1]
        assert "│   ├── __init__ (Constructor), range: 10:1-25:1, selection_range: 10:5-10:13" in lines[2]
        assert "│   └── method (Method), range: 30:1-45:1, selection_range: 30:5-30:11" in lines[3]
        assert "└── helper (Function), range: 55:1-80:1, selection_range: 55:1-55:8" in lines[4]


# =============================================================================
# New Format Tests: Diagnostic and Symbol TEXT Format Modification
# =============================================================================


@pytest.fixture
def sample_diagnostic_full() -> dict[str, Any]:
    """Diagnostic with all fields present."""
    return {
        "severity_name": "Hint",
        "message": '"method" is not accessed',
        "code": "reportUnusedParameter",
        "range": "229:42-229:48",
        "tags": ["Unnecessary"],
    }


@pytest.fixture
def sample_diagnostic_minimal() -> dict[str, Any]:
    """Diagnostic with only required fields."""
    return {
        "severity_name": "Error",
        "message": "undefined variable",
        "range": "10:5-10:12",
    }


@pytest.fixture
def sample_symbol_full() -> dict[str, Any]:
    """Symbol with all fields present."""
    return {
        "name": "UNIXServer",
        "kind_name": "Class",
        "range": "23:1-232:13",
        "selection_range": "23:7-23:17",
    }


@pytest.fixture
def sample_symbol_minimal() -> dict[str, Any]:
    """Symbol with only required fields."""
    return {
        "name": "my_function",
        "kind_name": "Function",
        "range": "10:1-50:1",
    }


@pytest.fixture
def sample_grouped_diagnostics() -> list[dict[str, Any]]:
    """Grouped diagnostics data."""
    return [
        {
            "file": "src/main.py",
            "diagnostics": [
                {"severity_name": "Error", "message": "syntax error", "range": "10:1-10:10"},
                {
                    "severity_name": "Warning",
                    "message": "unused import",
                    "code": "F401",
                    "range": "1:1-1:15",
                },
            ],
        }
    ]


@pytest.fixture
def sample_grouped_symbols() -> list[dict[str, Any]]:
    """Grouped symbols data."""
    return [
        {
            "file": "src/models.py",
            "symbols": [
                {
                    "name": "User",
                    "kind_name": "Class",
                    "range": "1:1-50:1",
                    "selection_range": "1:7-1:11",
                },
                {"name": "get_user", "kind_name": "Function", "range": "52:1-60:1"},
            ],
        }
    ]


# =============================================================================
# D1-D8: Diagnostic Format Tests
# =============================================================================


class TestDiagnosticLineFormat:
    """Tests for new diagnostic TEXT format: severity: message, code: X, range: Y, tags: [Z]"""

    def test_d1_diagnostic_full_fields(self, sample_diagnostic_full: dict[str, Any]) -> None:
        """D1: Full diagnostic with all fields present."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        result = _render_diagnostic_line(sample_diagnostic_full)
        # New format: severity: message, code: <code>, range: <range>, tags: [<tags>]
        expected = (
            'Hint: "method" is not accessed, code: reportUnusedParameter, '
            "range: 229:42-229:48, tags: [Unnecessary]"
        )
        assert result == expected

    def test_d2_diagnostic_no_code(self, sample_diagnostic_minimal: dict[str, Any]) -> None:
        """D2: Diagnostic without code field."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        result = _render_diagnostic_line(sample_diagnostic_minimal)
        # Code field omitted when not present
        assert result == "Error: undefined variable, range: 10:5-10:12"

    def test_d3_diagnostic_no_tags(self) -> None:
        """D3: Diagnostic with code but no tags."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        diag = {
            "severity_name": "Warning",
            "message": "unused import",
            "code": "F401",
            "range": "1:1-1:15",
        }
        result = _render_diagnostic_line(diag)
        # Tags field omitted when not present
        assert result == "Warning: unused import, code: F401, range: 1:1-1:15"

    def test_d4_diagnostic_empty_tags_omitted(self) -> None:
        """D4: Diagnostic with empty tags list - tags field omitted."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        diag = {
            "severity_name": "Information",
            "message": "docstring missing",
            "range": "5:1-5:20",
            "tags": [],
        }
        result = _render_diagnostic_line(diag)
        # Empty tags list should be omitted
        assert result == "Information: docstring missing, range: 5:1-5:20"

    def test_d5_diagnostic_multiple_tags(self) -> None:
        """D5: Diagnostic with multiple tags."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        diag = {
            "severity_name": "Hint",
            "message": "deprecated function",
            "code": "DEP001",
            "range": "100:1-100:50",
            "tags": ["Unnecessary", "Deprecated"],
        }
        result = _render_diagnostic_line(diag)
        expected = (
            "Hint: deprecated function, code: DEP001, range: 100:1-100:50, "
            "tags: [Unnecessary, Deprecated]"
        )
        assert result == expected

    def test_d6_diagnostic_special_chars_message(self) -> None:
        """D6: Diagnostic with special characters in message."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        diag = {
            "severity_name": "Error",
            "message": "Type mismatch: expected 'string', got 'number'",
            "code": "TS2345",
            "range": "20:10-20:25",
        }
        result = _render_diagnostic_line(diag)
        expected = (
            "Error: Type mismatch: expected 'string', got 'number', "
            "code: TS2345, range: 20:10-20:25"
        )
        assert result == expected

    def test_d7_diagnostic_multiline_message(self) -> None:
        """D7: Diagnostic with multiline message (newlines preserved)."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        diag = {
            "severity_name": "Error",
            "message": "Line 1\nLine 2\nLine 3",
            "range": "1:1-1:10",
        }
        result = _render_diagnostic_line(diag)
        # Newlines in message preserved as-is
        assert result == "Error: Line 1\nLine 2\nLine 3, range: 1:1-1:10"

    def test_d8_diagnostic_numeric_code(self) -> None:
        """D8: Diagnostic with numeric code (should convert to string)."""
        from llm_lsp_cli.output.text_renderer import _render_diagnostic_line

        diag = {
            "severity_name": "Error",
            "message": "syntax error",
            "code": 123,
            "range": "5:1-5:5",
        }
        result = _render_diagnostic_line(diag)
        # Numeric code should be rendered as string
        assert result == "Error: syntax error, code: 123, range: 5:1-5:5"


# =============================================================================
# S1-S6: Symbol Format Tests
# =============================================================================


class TestSymbolLineFormat:
    """Tests for new symbol TEXT format: name (kind), range: X, selection_range: Y"""

    def test_s1_symbol_full_fields(self, sample_symbol_full: dict[str, Any]) -> None:
        """S1: Full symbol with all fields present."""
        from llm_lsp_cli.output.text_renderer import _render_symbol_line

        result = _render_symbol_line(sample_symbol_full)
        # New format: name (kind_name), range: <range>, selection_range: <selection_range>
        assert result == "UNIXServer (Class), range: 23:1-232:13, selection_range: 23:7-23:17"

    def test_s2_symbol_no_selection_range(self, sample_symbol_minimal: dict[str, Any]) -> None:
        """S2: Symbol without selection_range field."""
        from llm_lsp_cli.output.text_renderer import _render_symbol_line

        result = _render_symbol_line(sample_symbol_minimal)
        # selection_range omitted when not present
        assert result == "my_function (Function), range: 10:1-50:1"

    def test_s3_symbol_none_selection_range_omitted(self) -> None:
        """S3: Symbol with None selection_range - field omitted."""
        from llm_lsp_cli.output.text_renderer import _render_symbol_line

        symbol = {
            "name": "my_variable",
            "kind_name": "Variable",
            "range": "5:1-5:20",
            "selection_range": None,
        }
        result = _render_symbol_line(symbol)
        # None selection_range should be omitted
        assert result == "my_variable (Variable), range: 5:1-5:20"

    def test_s4_symbol_special_chars_name(self) -> None:
        """S4: Symbol with special characters in name."""
        from llm_lsp_cli.output.text_renderer import _render_symbol_line

        symbol = {
            "name": "__init__",
            "kind_name": "Method",
            "range": "15:5-20:30",
            "selection_range": "15:9-15:17",
        }
        result = _render_symbol_line(symbol)
        assert result == "__init__ (Method), range: 15:5-20:30, selection_range: 15:9-15:17"

    def test_s5_symbol_long_name(self) -> None:
        """S5: Symbol with long name (formatting should still be correct)."""
        from llm_lsp_cli.output.text_renderer import _render_symbol_line

        symbol = {
            "name": "very_long_function_name_that_might_cause_formatting_issues_in_output",
            "kind_name": "Function",
            "range": "100:1-200:1",
        }
        result = _render_symbol_line(symbol)
        expected = (
            "very_long_function_name_that_might_cause_formatting_issues_in_output "
            "(Function), range: 100:1-200:1"
        )
        assert result == expected

    def test_s6_symbol_unicode_name(self) -> None:
        """S6: Symbol with Unicode characters in name."""
        from llm_lsp_cli.output.text_renderer import _render_symbol_line

        symbol = {
            "name": "process_中文_data",
            "kind_name": "Function",
            "range": "1:1-5:1",
        }
        result = _render_symbol_line(symbol)
        assert result == "process_中文_data (Function), range: 1:1-5:1"


# =============================================================================
# W1-W4: Workspace-Level Grouped Tests
# =============================================================================


class TestWorkspaceGroupedFormat:
    """Tests for workspace-level grouped output with new format."""

    def test_w1_workspace_diagnostics_grouped(self) -> None:
        """W1: Workspace diagnostics with grouped output and new format."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "src/main.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "syntax error", "range": "10:1-10:10"},
                    {
                        "severity_name": "Warning",
                        "message": "unused import",
                        "code": "F401",
                        "range": "1:1-1:15",
                    },
                ],
            },
            {
                "file": "src/utils.py",
                "diagnostics": [
                    {
                        "severity_name": "Hint",
                        "message": '"x" is not accessed',
                        "code": "reportUnusedVariable",
                        "range": "20:5-20:6",
                        "tags": ["Unnecessary"],
                    }
                ],
            },
        ]

        result = render_workspace_diagnostics_grouped(grouped_data)
        lines = result.split("\n")

        # File headers
        assert "src/main.py:" in result
        assert "src/utils.py:" in result

        # Tree connectors
        assert "  ├── Error: syntax error, range: 10:1-10:10" in lines
        assert "  └── Warning: unused import, code: F401, range: 1:1-1:15" in lines
        expected_hint = (
            '  └── Hint: "x" is not accessed, code: reportUnusedVariable, '
            "range: 20:5-20:6, tags: [Unnecessary]"
        )
        assert expected_hint in lines

    def test_w2_workspace_symbols_grouped(self) -> None:
        """W2: Workspace symbols with grouped output and new format."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        grouped_data = [
            {
                "file": "src/models.py",
                "symbols": [
                    {
                        "name": "User",
                        "kind_name": "Class",
                        "range": "1:1-50:1",
                        "selection_range": "1:7-1:11",
                    },
                    {"name": "get_user", "kind_name": "Function", "range": "52:1-60:1"},
                ],
            }
        ]

        result = render_workspace_symbols_grouped(grouped_data)
        lines = result.split("\n")

        assert "src/models.py:" in result
        assert "  ├── User (Class), range: 1:1-50:1, selection_range: 1:7-1:11" in lines
        assert "  └── get_user (Function), range: 52:1-60:1" in lines

    def test_w3_workspace_empty_grouped_diagnostics(self) -> None:
        """W3: Empty grouped diagnostics returns appropriate message."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        result = render_workspace_diagnostics_grouped([])
        assert result == "No diagnostics found."

    def test_w3b_workspace_empty_grouped_symbols(self) -> None:
        """W3b: Empty grouped symbols returns appropriate message."""
        from llm_lsp_cli.output.text_renderer import render_workspace_symbols_grouped

        result = render_workspace_symbols_grouped([])
        assert result == "No symbols found."

    def test_w4_workspace_grouped_with_header(self) -> None:
        """W4: Grouped output with alert header."""
        from llm_lsp_cli.output.text_renderer import render_workspace_diagnostics_grouped

        grouped_data = [
            {
                "file": "test.py",
                "diagnostics": [
                    {"severity_name": "Error", "message": "test error", "range": "1:1-1:10"}
                ],
            }
        ]
        header = "Alert: Workspace diagnostics from pyright"

        result = render_workspace_diagnostics_grouped(grouped_data, header=header)
        lines = result.split("\n")

        assert lines[0] == "Alert: Workspace diagnostics from pyright"
        assert "test.py:" in result
        assert "  └── Error: test error, range: 1:1-1:10" in lines
