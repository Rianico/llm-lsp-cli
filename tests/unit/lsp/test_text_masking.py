"""Unit tests for text field masking verification.

Tests for the _mask_text_content function and _mask_diagnostics integration.
"""

import copy
from typing import Any

# =============================================================================
# Test Suite 3.1: _mask_text_content Function
# =============================================================================


class TestMaskTextContent:
    """Tests for _mask_text_content function."""

    def test_mask_did_open_text(self) -> None:
        """textDocument/didOpen text field masked."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {
                "uri": "file:///test/sample.py",
                "languageId": "python",
                "version": 1,
                "text": "def hello():\n    print('world')\n",
            }
        }

        _mask_text_content(params)

        assert params["textDocument"]["text"] == "... (text_len: 32)"
        assert params["textDocument"]["uri"] == "file:///test/sample.py"
        assert params["textDocument"]["languageId"] == "python"
        assert params["textDocument"]["version"] == 1

    def test_mask_did_change_text(self) -> None:
        """textDocument/didChange contentChanges masked."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {"uri": "file:///test/sample.py", "version": 2},
            "contentChanges": [
                {"text": "new code here"},
                {"text": "another change"},
            ],
        }

        _mask_text_content(params)

        assert params["contentChanges"][0]["text"] == "... (text_len: 13)"
        assert params["contentChanges"][1]["text"] == "... (text_len: 14)"

    def test_mask_preserves_other_fields(self) -> None:
        """Non-text fields preserved unchanged."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {
                "uri": "file:///test/sample.py",
                "languageId": "python",
                "version": 5,
                "text": "some code",
            }
        }

        _mask_text_content(params)

        assert params["textDocument"]["uri"] == "file:///test/sample.py"
        assert params["textDocument"]["languageId"] == "python"
        assert params["textDocument"]["version"] == 5

    def test_mask_empty_text(self) -> None:
        """Empty text string handled correctly."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        params: dict[str, Any] = {
            "textDocument": {
                "uri": "file:///test/empty.py",
                "text": "",
            }
        }

        _mask_text_content(params)

        assert params["textDocument"]["text"] == "... (text_len: 0)"

    def test_mask_unicode_text(self) -> None:
        """Unicode text length calculated correctly (character count, not bytes)."""
        from llm_lsp_cli.lsp.transport import _mask_text_content

        unicode_text = "def hello():\n    print('Hello, 世界!')\n"
        params: dict[str, Any] = {
            "textDocument": {
                "uri": "file:///test/unicode.py",
                "text": unicode_text,
            }
        }

        _mask_text_content(params)

        # len() on Python string counts characters, not bytes
        expected_len = len(unicode_text)
        assert params["textDocument"]["text"] == f"... (text_len: {expected_len})"


# =============================================================================
# Test Suite 3.2: _mask_diagnostics Integration
# =============================================================================


class TestMaskDiagnosticsIntegration:
    """Tests for _mask_diagnostics calling _mask_text_content."""

    def test_mask_did_open_in_mask_diagnostics(self) -> None:
        """_mask_diagnostics() calls _mask_text_content() for didOpen."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test/sample.py",
                    "text": "def hello():\n    print('world')\n",
                }
            },
        }

        result = _mask_diagnostics(input_data)

        assert result["params"]["textDocument"]["text"] == "... (text_len: 32)"

    def test_mask_did_change_in_mask_diagnostics(self) -> None:
        """_mask_diagnostics() calls _mask_text_content() for didChange."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        input_data: dict[str, Any] = {
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "file:///test/sample.py"},
                "contentChanges": [{"text": "new code"}],
            },
        }

        result = _mask_diagnostics(input_data)

        assert result["params"]["contentChanges"][0]["text"] == "... (text_len: 8)"

    def test_mask_immutability(self) -> None:
        """Original input dict not mutated."""
        from llm_lsp_cli.lsp.transport import _mask_diagnostics

        original_data: dict[str, Any] = {
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test/sample.py",
                    "text": "def hello():\n    print('world')\n",
                }
            },
        }
        original_copy = copy.deepcopy(original_data)

        _mask_diagnostics(original_data)

        # The input should not be mutated (deep copy is made)
        assert original_data == original_copy
