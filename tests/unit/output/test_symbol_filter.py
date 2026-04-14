"""Unit tests for symbol_filter module."""

from llm_lsp_cli.output.symbol_filter import (
    VARIABLE_KINDS,
    filter_symbols,
    is_variable_symbol,
)
from llm_lsp_cli.output.verbosity import VerbosityLevel
from tests.fixtures import (
    DEEPLY_NESTED_SYMBOL_RESPONSE,
    MULTI_BRANCH_NESTED,
    PARENT_WITH_ONLY_VARIABLE_CHILDREN,
    SYMBOL_KIND_CLASS,
    SYMBOL_KIND_FIELD,
    SYMBOL_KIND_FUNCTION,
    SYMBOL_KIND_METHOD,
    SYMBOL_KIND_MODULE,
    SYMBOL_KIND_VARIABLE,
)


class TestVariableKindsConstant:
    """Tests for VARIABLE_KINDS frozenset."""

    def test_contains_variable(self) -> None:
        """Verify VARIABLE_KINDS contains SYMBOL_KIND_VARIABLE."""
        assert SYMBOL_KIND_VARIABLE in VARIABLE_KINDS

    def test_contains_field(self) -> None:
        """Verify VARIABLE_KINDS contains SYMBOL_KIND_FIELD."""
        assert SYMBOL_KIND_FIELD in VARIABLE_KINDS

    def test_does_not_contain_class(self) -> None:
        """Verify VARIABLE_KINDS does not contain SYMBOL_KIND_CLASS."""
        assert SYMBOL_KIND_CLASS not in VARIABLE_KINDS

    def test_does_not_contain_function(self) -> None:
        """Verify VARIABLE_KINDS does not contain SYMBOL_KIND_FUNCTION."""
        assert SYMBOL_KIND_FUNCTION not in VARIABLE_KINDS

    def test_is_frozenset(self) -> None:
        """Verify VARIABLE_KINDS is a frozenset (immutable)."""
        assert isinstance(VARIABLE_KINDS, frozenset)


class TestIsVariableSymbol:
    """Tests for is_variable_symbol function."""

    def test_variable_kind_returns_true(self) -> None:
        """Verify symbol with kind=13 returns True."""
        symbol = {"kind": SYMBOL_KIND_VARIABLE}
        assert is_variable_symbol(symbol) is True

    def test_field_kind_returns_true(self) -> None:
        """Verify symbol with kind=8 returns True."""
        symbol = {"kind": SYMBOL_KIND_FIELD}
        assert is_variable_symbol(symbol) is True

    def test_class_kind_returns_false(self) -> None:
        """Verify symbol with kind=5 returns False."""
        symbol = {"kind": SYMBOL_KIND_CLASS}
        assert is_variable_symbol(symbol) is False

    def test_function_kind_returns_false(self) -> None:
        """Verify symbol with kind=12 returns False."""
        symbol = {"kind": SYMBOL_KIND_FUNCTION}
        assert is_variable_symbol(symbol) is False

    def test_method_kind_returns_false(self) -> None:
        """Verify symbol with kind=6 returns False."""
        symbol = {"kind": SYMBOL_KIND_METHOD}
        assert is_variable_symbol(symbol) is False

    def test_missing_kind_returns_false(self) -> None:
        """Verify symbol without 'kind' field returns False."""
        symbol = {}
        assert is_variable_symbol(symbol) is False

    def test_unknown_kind_returns_false(self) -> None:
        """Verify symbol with unknown kind returns False."""
        symbol = {"kind": 99}
        assert is_variable_symbol(symbol) is False

    def test_none_kind_returns_false(self) -> None:
        """Verify symbol with kind=None returns False."""
        symbol = {"kind": None}
        assert is_variable_symbol(symbol) is False


