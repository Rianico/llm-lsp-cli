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


def test_rename_cast_calls_remain() -> None:
    """Verify cast(dict[str, object]) for rename operations remains (out of scope)."""
    client_file = Path("src/llm_lsp_cli/lsp/client.py")
    content = client_file.read_text()

    # Rename operations use cast(dict[str, object] | None, result) - this is expected
    # The WorkspaceEdit type is out of scope for this refactor
    rename_cast_pattern = r'cast\(dict\[str, object\] \| None, result\)'
    matches = re.findall(rename_cast_pattern, content)

    # We expect exactly 2: one in request_prepare_rename and one in request_rename
    assert len(matches) == 2, f"Expected 2 cast() for rename, found {len(matches)}"
