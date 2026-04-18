"""Tests for log formatters."""

from llm_lsp_cli.infrastructure.logging import (
    ColorFormatter,
    Colors,
    LogEntry,
    LSPMessageFormatter,
)


class TestColorFormatter:
    """Test ColorFormatter behavior."""

    def test_color_formatter_formats_entry(
        self, log_entry: LogEntry, mock_tty_stdout: None
    ) -> None:
        """Verify ColorFormatter produces expected output format."""
        formatter = ColorFormatter()
        output = formatter.format(log_entry)

        assert "client" in output
        assert log_entry.message in output

    def test_color_formatter_uses_error_color(
        self, error_log_entry: LogEntry, mock_tty_stdout: None
    ) -> None:
        """Verify ERROR level uses red color."""
        formatter = ColorFormatter()
        output = formatter.format(error_log_entry)

        assert Colors.ERROR in output

    def test_color_formatter_uses_success_color(
        self, success_log_entry: LogEntry, mock_tty_stdout: None
    ) -> None:
        """Verify SUCCESS level uses green color."""
        formatter = ColorFormatter()
        output = formatter.format(success_log_entry)

        assert Colors.SUCCESS in output

    def test_color_formatter_falls_back_to_plain(
        self,
        log_entry: LogEntry,
        mock_non_tty_stdout: None,
    ) -> None:
        """Verify formatter falls back to plain text when colors unsupported."""
        formatter = ColorFormatter()
        output = formatter.format(log_entry)

        # Check for ANSI escape character, not empty color codes
        assert "\033" not in output
        assert log_entry.message in output


class TestLSPMessageFormatter:
    """Test LSPMessageFormatter behavior."""

    def test_lsp_formatter_truncates_long_messages(self) -> None:
        """Verify LSP message formatter truncates payloads over MAX_PAYLOAD_LENGTH."""
        formatter = LSPMessageFormatter()
        long_message = {"data": "x" * 500}

        output = formatter.format_trace("→", long_message)

        assert len(output) < 500  # Truncated

    def test_lsp_formatter_shows_direction_sent(
        self, lsp_message: dict, mock_tty_stdout: None
    ) -> None:
        """Verify sent messages show → direction indicator."""
        formatter = LSPMessageFormatter()
        output = formatter.format_trace("→", lsp_message)

        assert "→" in output
        assert Colors.CLI in output

    def test_lsp_formatter_shows_direction_received(
        self, lsp_message: dict, mock_tty_stdout: None
    ) -> None:
        """Verify received messages show ← direction indicator."""
        formatter = LSPMessageFormatter()
        output = formatter.format_trace("←", lsp_message)

        assert "←" in output
        assert Colors.SERVER in output

    def test_lsp_formatter_extracts_method(self) -> None:
        """Verify formatter extracts method name from LSP message."""
        formatter = LSPMessageFormatter()
        message = {"method": "textDocument/definition", "params": {}}

        output = formatter.format_trace("→", message)

        assert "textDocument/definition" in output
