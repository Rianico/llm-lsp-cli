"""Mock LSP response fixtures for tests.

This module centralizes all mock LSP server responses used in testing.
Each constant represents a typical response from an LSP command.

Two formats are provided:
- Dict fixtures (legacy): For tests that mock daemon responses
- Typed fixtures: For tests that mock send_request (returns Pydantic models)

Usage:
    from tests.fixtures import (
        LOCATION_RESPONSE,
        TYPED_LOCATION_RESPONSE,  # Returns list[Location]
        DOCUMENT_SYMBOL_RESPONSE,
        TYPED_DOCUMENT_SYMBOL_RESPONSE,  # Returns list[DocumentSymbol]
        COMPLETION_RESPONSE,
        TYPED_COMPLETION_RESPONSE,  # Returns list[CompletionItem]
        HOVER_RESPONSE,
        TYPED_HOVER_RESPONSE,  # Returns Hover | None
        WORKSPACE_SYMBOL_RESPONSE,
        TYPED_WORKSPACE_SYMBOL_RESPONSE,  # Returns list[SymbolInformation]
        create_location_response_with_test_files,
        create_workspace_symbol_response_with_test_files,
    )
"""

from typing import Any

from llm_lsp_cli.lsp.types import (
    CompletionItem,
    DocumentSymbol,
    Hover,
    Location,
    MarkupContent,
    Position,
    Range,
    SymbolInformation,
)

__all__ = [
    # Location-Based (dict format for daemon mocks)
    "LOCATION_RESPONSE",
    "LOCATION_RESPONSE_MULTI",
    "LOCATION_RESPONSE_EMPTY",
    "LOCATION_RESPONSE_WITH_COMMAS",
    "LOCATION_RESPONSE_WITH_QUOTES",
    "create_location_response_with_test_files",
    # Location-Based (typed for send_request mocks)
    "TYPED_LOCATION_RESPONSE",
    "TYPED_LOCATION_RESPONSE_MULTI",
    "TYPED_LOCATION_RESPONSE_EMPTY",
    "TYPED_LOCATION_RESPONSE_WITH_COMMAS",
    "TYPED_LOCATION_RESPONSE_WITH_QUOTES",
    "create_typed_location_response_with_test_files",
    # Symbol-Based (dict format)
    "SYMBOL_RESPONSE",
    "DOCUMENT_SYMBOL_RESPONSE",
    "DOCUMENT_SYMBOL_WITH_CHILDREN",
    "WORKSPACE_SYMBOL_RESPONSE",
    "create_workspace_symbol_response_with_test_files",
    "create_workspace_symbol_response_with_variables",
    "create_document_symbol_response_with_variables",
    # Symbol-Based (typed for send_request mocks)
    "TYPED_DOCUMENT_SYMBOL_RESPONSE",
    "TYPED_DOCUMENT_SYMBOL_WITH_CHILDREN",
    "TYPED_WORKSPACE_SYMBOL_RESPONSE",
    "create_typed_workspace_symbol_response_with_test_files",
    "create_typed_document_symbol_response_with_variables",
    # Completion-Based (dict format)
    "COMPLETION_RESPONSE",
    "COMPLETION_RESPONSE_RICH",
    "COMPLETION_RESPONSE_EMPTY",
    "COMPLETION_RESPONSE_MINIMAL",
    "COMPLETION_RESPONSE_WITH_COMMAS",
    # Completion-Based (typed for send_request mocks)
    "TYPED_COMPLETION_RESPONSE",
    "TYPED_COMPLETION_RESPONSE_RICH",
    "TYPED_COMPLETION_RESPONSE_EMPTY",
    "TYPED_COMPLETION_RESPONSE_WITH_COMMAS",
    # Hover-Based (dict format)
    "HOVER_RESPONSE",
    "HOVER_RESPONSE_PLAINTEXT",
    "HOVER_RESPONSE_EMPTY",
    # Hover-Based (typed for send_request mocks)
    "TYPED_HOVER_RESPONSE",
    "TYPED_HOVER_RESPONSE_PLAINTEXT",
    "TYPED_HOVER_RESPONSE_EMPTY",
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
    # Call Hierarchy Responses (LSP 3.17)
    "CALL_HIERARCHY_PREPARE_RESPONSE",
    "CALL_HIERARCHY_PREPARE_NULL_RESPONSE",
    "CALL_HIERARCHY_PREPARE_EMPTY_RESPONSE",
    "CALL_HIERARCHY_INCOMING_RESPONSE",
    "CALL_HIERARCHY_OUTGOING_RESPONSE",
    "CALL_HIERARCHY_EMPTY_RESPONSE",
    "CALL_HIERARCHY_NULL_CALLS_RESPONSE",
    "create_call_hierarchy_item_with_data",
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
                "selectionRange": {
                    "start": {"line": 0, "character": 6},
                    "end": {"line": 0, "character": 13},
                },
                "children": [
                    {
                        "name": "__init__",
                        "kind": 6,
                        "range": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 10, "character": 0},
                        },
                        "selectionRange": {
                            "start": {"line": 5, "character": 8},
                            "end": {"line": 5, "character": 16},
                        },
                    },
                    {
                        "name": "instance_var",
                        "kind": 8,  # FIELD
                        "range": {
                            "start": {"line": 6, "character": 8},
                            "end": {"line": 6, "character": 20},
                        },
                        "selectionRange": {
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
                "selectionRange": {
                    "start": {"line": 55, "character": 0},
                    "end": {"line": 55, "character": 15},
                },
            },
        ]
    }


