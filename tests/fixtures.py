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
    """Create workspace symbol response with both source and test files.

    Returns:
        Workspace symbol response with mixed source/test files
    """
    return {
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
                "name": "TestMyClass",
                "kind": 5,
                "location": {
                    "uri": "file:///path/to/tests/test_myclass.py",
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 30, "character": 0},
                    },
                },
            },
        ]
    }
