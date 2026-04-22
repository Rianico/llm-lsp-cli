"""Mock LSP response fixtures for tests.

This module centralizes all mock LSP server responses used in testing.
Each constant represents a typical response from an LSP command.

Usage:
    from tests.fixtures import (
        LOCATION_RESPONSE,
        DOCUMENT_SYMBOL_RESPONSE,
        COMPLETION_RESPONSE,
        HOVER_RESPONSE,
        WORKSPACE_SYMBOL_RESPONSE,
        create_location_response_with_test_files,
        create_workspace_symbol_response_with_test_files,
    )
"""

from typing import Any

__all__ = [
    # Location-Based
    "LOCATION_RESPONSE",
    "LOCATION_RESPONSE_MULTI",
    "LOCATION_RESPONSE_EMPTY",
    "LOCATION_RESPONSE_WITH_COMMAS",
    "LOCATION_RESPONSE_WITH_QUOTES",
    "create_location_response_with_test_files",
    # Symbol-Based
    "SYMBOL_RESPONSE",
    "DOCUMENT_SYMBOL_RESPONSE",
    "DOCUMENT_SYMBOL_WITH_CHILDREN",
    "WORKSPACE_SYMBOL_RESPONSE",
    "create_workspace_symbol_response_with_test_files",
    "create_workspace_symbol_response_with_variables",
    "create_document_symbol_response_with_variables",
    # Completion-Based
    "COMPLETION_RESPONSE",
    "COMPLETION_RESPONSE_RICH",
    "COMPLETION_RESPONSE_EMPTY",
    "COMPLETION_RESPONSE_MINIMAL",
    "COMPLETION_RESPONSE_WITH_COMMAS",
    # Hover-Based
    "HOVER_RESPONSE",
    "HOVER_RESPONSE_PLAINTEXT",
    "HOVER_RESPONSE_EMPTY",
    # Symbol Kind Constants
    "SYMBOL_KIND_FILE",
    "SYMBOL_KIND_MODULE",
    "SYMBOL_KIND_NAMESPACE",
    "SYMBOL_KIND_PACKAGE",
    "SYMBOL_KIND_CLASS",
    "SYMBOL_KIND_METHOD",
    "SYMBOL_KIND_PROPERTY",
    "SYMBOL_KIND_FIELD",
    "SYMBOL_KIND_CONSTRUCTOR",
    "SYMBOL_KIND_ENUM",
    "SYMBOL_KIND_INTERFACE",
    "SYMBOL_KIND_FUNCTION",
    "SYMBOL_KIND_VARIABLE",
    "SYMBOL_KIND_CONSTANT",
    # Symbol Fixtures
    "VARIABLE_SYMBOL",
    "FIELD_SYMBOL",
    "CLASS_SYMBOL",
    "FUNCTION_SYMBOL",
    "METHOD_SYMBOL",
    "MIXED_SYMBOLS",
    # Recursive Filtering Fixtures
    "DEEPLY_NESTED_SYMBOL_RESPONSE",
    "PARENT_WITH_ONLY_VARIABLE_CHILDREN",
    "WIDE_TREE_SYMBOLS",
    "MULTI_BRANCH_NESTED",
    "create_nested_symbol",
]


# =============================================================================
# Location-Based Responses
# Used by: definition, references, implementation
# =============================================================================

LOCATION_RESPONSE: dict[str, Any] = {
    "locations": [
        {
            "uri": "file:///path/to/file.py",
            "range": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 20},
            },
        }
    ]
}

LOCATION_RESPONSE_MULTI: dict[str, Any] = {
    "locations": [
        {
            "uri": "file:///path/to/file1.py",
            "range": {
                "start": {"line": 5, "character": 0},
                "end": {"line": 5, "character": 15},
            },
        },
        {
            "uri": "file:///path/to/file2.py",
            "range": {
                "start": {"line": 20, "character": 8},
                "end": {"line": 20, "character": 23},
            },
        },
        {
            "uri": "file:///path/to/file3.py",
            "range": {
                "start": {"line": 100, "character": 12},
                "end": {"line": 100, "character": 30},
            },
        },
    ]
}

LOCATION_RESPONSE_EMPTY: dict[str, Any] = {"locations": []}

LOCATION_RESPONSE_WITH_COMMAS: dict[str, Any] = {
    "locations": [
        {
            "uri": "file:///path/to/file,with,commas.py",
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
        }
    ]
}
"""Location response with commas in URI for CSV escaping tests."""