# =============================================================================
# Call Hierarchy Responses (LSP 3.17)
# =============================================================================

CALL_HIERARCHY_PREPARE_RESPONSE: dict[str, Any] = {
    "items": [
        {
            "name": "my_function",
            "kind": 12,  # Function
            "uri": "file:///project/src/module.py",
            "range": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 20, "character": 0},
            },
            "selectionRange": {
                "start": {"line": 10, "character": 4},
                "end": {"line": 10, "character": 16},
            },
            "data": {"opaque": "server-data"},
        }
    ]
}

CALL_HIERARCHY_PREPARE_NULL_RESPONSE: dict[str, Any] = {"items": None}

CALL_HIERARCHY_PREPARE_EMPTY_RESPONSE: dict[str, Any] = {"items": []}

CALL_HIERARCHY_INCOMING_RESPONSE: dict[str, Any] = {
    "calls": [
        {
            "from": {  # NOTE: LSP uses 'from', Python uses 'from_'
                "name": "caller_function",
                "kind": 12,
                "uri": "file:///project/src/caller.py",
                "range": {
                    "start": {"line": 5, "character": 0},
                    "end": {"line": 10, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 5, "character": 4},
                    "end": {"line": 5, "character": 19},
                },
            },
            "fromRanges": [
                {
                    "start": {"line": 7, "character": 4},
                    "end": {"line": 7, "character": 19},
                }
            ],
        }
    ]
}

CALL_HIERARCHY_OUTGOING_RESPONSE: dict[str, Any] = {
    "calls": [
        {
            "to": {
                "name": "helper_function",
                "kind": 12,
                "uri": "file:///project/src/helper.py",
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 5, "character": 0},
                },
                "selectionRange": {
                    "start": {"line": 0, "character": 4},
                    "end": {"line": 0, "character": 19},
                },
            },
            "fromRanges": [
                {
                    "start": {"line": 15, "character": 8},
                    "end": {"line": 15, "character": 23},
                }
            ],
        }
    ]
}

CALL_HIERARCHY_EMPTY_RESPONSE: dict[str, Any] = {"calls": []}

CALL_HIERARCHY_NULL_CALLS_RESPONSE: dict[str, Any] = {"calls": None}


def create_call_hierarchy_item_with_data(data: dict[str, Any]) -> dict[str, Any]:
    """Create a CallHierarchyItem with custom data field.

    Args:
        data: Custom data field value

    Returns:
        CallHierarchyItem dict with custom data
    """
    return {
        "name": "test_func",
        "kind": 12,
        "uri": "file:///project/test.py",
        "range": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 5, "character": 0},
        },
        "selectionRange": {
            "start": {"line": 0, "character": 4},
            "end": {"line": 0, "character": 12},
        },
        "data": data,
    }


