"""Tests to verify cast() removal from LSP client.

After the refactoring, no cast() calls should remain for LSP types
in client.py - all type safety should come from Pydantic validation.

Note: cast(dict[str, Any]) for rename operations (WorkspaceEdit) is
explicitly OUT OF SCOPE and remains in the codebase.
"""

import re
from pathlib import Path


def test_no_cast_calls_for_lsp_types() -> None:
    """Verify no cast() calls remain for LSP types in client.py.

    Note: cast(dict[str, Any]) is allowed for out-of-scope types like WorkspaceEdit.
    """
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Check for cast calls with lsp. types (not dict[str, Any])
    cast_pattern = r'cast\([^)]*lsp\.\w+'
    matches = re.findall(cast_pattern, content)

    assert len(matches) == 0, f"Found cast() calls for LSP types: {matches}"


def test_no_cast_calls_for_hover_type() -> None:
    """Verify cast(lsp.Hover...) is removed."""
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Check for cast calls with lsp.Hover
    matches = re.findall(r'cast\([^)]*lsp\.Hover', content)

    assert len(matches) == 0, f"Found cast(lsp.Hover...) calls: {matches}"


def test_no_cast_calls_for_location_type() -> None:
    """Verify cast(lsp.Location...) is removed."""
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Check for cast calls with lsp.Location
    matches = re.findall(r'cast\([^)]*lsp\.Location', content)

    assert len(matches) == 0, f"Found cast(lsp.Location...) calls: {matches}"


def test_no_cast_calls_for_initialize_result() -> None:
    """Verify cast(lsp.InitializeResult) is removed."""
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Check for cast calls with lsp.InitializeResult
    matches = re.findall(r'cast\([^)]*lsp\.InitializeResult', content)

    assert len(matches) == 0, f"Found cast(lsp.InitializeResult) calls: {matches}"


def test_no_cast_calls_for_completion_item() -> None:
    """Verify cast(lsp.CompletionItem...) is removed."""
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Check for cast calls with lsp.CompletionItem
    matches = re.findall(r'cast\([^)]*lsp\.CompletionItem', content)

    assert len(matches) == 0, f"Found cast(lsp.CompletionItem...) calls: {matches}"


def test_no_cast_calls_for_rename_types() -> None:
    """Verify no cast() calls remain for rename operations.

    After adding WorkspaceEdit and PrepareRenameResult types, the cast() calls
    were removed. The typed transport methods return validated Pydantic models.
    """
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Check for any cast calls with dict[str, object] in rename methods
    rename_cast_pattern = r'cast\(dict\[str, object\] \| None, result\)'
    matches = re.findall(rename_cast_pattern, content)

    # No cast() calls should remain - typed transport returns validated models
    assert len(matches) == 0, f"Found cast() calls for rename: {matches}"
