"""Tests for TTY detection."""

from llm_lsp_cli.infrastructure.logging import Colors, LSPLogger


class TestTTYDetection:
    """Test TTY auto-detection behavior."""

    def test_auto_detect_tty(self, mock_tty_stdout: None) -> None:
        """Verify auto-detection returns True for TTY."""
        assert Colors.supported() is True

    def test_auto_detect_non_tty(self, mock_non_tty_stdout: None) -> None:
        """Verify auto-detection returns False for non-TTY."""
        assert Colors.supported() is False

    def test_explicit_use_colors_true(self, mock_non_tty_stdout: None) -> None:
        """Verify explicit use_colors=True does not call disable()."""
        # use_colors=True should NOT call disable(), so _disabled should be False
        LSPLogger(use_colors=True)
        assert Colors._disabled is False

    def test_explicit_use_colors_false(self) -> None:
        """Verify explicit use_colors=False forces colors off."""
        LSPLogger(use_colors=False)
        # Should disable colors
        assert Colors._disabled is True
        assert Colors.RESET == ""
