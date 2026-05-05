"""Tests for Colors ANSI color codes and TTY detection."""

import pytest

from llm_lsp_cli.infrastructure.logging import Colors


class TestColorCodes:
    """Test color code constants."""

    def test_color_codes_are_defined(self) -> None:
        """Verify all ANSI color codes are non-empty strings."""
        assert Colors.reset
        assert Colors.cli
        assert Colors.server
        assert Colors.success
        assert Colors.error
        assert Colors.info
        assert Colors.debug

    def test_color_codes_match_reference(self) -> None:
        """Verify color codes match reference implementation."""
        assert Colors.cli == "\033[36m"  # Cyan
        assert Colors.server == "\033[33m"  # Yellow
        assert Colors.success == "\033[32m"  # Green
        assert Colors.error == "\033[31m"  # Red
        assert Colors.info == "\033[34m"  # Blue


class TestColorSupport:
    """Test color support detection and disabling."""

    def test_colors_supported_when_tty(self, mock_tty_stdout: None) -> None:
        """Verify colors are supported when stdout is a TTY."""
        assert Colors.supported() is True

    def test_colors_not_supported_when_not_tty(self, mock_non_tty_stdout: None) -> None:
        """Verify colors are disabled when stdout is not a TTY."""
        assert Colors.supported() is False

    def test_colors_respect_no_color_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify NO_COLOR environment variable disables colors."""
        monkeypatch.setenv("NO_COLOR", "1")
        assert Colors.supported() is False

    def test_disable_sets_empty_codes(self) -> None:
        """Verify disable() sets all color codes to empty strings."""
        Colors.disable()
        assert Colors.reset == ""
        assert Colors.cli == ""
        assert Colors.server == ""
        assert Colors.success == ""
        assert Colors.error == ""
        assert Colors.info == ""