class TestFilterSymbols:
    """Tests for filter_symbols function."""

    def test_empty_list_returns_empty(self) -> None:
        """Verify empty input returns empty list."""
        result = filter_symbols([], VerbosityLevel.NORMAL)
        assert result == []

    def test_normal_excludes_variables(self) -> None:
        """Verify NORMAL verbosity excludes variable and field symbols."""
        symbols = [
            {"kind": SYMBOL_KIND_VARIABLE, "name": "var"},
            {"kind": SYMBOL_KIND_FIELD, "name": "field"},
            {"kind": SYMBOL_KIND_CLASS, "name": "class"},
            {"kind": SYMBOL_KIND_FUNCTION, "name": "func"},
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        assert len(result) == 2
        assert all(s["kind"] in {SYMBOL_KIND_CLASS, SYMBOL_KIND_FUNCTION} for s in result)

    def test_verbose_includes_all(self) -> None:
        """Verify VERBOSE verbosity includes all symbols."""
        symbols = [
            {"kind": SYMBOL_KIND_VARIABLE, "name": "var"},
            {"kind": SYMBOL_KIND_FIELD, "name": "field"},
            {"kind": SYMBOL_KIND_CLASS, "name": "class"},
            {"kind": SYMBOL_KIND_FUNCTION, "name": "func"},
        ]
        result = filter_symbols(symbols, VerbosityLevel.VERBOSE)
        assert len(result) == 4

    def test_all_variables_filtered(self) -> None:
        """Verify NORMAL verbosity filters out all variable symbols."""
        symbols = [
            {"kind": SYMBOL_KIND_VARIABLE, "name": "var1"},
            {"kind": SYMBOL_KIND_VARIABLE, "name": "var2"},
            {"kind": SYMBOL_KIND_VARIABLE, "name": "var3"},
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        assert len(result) == 0

    def test_no_variables_passes_through(self) -> None:
        """Verify non-variable symbols pass through NORMAL filter."""
        symbols = [
            {"kind": SYMBOL_KIND_CLASS, "name": "class"},
            {"kind": SYMBOL_KIND_FUNCTION, "name": "func"},
            {"kind": SYMBOL_KIND_METHOD, "name": "method"},
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        assert len(result) == 3

    def test_debug_includes_all(self) -> None:
        """Verify DEBUG verbosity includes all symbols."""
        symbols = [
            {"kind": SYMBOL_KIND_VARIABLE, "name": "var"},
            {"kind": SYMBOL_KIND_CLASS, "name": "class"},
        ]
        result = filter_symbols(symbols, VerbosityLevel.DEBUG)
        assert len(result) == 2

    def test_mixed_kinds_correct_filtering(self) -> None:
        """Verify mixed symbol list is filtered correctly at NORMAL verbosity."""
        symbols = [
            {"kind": k, "name": f"sym_{k}"}
            for k in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        # Should exclude kind 8 (FIELD) and 13 (VARIABLE)
        assert len(result) == 12
        assert all(s["kind"] not in VARIABLE_KINDS for s in result)

    def test_verbosity_level_ordering(self) -> None:
        """Verify >= VERBOSE includes variable symbols."""
        symbols = [{"kind": SYMBOL_KIND_VARIABLE, "name": "var"}]
        for level in [VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG]:
            result = filter_symbols(symbols, level)
            assert len(result) == 1

    def test_preserves_symbol_data(self) -> None:
        """Verify filter preserves all symbol data."""
        symbols = [
            {
                "name": "MyClass",
                "kind": SYMBOL_KIND_CLASS,
                "location": {"uri": "file:///test.py"},
                "detail": "class MyClass",
            },
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)
        assert len(result) == 1
        assert result[0]["name"] == "MyClass"
        assert result[0]["location"] == {"uri": "file:///test.py"}


class TestFilterSymbolsRecursive:
    """Tests for recursive children filtering."""

    def test_recursive_excludes_nested_variables(self) -> None:
        """Verify nested children are recursively filtered at NORMAL verbosity."""
        symbols = [
            {
                "name": "MyClass",
                "kind": SYMBOL_KIND_CLASS,
                "children": [
                    {"name": "method", "kind": SYMBOL_KIND_METHOD},
                    {"name": "field", "kind": SYMBOL_KIND_FIELD},
                ]
            }
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert result[0]["name"] == "MyClass"
        assert "children" in result[0]
        assert len(result[0]["children"]) == 1
        assert result[0]["children"][0]["name"] == "method"

    def test_recursive_includes_all_at_verbose(self) -> None:
        """Verify VERBOSE verbosity includes all nested symbols."""
        symbols = [
            {
                "name": "MyClass",
                "kind": SYMBOL_KIND_CLASS,
                "children": [
                    {"name": "method", "kind": SYMBOL_KIND_METHOD},
                    {"name": "field", "kind": SYMBOL_KIND_FIELD},
                ]
            }
        ]
        result = filter_symbols(symbols, VerbosityLevel.VERBOSE)

        assert len(result) == 1
        assert result[0]["name"] == "MyClass"
        assert len(result[0]["children"]) == 2

    def test_deep_nesting_three_levels(self) -> None:
        """Verify filtering works correctly at 3+ levels of nesting."""
        symbols = DEEPLY_NESTED_SYMBOL_RESPONSE["symbols"]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        module = result[0]
        assert module["name"] == "Module"
        assert len(module["children"]) == 1

        my_class = module["children"][0]
        assert my_class["name"] == "MyClass"
        # After filtering: method remains (non-variable), field is excluded (FIELD kind)
        assert len(my_class["children"]) == 1

        children_names = [c["name"] for c in my_class["children"]]
        assert "method" in children_names

        method = [c for c in my_class["children"] if c["name"] == "method"][0]
        # method's children (local_var - VARIABLE) should be filtered out
        assert len(method["children"]) == 0

    def test_parent_with_only_variable_children(self) -> None:
        """Verify parent is retained even when all children are filtered out."""
        symbols = PARENT_WITH_ONLY_VARIABLE_CHILDREN["symbols"]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert result[0]["name"] == "MyClass"
        assert "children" in result[0]
        assert len(result[0]["children"]) == 0

    def test_empty_children_array(self) -> None:
        """Verify symbols with empty children array are handled correctly."""
        symbols = [
            {
                "name": "MyClass",
                "kind": SYMBOL_KIND_CLASS,
                "children": []
            }
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert result[0]["name"] == "MyClass"
        assert result[0]["children"] == []

    def test_mixed_children_some_variables(self) -> None:
        """Verify mixed children list filters only variable kinds."""
        symbols = [
            {
                "name": "MyClass",
                "kind": SYMBOL_KIND_CLASS,
                "children": [
                    {"name": "method", "kind": SYMBOL_KIND_METHOD},
                    {"name": "field1", "kind": SYMBOL_KIND_FIELD},
                    {"name": "function", "kind": SYMBOL_KIND_FUNCTION},
                    {"name": "field2", "kind": SYMBOL_KIND_FIELD},
                ]
            }
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert len(result[0]["children"]) == 2
        child_names = [c["name"] for c in result[0]["children"]]
        assert "method" in child_names
        assert "function" in child_names

    def test_multi_branch_nested(self) -> None:
        """Verify recursive filtering at multiple branch points."""
        symbols = MULTI_BRANCH_NESTED["symbols"]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        root = result[0]
        assert len(root["children"]) == 2

        branch_a = [c for c in root["children"] if c["name"] == "branch_a"][0]
        branch_b = [c for c in root["children"] if c["name"] == "branch_b"][0]

        assert len(branch_a["children"]) == 0
        assert len(branch_b["children"]) == 1
        assert branch_b["children"][0]["name"] == "func_b"

    def test_preserves_structure_excluding_variables(self) -> None:
        """Verify non-variable structure is preserved after filtering."""
        symbols = [
            {
                "name": "Module",
                "kind": SYMBOL_KIND_MODULE,
                "location": {"uri": "file:///test.py"},
                "children": [
                    {
                        "name": "MyClass",
                        "kind": SYMBOL_KIND_CLASS,
                        "detail": "A class",
                        "children": [
                            {"name": "var", "kind": SYMBOL_KIND_VARIABLE},
                            {"name": "method", "kind": SYMBOL_KIND_METHOD},
                        ]
                    }
                ]
            }
        ]
        result = filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert len(result) == 1
        assert result[0]["name"] == "Module"
        assert result[0]["location"] == {"uri": "file:///test.py"}
        assert len(result[0]["children"]) == 1
        assert result[0]["children"][0]["name"] == "MyClass"
        assert result[0]["children"][0]["detail"] == "A class"

    def test_recursion_no_mutation(self) -> None:
        """Verify input symbols are not mutated during filtering."""
        original_symbol = {
            "name": "MyClass",
            "kind": SYMBOL_KIND_CLASS,
            "children": [
                {"name": "field", "kind": SYMBOL_KIND_FIELD},
                {"name": "method", "kind": SYMBOL_KIND_METHOD},
            ]
        }
        symbols = [original_symbol]

        original_copy = {
            "name": "MyClass",
            "kind": SYMBOL_KIND_CLASS,
            "children": [
                {"name": "field", "kind": SYMBOL_KIND_FIELD},
                {"name": "method", "kind": SYMBOL_KIND_METHOD},
            ]
        }

        filter_symbols(symbols, VerbosityLevel.NORMAL)

        assert symbols[0] == original_copy