# =============================================================================
# TYPED FIXTURES FOR send_request MOCKS
# These return Pydantic model instances, matching send_request overloads
# =============================================================================


def _make_range(start_line: int, start_char: int, end_line: int, end_char: int) -> Range:
    """Create a Range from line/char values."""
    return Range(
        start=Position(line=start_line, character=start_char),
        end=Position(line=end_line, character=end_char),
    )


# -----------------------------------------------------------------------------
# Location fixtures (for definition, references)
# -----------------------------------------------------------------------------

TYPED_LOCATION_RESPONSE: list[Location] = [
    Location(
        uri="file:///path/to/file.py",
        range=_make_range(10, 4, 10, 20),
    )
]

TYPED_LOCATION_RESPONSE_MULTI: list[Location] = [
    Location(
        uri="file:///path/to/file1.py",
        range=_make_range(5, 0, 5, 15),
    ),
    Location(
        uri="file:///path/to/file2.py",
        range=_make_range(20, 8, 20, 23),
    ),
    Location(
        uri="file:///path/to/file3.py",
        range=_make_range(100, 12, 100, 30),
    ),
]

TYPED_LOCATION_RESPONSE_EMPTY: list[Location] = []

TYPED_LOCATION_RESPONSE_WITH_COMMAS: list[Location] = [
    Location(
        uri="file:///path/to/file,with,commas.py",
        range=_make_range(0, 0, 0, 10),
    )
]

TYPED_LOCATION_RESPONSE_WITH_QUOTES: list[Location] = [
    Location(
        uri='file:///path/to/file"with"quotes.py',
        range=_make_range(0, 0, 0, 10),
    )
]


def create_typed_location_response_with_test_files() -> list[Location]:
    """Create typed location response with both source and test files."""
    return [
        Location(
            uri="file:///path/to/file.py",
            range=_make_range(5, 0, 5, 15),
        ),
        Location(
            uri="file:///path/to/tests/test_file.py",
            range=_make_range(10, 4, 10, 19),
        ),
    ]


# -----------------------------------------------------------------------------
# DocumentSymbol fixtures
# -----------------------------------------------------------------------------

TYPED_DOCUMENT_SYMBOL_RESPONSE: list[DocumentSymbol] = [
    DocumentSymbol(
        name="MyClass",
        kind=SYMBOL_KIND_CLASS,
        range=_make_range(0, 0, 50, 0),
        selection_range=_make_range(0, 6, 0, 13),
    )
]

TYPED_DOCUMENT_SYMBOL_WITH_CHILDREN: list[DocumentSymbol] = [
    DocumentSymbol(
        name="MyClass",
        kind=SYMBOL_KIND_CLASS,
        range=_make_range(0, 0, 50, 0),
        selection_range=_make_range(0, 6, 0, 13),
        children=[
            DocumentSymbol(
                name="__init__",
                kind=SYMBOL_KIND_METHOD,
                range=_make_range(5, 4, 10, 0),
                selection_range=_make_range(5, 8, 5, 16),
            ),
            DocumentSymbol(
                name="my_method",
                kind=SYMBOL_KIND_METHOD,
                range=_make_range(15, 4, 25, 0),
                selection_range=_make_range(15, 8, 15, 17),
            ),
        ],
    ),
    DocumentSymbol(
        name="helper_function",
        kind=SYMBOL_KIND_FUNCTION,
        range=_make_range(55, 0, 70, 0),
        selection_range=_make_range(55, 0, 55, 15),
    ),
]