LOCATION_RESPONSE_WITH_QUOTES: dict[str, Any] = {
    "locations": [
        {
            "uri": 'file:///path/to/file"with"quotes.py',
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 10},
            },
        }
    ]
}
"""Location response with double quotes in URI for CSV escaping tests."""


# =============================================================================
# Symbol Responses
# Used by: document-symbol, workspace-symbol
# =============================================================================

SYMBOL_RESPONSE: dict[str, Any] = {
    "symbols": [
        {
            "name": "MyClass",
            "kind": 5,
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 50, "character": 0},
            },
        }
    ]
}

DOCUMENT_SYMBOL_RESPONSE: dict[str, Any] = {
    "symbols": [
        {
            "name": "MyClass",
            "kind": 5,
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 50, "character": 0},
            },
            "selectionRange": {
                "start": {"line": 0, "character": 6},
                "end": {"line": 0, "character": 13},
            },
        }
    ]
}

DOCUMENT_SYMBOL_WITH_CHILDREN: dict[str, Any] = {
    "symbols": [
        {
            "name": "MyClass",
            "kind": 5,
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 50, "character": 0},
            },
            "children": [
                {
                    "name": "__init__",
                    "kind": 6,
                    "range": {
                        "start": {"line": 5, "character": 4},
                        "end": {"line": 10, "character": 0},
                    },
                },
                {
                    "name": "my_method",
                    "kind": 6,
                    "range": {
                        "start": {"line": 15, "character": 4},
                        "end": {"line": 25, "character": 0},
                    },
                },
            ],
        },
        {
            "name": "helper_function",
            "kind": 12,
            "range": {
                "start": {"line": 55, "character": 0},
                "end": {"line": 70, "character": 0},
            },
        },
    ]
}

WORKSPACE_SYMBOL_RESPONSE: dict[str, Any] = {
    "symbols": [
        {
            "name": "MyClass",
            "kind": 5,
            "location": {
                "uri": "file:///path/to/myclass.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
            },
        },
        {
            "name": "helper_function",
            "kind": 12,
            "location": {
                "uri": "file:///path/to/utils.py",
                "range": {
                    "start": {"line": 10, "character": 0},
                    "end": {"line": 30, "character": 0},
                },
            },
        },
    ]
}


# =============================================================================
# Completion Responses
# Used by: completion
# =============================================================================

COMPLETION_RESPONSE: dict[str, Any] = {
    "items": [
        {
            "label": "my_function",
            "kind": 12,
            "detail": "def my_function(x: int) -> str",
            "documentation": "A sample function",
        },
        {
            "label": "my_variable",
            "kind": 13,
            "detail": "str",
        },
    ]
}

COMPLETION_RESPONSE_EMPTY: dict[str, Any] = {"items": []}

COMPLETION_RESPONSE_RICH: dict[str, Any] = {
    "items": [
        {
            "label": "complex_function",
            "kind": 12,
            "tags": [1, 2],
            "detail": "def complex_function(x: int, y: str) -> tuple",
            "documentation": {
                "kind": "markdown",
                "value": "Detailed documentation",
            },
            "deprecated": False,
            "preselect": True,
            "filterText": "complex_function",
            "insertText": "complex_function(${1:x}, ${2:y})",
            "insertTextFormat": 2,
            "textEdit": {
                "range": {
                    "start": {"line": 10, "character": 0},
                    "end": {"line": 10, "character": 5},
                },
                "newText": "complex_function()",
            },
        }
    ]
}

COMPLETION_RESPONSE_MINIMAL: dict[str, Any] = {
    "items": [
        {
            "label": "minimal_item",
        }
    ]
}
"""Minimal completion response with only label field.

Used for testing missing optional fields handling.
"""

COMPLETION_RESPONSE_WITH_COMMAS: dict[str, Any] = {
    "items": [
        {
            "label": "func_with_args",
            "kind": 12,
            "detail": "def func(a, b, c):  # has, commas",
            "documentation": "Documentation, with, commas",
        }
    ]
}
"""Completion response with commas in detail/documentation for CSV tests."""


# =============================================================================
# Hover Responses
# Used by: hover
# =============================================================================

HOVER_RESPONSE: dict[str, Any] = {
    "hover": {
        "contents": {
            "kind": "markdown",
            "value": "```python\ndef my_function(x: int) -> str\n```\n\nA sample function.",
        },
        "range": {
            "start": {"line": 10, "character": 4},
            "end": {"line": 10, "character": 15},
        },
    }
}

