"""Unit tests for output formatting utilities."""

from llm_lsp_cli.utils.formatter import OutputFormat


class TestOutputFormatEnum:
    """Tests for OutputFormat enum."""

    def test_csv_format_enum_exists(self) -> None:
        """Test that CSV format is available in OutputFormat enum."""
        assert hasattr(OutputFormat, "CSV")
        assert OutputFormat.CSV == "csv"

    def test_csv_format_in_iteration(self) -> None:
        """Test that CSV format can be iterated over with other formats."""
        formats = list(OutputFormat)
        format_values = [f.value for f in formats]

        assert "csv" in format_values