def create_typed_document_symbol_response_with_variables() -> list[DocumentSymbol]:
    """Create typed document symbol response with nested structure including variables."""
    return [
        DocumentSymbol(
            name="MyClass",
            kind=SYMBOL_KIND_CLASS,
            range=_make_range(0, 0, 50, 0),
            selection_range=_make_range(0, 6, 0, 13),
            children=[
                DocumentSymbol(
                    name="__init__",
                    kind=SYMBOL_KIND_METHOD,
                    range=_make_range(5, 4, 10, 0),
                    selection_range=_make_range(5, 8, 5, 16),
                ),
                DocumentSymbol(
                    name="instance_var",
                    kind=SYMBOL_KIND_FIELD,
                    range=_make_range(6, 8, 6, 20),
                    selection_range=_make_range(6, 8, 6, 20),
                ),
            ],
        ),
        DocumentSymbol(
            name="module_variable",
            kind=SYMBOL_KIND_VARIABLE,
            range=_make_range(55, 0, 55, 20),
            selection_range=_make_range(55, 0, 55, 15),
        ),
    ]


# -----------------------------------------------------------------------------
# SymbolInformation fixtures (for workspace/symbol)
# -----------------------------------------------------------------------------

TYPED_WORKSPACE_SYMBOL_RESPONSE: list[SymbolInformation] = [
    SymbolInformation(
        name="MyClass",
        kind=SYMBOL_KIND_CLASS,
        location=Location(
            uri="file:///path/to/myclass.py",
            range=_make_range(0, 0, 50, 0),
        ),
    ),
    SymbolInformation(
        name="helper_function",
        kind=SYMBOL_KIND_FUNCTION,
        location=Location(
            uri="file:///path/to/utils.py",
            range=_make_range(10, 0, 30, 0),
        ),
    ),
]


def create_typed_workspace_symbol_response_with_test_files() -> list[SymbolInformation]:
    """Create typed workspace symbol response with both source and test file symbols."""
    return [
        SymbolInformation(
            name="MyClass",
            kind=SYMBOL_KIND_CLASS,
            location=Location(
                uri="file:///path/to/file.py",
                range=_make_range(5, 0, 50, 0),
            ),
        ),
        SymbolInformation(
            name="TestMyClass",
            kind=SYMBOL_KIND_CLASS,
            location=Location(
                uri="file:///path/to/tests/test_file.py",
                range=_make_range(10, 4, 30, 0),
            ),
        ),
    ]


# -----------------------------------------------------------------------------
# CompletionItem fixtures
# -----------------------------------------------------------------------------

TYPED_COMPLETION_RESPONSE: list[CompletionItem] = [
    CompletionItem(
        label="my_function",
        kind=SYMBOL_KIND_FUNCTION,
        detail="def my_function(x: int) -> str",
        documentation="A sample function",
    ),
    CompletionItem(
        label="my_variable",
        kind=SYMBOL_KIND_VARIABLE,
        detail="str",
    ),
]

TYPED_COMPLETION_RESPONSE_EMPTY: list[CompletionItem] = []

TYPED_COMPLETION_RESPONSE_RICH: list[CompletionItem] = [
    CompletionItem(
        label="complex_function",
        kind=SYMBOL_KIND_FUNCTION,
        tags=[1, 2],
        detail="def complex_function(x: int, y: str) -> tuple",
        documentation=MarkupContent(
            kind="markdown",
            value="Detailed documentation",
        ),
    ),
]

TYPED_COMPLETION_RESPONSE_WITH_COMMAS: list[CompletionItem] = [
    CompletionItem(
        label="func_with_args",
        kind=SYMBOL_KIND_FUNCTION,
        detail="def func(a, b, c):  # has, commas",
        documentation="Documentation, with, commas",
    ),
]


# -----------------------------------------------------------------------------
# Hover fixtures
# -----------------------------------------------------------------------------

TYPED_HOVER_RESPONSE: Hover = Hover(
    contents=MarkupContent(
        kind="markdown",
        value="```python\ndef my_function(x: int) -> str\n```\n\nA sample function.",
    ),
    range=_make_range(10, 4, 10, 15),
)

TYPED_HOVER_RESPONSE_PLAINTEXT: Hover = Hover(
    contents=MarkupContent(
        kind="plaintext",
        value="Hover content",
    ),
    range=_make_range(0, 0, 0, 10),
)

TYPED_HOVER_RESPONSE_EMPTY: Hover | None = None