HOVER_RESPONSE_PLAINTEXT: dict[str, Any] = {
    "hover": {
        "contents": {"kind": "plaintext", "value": "Hover content"},
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 10},
        },
    }
}

HOVER_RESPONSE_EMPTY: dict[str, Any] = {"hover": None}


# =============================================================================
# Test File Filtering Responses
# Used by: tests with --include-tests flag
# =============================================================================


def create_location_response_with_test_files() -> dict[str, Any]:
    """Create location response with both source and test files.

    Returns:
        Location response with mixed source/test files
    """
    return {
        "locations": [
            {
                "uri": "file:///path/to/file.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 5, "character": 15},
                },
            },
            {
                "uri": "file:///path/to/tests/test_file.py",
                "range": {
                    "start": {"line": 10, "character": 4},
                    "end": {"line": 10, "character": 19},
                },
            },
        ]
    }


def create_workspace_symbol_response_with_test_files() -> dict[str, Any]:
    """Create workspace symbol response with both source and test file symbols.

    Returns:
        Workspace symbol response with mixed source/test file symbols
    """
    return {
        "symbols": [
            {
                "name": "MyClass",
                "kind": SYMBOL_KIND_CLASS,
                "location": {
                    "uri": "file:///path/to/file.py",
                    "range": {
                        "start": {"line": 5, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            },
            {
                "name": "TestMyClass",
                "kind": SYMBOL_KIND_CLASS,
                "location": {
                    "uri": "file:///path/to/tests/test_file.py",
                    "range": {
                        "start": {"line": 10, "character": 4},
                        "end": {"line": 30, "character": 0},
                    },
                },
            },
        ]
    }


# =============================================================================
# Symbol Kind Constants (from LSP specification)
# Used by: symbol_filter tests
# =============================================================================

SYMBOL_KIND_FILE = 1
SYMBOL_KIND_MODULE = 2
SYMBOL_KIND_NAMESPACE = 3
SYMBOL_KIND_PACKAGE = 4
SYMBOL_KIND_CLASS = 5
SYMBOL_KIND_METHOD = 6
SYMBOL_KIND_PROPERTY = 7
SYMBOL_KIND_FIELD = 8  # Variable-level (filtered by default)
SYMBOL_KIND_CONSTRUCTOR = 9
SYMBOL_KIND_ENUM = 10
SYMBOL_KIND_INTERFACE = 11
SYMBOL_KIND_FUNCTION = 12
SYMBOL_KIND_VARIABLE = 13  # Variable-level (filtered by default)
SYMBOL_KIND_CONSTANT = 14


# =============================================================================
# Symbol Fixtures for Symbol Filter Tests
# =============================================================================

VARIABLE_SYMBOL: dict[str, Any] = {
    "name": "my_var",
    "kind": SYMBOL_KIND_VARIABLE,
    "location": {"uri": "file:///project/src/module.py"},
}

FIELD_SYMBOL: dict[str, Any] = {
    "name": "instance_field",
    "kind": SYMBOL_KIND_FIELD,
    "location": {"uri": "file:///project/src/module.py"},
}

CLASS_SYMBOL: dict[str, Any] = {
    "name": "MyClass",
    "kind": SYMBOL_KIND_CLASS,
    "location": {"uri": "file:///project/src/module.py"},
}

FUNCTION_SYMBOL: dict[str, Any] = {
    "name": "my_function",
    "kind": SYMBOL_KIND_FUNCTION,
    "location": {"uri": "file:///project/src/module.py"},
}

METHOD_SYMBOL: dict[str, Any] = {
    "name": "my_method",
    "kind": SYMBOL_KIND_METHOD,
    "location": {"uri": "file:///project/src/module.py"},
}

MIXED_SYMBOLS: list[dict[str, Any]] = [
    VARIABLE_SYMBOL,
    FIELD_SYMBOL,
    CLASS_SYMBOL,
    FUNCTION_SYMBOL,
    METHOD_SYMBOL,
]


# =============================================================================
# Recursive Filtering Fixtures (for test_symbol_filter.py)
# =============================================================================

DEEPLY_NESTED_SYMBOL_RESPONSE: dict[str, Any] = {
    "symbols": [
        {
            "name": "Module",
            "kind": SYMBOL_KIND_MODULE,
            "children": [
                {
                    "name": "MyClass",
                    "kind": SYMBOL_KIND_CLASS,
                    "children": [
                        {
                            "name": "method",
                            "kind": SYMBOL_KIND_METHOD,
                            "children": [
                                {
                                    "name": "local_var",
                                    "kind": SYMBOL_KIND_VARIABLE,
                                }
                            ],
                        },
                        {
                            "name": "field",
                            "kind": SYMBOL_KIND_FIELD,
                        },
                    ],
                }
            ],
        }
    ]
}
"""Deeply nested structure (3+ levels) for recursive filtering tests."""


PARENT_WITH_ONLY_VARIABLE_CHILDREN: dict[str, Any] = {
    "symbols": [
        {
            "name": "MyClass",
            "kind": SYMBOL_KIND_CLASS,
            "children": [
                {"name": "field1", "kind": SYMBOL_KIND_FIELD},
                {"name": "field2", "kind": SYMBOL_KIND_FIELD},
            ],
        }
    ]
}
"""Parent with all variable children (tests empty-after-filter scenario)."""


WIDE_TREE_SYMBOLS: list[dict[str, Any]] = [
    {
        "name": "Parent",
        "kind": SYMBOL_KIND_CLASS,
        "children": [
            {"name": f"child_{i}", "kind": SYMBOL_KIND_METHOD if i % 2 == 0 else SYMBOL_KIND_FIELD}
            for i in range(100)
        ],
    }
]
"""Wide tree fixture with 100 sibling children for performance tests."""


MULTI_BRANCH_NESTED: dict[str, Any] = {
    "symbols": [
        {
            "name": "Root",
            "kind": SYMBOL_KIND_CLASS,
            "children": [
                {
                    "name": "branch_a",
                    "kind": SYMBOL_KIND_METHOD,
                    "children": [{"name": "var_a", "kind": SYMBOL_KIND_VARIABLE}],
                },
                {
                    "name": "branch_b",
                    "kind": SYMBOL_KIND_METHOD,
                    "children": [{"name": "func_b", "kind": SYMBOL_KIND_FUNCTION}],
                },
            ],
        }
    ]
}
"""Multi-branch nested fixture for testing recursive filtering at multiple branch points."""


def create_nested_symbol(depth: int, variable_at_leaf: bool = True) -> dict[str, Any]:
    """Create a nested symbol structure of specified depth.

    Args:
        depth: Depth of the nested structure (1 = leaf node)
        variable_at_leaf: If True, leaf node is VARIABLE kind; otherwise FUNCTION

    Returns:
        Nested symbol dictionary
    """
    if depth == 1:
        kind = SYMBOL_KIND_VARIABLE if variable_at_leaf else SYMBOL_KIND_FUNCTION
        return {"name": f"leaf_{depth}", "kind": kind}
    return {
        "name": f"node_{depth}",
        "kind": SYMBOL_KIND_CLASS if depth % 2 == 0 else SYMBOL_KIND_METHOD,
        "children": [create_nested_symbol(depth - 1, variable_at_leaf)],
    }


def create_workspace_symbol_response_with_variables() -> dict[str, Any]:
    """Create workspace symbol response with mixed variable and non-variable symbols."""
    return {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///project/src/models.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 50, "character": 0},
                    },
                },
            },
            {
                "name": "my_variable",
                "kind": 13,
                "location": {
                    "uri": "file:///project/src/models.py",
                    "range": {
                        "start": {"line": 10, "character": 4},
                        "end": {"line": 10, "character": 20},
                    },
                },
            },
            {
                "name": "instance_field",
                "kind": 8,
                "location": {
                    "uri": "file:///project/src/models.py",
                    "range": {
                        "start": {"line": 5, "character": 8},
                        "end": {"line": 5, "character": 24},
                    },
                },
            },
            {
                "name": "helper_function",
                "kind": 12,
                "location": {
                    "uri": "file:///project/src/utils.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 30, "character": 0},
                    },
                },
            },
        ]
    }


def create_document_symbol_response_with_variables() -> dict[str, Any]:
    """Create document symbol response with nested structure including variables."""
    return {
        "symbols": [
            {
                "name": "MyClass",
                "kind": 5,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 50, "character": 0},
                },
                "children": [
                    {
                        "name": "__init__",
                        "kind": 6,
                        "range": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 10, "character": 0},
                        },
                    },
                    {
                        "name": "instance_var",
                        "kind": 8,  # FIELD
                        "range": {
                            "start": {"line": 6, "character": 8},
                            "end": {"line": 6, "character": 20},
                        },
                    },
                ],
            },
            {
                "name": "module_variable",
                "kind": 13,  # VARIABLE
                "range": {
                    "start": {"line": 55, "character": 0},
                    "end": {"line": 55, "character": 20},
                },
            },
        ]
    }
